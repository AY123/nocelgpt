"""Private files and fail-closed terminal input for an authorized probe.

These helpers do not grant dispatch authority. The caller must validate the
fixed authorization before claiming files or requesting terminal input.
"""

from __future__ import annotations

import fcntl
import json
import os
import select
import stat
import termios
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from .models import GatewayError


def read_hidden_credential(
    *, deadline_at: str | None = None, tty_fd: int | None = None, kimi: bool = False
) -> str:
    """Read only a controllable /dev/tty; never fall back to stdin or env."""
    descriptor: int | None = None
    original: list[Any] | None = None
    restore_failed = False
    try:
        if tty_fd is None:
            descriptor = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY | os.O_CLOEXEC)
        elif type(tty_fd) is int:
            descriptor = os.dup(tty_fd)
            current = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY | os.O_CLOEXEC)
            try:
                if not os.isatty(current) or os.tcgetpgrp(descriptor) != os.tcgetpgrp(
                    current
                ):
                    raise GatewayError("Inherited terminal is not the controlling TTY")
            finally:
                os.close(current)
        else:
            raise GatewayError("Inherited terminal descriptor must be an integer")
        if not os.isatty(descriptor):
            raise GatewayError("Hidden terminal input unavailable")
        # The typed parent passes the same open-file description, so this lock
        # remains held until its final restore/close. Never explicitly unlock:
        # a child LOCK_UN would release the parent's shared lock as well.
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = termios.tcgetattr(descriptor)
        hidden = original.copy()
        hidden[3] = (int(hidden[3]) | termios.ICANON) & ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(descriptor, termios.TCSAFLUSH, hidden)
        actual = int(termios.tcgetattr(descriptor)[3])
        if actual & (termios.ECHO | termios.ECHONL) or not actual & termios.ICANON:
            raise GatewayError("Hidden terminal input unavailable")
        remaining = None
        if deadline_at is not None:
            deadline = datetime.fromisoformat(deadline_at)
            if deadline.tzinfo is None:
                raise GatewayError("Credential deadline must include a timezone")
            remaining = (deadline - datetime.now(UTC)).total_seconds()
            if remaining <= 0:
                raise GatewayError("Credential deadline elapsed")
        os.write(descriptor, b"Kimi API key: " if kimi else b"OpenAI API key: ")
        if not select.select([descriptor], [], [], remaining)[0]:
            raise GatewayError("Credential deadline elapsed")
        raw = os.read(descriptor, 4097)
        if not raw.endswith(b"\n") or len(raw) > 4096:
            raise GatewayError("Hidden terminal input incomplete")
        key = raw.rstrip(b"\r\n").decode("utf-8")
        if not key.strip() or any(ord(char) < 32 for char in key):
            raise GatewayError("Credential entry missing or invalid")
        return key
    except (OSError, termios.error, UnicodeError, ValueError):
        raise GatewayError("Hidden terminal input unavailable") from None
    finally:
        if descriptor is not None:
            if original is not None:
                try:
                    termios.tcsetattr(descriptor, termios.TCSAFLUSH, original)
                except (OSError, termios.error):
                    restore_failed = True
                try:
                    os.write(descriptor, b"\n")
                except OSError:
                    pass
            os.close(descriptor)
        if restore_failed:
            raise GatewayError("Terminal settings could not be restored") from None


def _directory_stat(directory: Path) -> os.stat_result:
    if not directory.is_absolute() or directory != directory.resolve(strict=True):
        raise GatewayError("Probe directory must be explicitly canonical")
    for ancestor in reversed((directory, *directory.parents)):
        entry = ancestor.lstat()
        if not stat.S_ISDIR(entry.st_mode):
            raise GatewayError("Probe directory ancestors cannot be symlinks")
    entry = directory.lstat()
    if entry.st_uid != os.getuid() or stat.S_IMODE(entry.st_mode) != 0o700:
        raise GatewayError("Probe directory requires current owner and mode0700")
    return entry


@dataclass(frozen=True, slots=True)
class PrivateProbeDirectory:
    directory: Path
    ledger: Path
    output: Path
    claim_path: Path
    _descriptor: int = field(repr=False)
    _identity: tuple[int, int] = field(repr=False)

    def _names(self) -> tuple[str, ...]:
        return (
            self.ledger.name,
            self.ledger.name + "-wal",
            self.ledger.name + "-shm",
            self.ledger.name + "-journal",
            self.output.name,
            self.claim_path.name,
        )

    def verify_files(self) -> None:
        """Check metadata only; never repair permissions or read prior results."""
        entry = _directory_stat(self.directory)
        held = os.fstat(self._descriptor)
        if (entry.st_dev, entry.st_ino) != self._identity or (
            held.st_dev,
            held.st_ino,
        ) != self._identity:
            raise GatewayError("Private probe directory identity changed")
        for name in self._names():
            try:
                entry = os.stat(name, dir_fd=self._descriptor, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if (
                not stat.S_ISREG(entry.st_mode)
                or entry.st_uid != os.getuid()
                or stat.S_IMODE(entry.st_mode) != 0o600
                or entry.st_nlink != 1
            ):
                raise GatewayError("Probe files require private regular mode0600")

    def _exclusive(self, path: Path) -> TextIO:
        self.verify_files()
        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=self._descriptor,
        )
        try:
            os.fsync(self._descriptor)
            return os.fdopen(descriptor, "w", encoding="utf-8")
        except BaseException:
            os.close(descriptor)
            raise

    def claim_authorization(self, authorization_id: str, attempt_id: str) -> None:
        """Consume the fixed authorization once, including failed TTY attempts."""
        if not authorization_id.strip() or not attempt_id.strip():
            raise GatewayError("Authorization and attempt identities are required")
        with self._exclusive(self.claim_path) as stream:
            json.dump(
                {
                    "kind": "PROBE_AUTHORIZATION_CLAIM",
                    "schema_version": "1.0",
                    "authorization_id": authorization_id,
                    "attempt_id": attempt_id,
                },
                stream,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(self._descriptor)

    def open_result(self) -> TextIO:
        return self._exclusive(self.output)


@contextmanager
def private_probe_directory(
    ledger: Path, output: Path, claim_path: Path
) -> Iterator[PrivateProbeDirectory]:
    """Require a precreated private canonical directory and restore umask."""
    paths = (ledger, output, claim_path)
    directory = ledger.parent
    if any(not path.is_absolute() or path.parent != directory for path in paths):
        raise GatewayError("Probe ledger, claim and result must share one directory")
    names = (
        ledger.name,
        ledger.name + "-wal",
        ledger.name + "-shm",
        ledger.name + "-journal",
        output.name,
        claim_path.name,
    )
    if len({unicodedata.normalize("NFC", name).casefold() for name in names}) != len(
        names
    ):
        raise GatewayError("Probe files cannot alias ledger or sidecar names")
    entry = _directory_stat(directory)
    descriptor = os.open(
        directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    previous_umask = os.umask(0o077)
    try:
        private = PrivateProbeDirectory(
            directory,
            ledger,
            output,
            claim_path,
            descriptor,
            (entry.st_dev, entry.st_ino),
        )
        private.verify_files()
        yield private
    finally:
        os.umask(previous_umask)
        os.close(descriptor)
