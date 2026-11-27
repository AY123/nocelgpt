"""Exclusive private exports, verified against a caller-rebuilt Draft assembly.

The manifest is written last. Its presence alone is not verification or source
freshness: all expected bytes and the application's current sources must pass.
Partial exports remain untouched for diagnosis; this module never resumes one.
"""

from __future__ import annotations

import os
import stat
import unicodedata
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from anovel.canon.identity import canonical_bytes, decode_canonical

from .models import WorkflowError

if TYPE_CHECKING:
    from .assembly import ChapterAssembly

_FILES = ("chapter.txt", "assembly.json", "manifest.json")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _absolute_output(output: Path) -> Path:
    if not isinstance(output, Path) or ".." in output.parts:
        raise WorkflowError("INVALID_ASSEMBLY_BUNDLE_PATH")
    result = output.absolute()
    if not result.name or "\0" in str(result):
        raise WorkflowError("INVALID_ASSEMBLY_BUNDLE_PATH")
    str(result).encode("utf-8")
    return result


def _normalized(path: Path) -> str:
    return unicodedata.normalize("NFC", str(path.resolve())).casefold()


def _reserved(
    output: Path,
    paths: tuple[Path, ...],
    directories: tuple[Path, ...],
) -> None:
    if (
        type(paths) is not tuple
        or type(directories) is not tuple
        or any(not isinstance(path, Path) for path in (*paths, *directories))
    ):
        raise WorkflowError("INVALID_ASSEMBLY_RESERVED_PATHS")
    protected = {
        _normalized(path.with_name(path.name + suffix))
        for path in paths
        for suffix in ("", "-wal", "-shm", "-journal")
    }
    protected.update(_normalized(path) for path in directories)
    for candidate in (output, *(output / name for name in _FILES)):
        identity = _normalized(candidate)
        if any(
            identity == reserved or identity.startswith(reserved + os.sep)
            for reserved in protected
        ):
            raise WorkflowError("ASSEMBLY_BUNDLE_RESERVED_PATH")


def _parent_descriptor(path: Path, *, create: bool) -> int:
    """Walk using directory capabilities; never follow a path component link."""
    descriptor = os.open(path.anchor, _DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:-1]:
            try:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                os.fsync(descriptor)
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _private_directory(descriptor: int) -> tuple[int, int]:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise WorkflowError("ASSEMBLY_BUNDLE_NOT_PRIVATE")
    return info.st_dev, info.st_ino


