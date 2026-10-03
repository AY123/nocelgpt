"""Fetch the pinned Gitleaks release into a new local tools directory.

Hashes are from the official v8.21.2 release's checksums file:
https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_checksums.txt
This verifies downloaded bytes, not the repository's remote permission boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import subprocess
import tarfile
import urllib.request
from pathlib import Path

VERSION = "8.21.2"
ARCHIVES: dict[tuple[str, str], tuple[str, str]] = {
    ("Linux", "x86_64"): (
        "linux_x64",
        "5bc41815076e6ed6ef8fbecc9d9b75bcae31f39029ceb55da08086315316e3ba",
    ),
    ("Linux", "aarch64"): (
        "linux_arm64",
        "654c935542c89f565aabe7bf7c6c500830f116c114f0aeb509d2460c1ac2e6da",
    ),
    ("Darwin", "arm64"): (
        "darwin_arm64",
        "cad3de5dc9a4d5447d967a70a4d49499c557f04db028274cc324f9ff983f6502",
    ),
    ("Darwin", "x86_64"): (
        "darwin_x64",
        "5b42c6e4b1fd693eaeb2b5b7faa5f17a1434299d4deb2de63d4b2efd7c753128",
    ),
}


def archive_identity() -> tuple[str, str]:
    """Resolve the host platform against constants, never a self-signed receipt."""
    system = (platform.system(), platform.machine())
    if system not in ARCHIVES:
        raise ValueError("SCANNER_PLATFORM_UNSUPPORTED")
    suffix, expected = ARCHIVES[system]
    return f"gitleaks_{VERSION}_{suffix}.tar.gz", expected


def archive_url(archive_name: str) -> str:
    return f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/{archive_name}"


def fetch_archive(archive_name: str) -> bytes:
    url = archive_url(archive_name)
    with urllib.request.urlopen(url, timeout=30) as response:
        archive = response.read(20 * 1024 * 1024 + 1)
    if not isinstance(archive, bytes):
        raise ValueError("SCANNER_ARCHIVE_RESPONSE")
    return archive


def verified_archive_binary(archive: bytes, expected: str) -> bytes:
    """Verify official bytes and read only the single regular executable member."""
    if (
        len(archive) > 20 * 1024 * 1024
        or hashlib.sha256(archive).hexdigest() != expected
    ):
        raise ValueError("SCANNER_ARCHIVE_CHECKSUM")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
            members = [
                member for member in source.getmembers() if member.name == "gitleaks"
            ]
            if (
                len(members) != 1
                or not members[0].isfile()
                or members[0].size > 64 * 1024 * 1024
            ):
                raise ValueError("SCANNER_ARCHIVE_EXECUTABLE")
            stream = source.extractfile(members[0])
            if stream is None:
                raise ValueError("SCANNER_ARCHIVE_EXECUTABLE")
            with stream:
                binary = stream.read(64 * 1024 * 1024 + 1)
            if not binary or len(binary) != members[0].size:
                raise ValueError("SCANNER_ARCHIVE_EXECUTABLE")
            return binary
    except tarfile.TarError:
        raise ValueError("SCANNER_ARCHIVE_FORMAT") from None


def verify_cached_scanner(path: Path, *, migrate_missing_archive: bool = False) -> Path:
    """An archive digest and exact extracted bytes authorize reuse; sidecars do not."""
    path = path.absolute()
    output = path.parent
    if path.name != "gitleaks" or path.is_symlink() or output.is_symlink():
        raise ValueError("SCANNER_EXISTING_PATH")
    archive_name, expected = archive_identity()
    receipt_path = output / "bootstrap-scanners.json"
    archive_path = output / archive_name
    if receipt_path.is_symlink() or archive_path.is_symlink():
        raise ValueError("SCANNER_EXISTING_PATH")
    receipt = json.loads(receipt_path.read_text())
    if (
        not isinstance(receipt, dict)
        or receipt.get("version") != VERSION
        or receipt.get("record_type") != "pinned_scanner_bootstrap"
        or receipt.get("archive") != archive_name
    ):
        raise ValueError("SCANNER_EXISTING_RECEIPT")
    missing = not archive_path.exists()
    if missing and not migrate_missing_archive:
        raise ValueError("SCANNER_ARCHIVE_MISSING")
    archive = fetch_archive(archive_name) if missing else archive_path.read_bytes()
    binary = verified_archive_binary(archive, expected)
    if path.read_bytes() != binary:
        raise ValueError("SCANNER_EXISTING_BINARY_MISMATCH")
    # Migrate only an absent archive, after validating the existing binary. Never
    # overwrite a binary, old sidecar, or another process's newly created archive.
    if missing:
        with archive_path.open("xb") as handle:
            handle.write(archive)
    result = subprocess.run(
        [str(path), "version"], capture_output=True, timeout=15, check=False
    )
    if result.returncode or result.stdout.decode().strip().removeprefix("v") != VERSION:
        raise ValueError("SCANNER_EXISTING_VERSION")
    return path


def provision(output: Path, *, reuse_verified: bool = False) -> Path:
    """Retain the pinned archive and executable for independently checked reuse."""
    output = output.absolute()
    if output.exists() or output.is_symlink():
        if not reuse_verified or output.is_symlink():
            raise ValueError("SCANNER_OUTPUT_EXISTS")
        return verify_cached_scanner(output / "gitleaks", migrate_missing_archive=True)
    archive_name, expected = archive_identity()
    archive = fetch_archive(archive_name)
    binary = verified_archive_binary(archive, expected)
    output.mkdir(parents=True, exist_ok=False)
    (output / archive_name).write_bytes(archive)
    executable = output / "gitleaks"
    executable.write_bytes(binary)
    executable.chmod(0o755)
    receipt = {
        "record_type": "pinned_scanner_bootstrap",
        "version": VERSION,
        "archive": archive_name,
        "archive_sha256": expected,
        "source_url": archive_url(archive_name),
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
    }
    (output / "bootstrap-scanners.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--reuse-verified", action="store_true")
    args = parser.parse_args()
    try:
        executable = provision(args.output_dir, reuse_verified=args.reuse_verified)
    except (OSError, ValueError, tarfile.TarError) as exc:
        # Transport exceptions can contain proxy URLs; never print their text.
        print(json.dumps({"status": "FAIL", "error": type(exc).__name__}))
        return 1
    print(
        json.dumps(
            {"status": "PASS", "version": VERSION, "executable": str(executable)}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