def _open_directory(path: Path) -> int:
    parent = _parent_descriptor(path, create=False)
    try:
        descriptor = os.open(path.name, _DIRECTORY_FLAGS, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        _private_directory(descriptor)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _new_directory(path: Path) -> int:
    parent = _parent_descriptor(path, create=True)
    try:
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            raise WorkflowError("ASSEMBLY_BUNDLE_ALREADY_EXISTS") from None
        os.fsync(parent)
        descriptor = os.open(path.name, _DIRECTORY_FLAGS, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        _private_directory(descriptor)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _same_directory(path: Path, descriptor: int) -> None:
    actual = _open_directory(path)
    try:
        if _private_directory(actual) != _private_directory(descriptor):
            raise WorkflowError("ASSEMBLY_BUNDLE_DIRECTORY_CHANGED")
    finally:
        os.close(actual)


def _private_file(info: os.stat_result) -> tuple[int, int, int, int, int]:
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise WorkflowError("ASSEMBLY_BUNDLE_FILE_NOT_PRIVATE")
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _read_file(directory: int, name: str, expected: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
        dir_fd=directory,
    )
    try:
        before = _private_file(os.fstat(descriptor))
        if before[2] != len(expected):
            raise WorkflowError("ASSEMBLY_BUNDLE_CONTENT_MISMATCH")
        parts: list[bytes] = []
        remaining = len(expected) + 1
        while remaining:
            part = os.read(descriptor, min(remaining, 1024 * 1024))
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        if (
            b"".join(parts) != expected
            or _private_file(os.fstat(descriptor)) != before
            or _private_file(os.stat(name, dir_fd=directory, follow_symlinks=False))
            != before
        ):
            raise WorkflowError("ASSEMBLY_BUNDLE_CONTENT_MISMATCH")
    finally:
        os.close(descriptor)


def _inspect(directory: int, payloads: dict[str, bytes]) -> None:
    _private_directory(directory)
    if set(os.listdir(directory)) != set(payloads):
        raise WorkflowError("ASSEMBLY_BUNDLE_FILE_SET_MISMATCH")
    for name, raw in payloads.items():
        _read_file(directory, name, raw)
    if set(os.listdir(directory)) != set(payloads):
        raise WorkflowError("ASSEMBLY_BUNDLE_FILE_SET_MISMATCH")


def _write_file(directory: int, name: str, raw: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=directory,
    )
    try:
        _private_file(os.fstat(descriptor))
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise WorkflowError("ASSEMBLY_BUNDLE_WRITE_FAILED")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory)


def _payloads(assembly: ChapterAssembly) -> dict[str, bytes]:
    from .assembly import ChapterAssembly

    if type(assembly) is not ChapterAssembly:
        raise WorkflowError("INVALID_CHAPTER_ASSEMBLY")
    prose, payload = assembly.prose, assembly.payload_bytes()
    if (
        type(prose) is not bytes
        or type(payload) is not bytes
        or sha256(prose).hexdigest() != assembly.prose_hash
        or sha256(payload).hexdigest() != assembly.record_hash
    ):
        raise WorkflowError("INVALID_CHAPTER_ASSEMBLY")
    decode_canonical(payload)
    files = {"chapter.txt": prose, "assembly.json": payload}
    manifest = canonical_bytes(
        {
            "record_type": "offline_chapter_assembly_bundle",
            "schema_version": "1.0",
            "maximum_artifact_state": "DRAFT",
            "accepted": False,
            "assembly_hash": assembly.record_hash,
            "files": {
                name: {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
                for name, raw in files.items()
            },
        }
    )
    return {**files, "manifest.json": manifest}


def write_assembly_bundle(
    assembly: ChapterAssembly,
    output: Path,
    *,
    reserved_paths: tuple[Path, ...],
    reserved_directories: tuple[Path, ...],
    before_manifest: Callable[[], None] | None = None,
) -> None:
    """Create a new bundle; source revalidation precedes the completion marker."""
    descriptor: int | None = None
    try:
        payloads = _payloads(assembly)
        path = _absolute_output(output)
        _reserved(path, reserved_paths, reserved_directories)
        if before_manifest is not None and not callable(before_manifest):
            raise WorkflowError("INVALID_ASSEMBLY_MANIFEST_CALLBACK")
        descriptor = _new_directory(path)
        _same_directory(path, descriptor)
        first = {name: payloads[name] for name in _FILES[:2]}
        for name, raw in first.items():
            _same_directory(path, descriptor)
            _write_file(descriptor, name, raw)
        _inspect(descriptor, first)
        if before_manifest is not None:
            before_manifest()
        _same_directory(path, descriptor)
        _inspect(descriptor, first)
        _write_file(descriptor, "manifest.json", payloads["manifest.json"])
        _same_directory(path, descriptor)
        _inspect(descriptor, payloads)
        _same_directory(path, descriptor)
    except WorkflowError:
        raise
    except (OSError, ValueError, UnicodeError, RuntimeError):
        raise WorkflowError("ASSEMBLY_BUNDLE_WRITE_FAILED") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def verify_assembly_bundle(
    assembly: ChapterAssembly,
    output: Path,
    *,
    reserved_paths: tuple[Path, ...],
    reserved_directories: tuple[Path, ...],
) -> None:
    """Read only; trust neither a bundle's manifest nor its claimed identities."""
    descriptor: int | None = None
    try:
        payloads = _payloads(assembly)
        path = _absolute_output(output)
        _reserved(path, reserved_paths, reserved_directories)
        descriptor = _open_directory(path)
        _same_directory(path, descriptor)
        _inspect(descriptor, payloads)
        _same_directory(path, descriptor)
    except WorkflowError:
        raise
    except (OSError, ValueError, UnicodeError, RuntimeError):
        raise WorkflowError("ASSEMBLY_BUNDLE_VERIFY_FAILED") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
