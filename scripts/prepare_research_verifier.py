"""Prepare the fixed Linux GitHub verifier without installing or executing it.

Authenticate the complete official archive before parsing it, then copy only
the fixed, independently digest-pinned executable into a new private directory.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import stat
import sys
import tarfile
from hashlib import sha256
from pathlib import Path, PurePosixPath

VERSION = "2.106.0"
ARCHIVE_NAME = f"gh_{VERSION}_linux_amd64.tar.gz"
ARCHIVE_URL = f"https://github.com/cli/cli/releases/download/v{VERSION}/{ARCHIVE_NAME}"
ARCHIVE_BYTES = 15101741
ARCHIVE_SHA256 = "a476449fa9625413c54a3734eded62e9e480e49f421ff08e7f3b3879c059a033"
BINARY_BYTES = 41373856
BINARY_SHA256 = "8b9e0e460b7373a42296b83d2683b12af7f2c6e0c7007d01252fc066acbf83cb"
CHECKSUMS_SHA256 = "1822d8b8c11a6df22d90f4d3b81312aa7b1c3a45a38d6c22407f00ec0ad09a5f"
MEMBER = f"gh_{VERSION}_linux_amd64/bin/gh"
MAX_ARCHIVE = 32 * 1024**2
MAX_EXPANDED = 64 * 1024**2


class PreparationRejected(ValueError):
    """A fixed identity, filesystem or archive boundary failed."""


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii") + b"\n"


def authenticated_archive(path: Path) -> bytes:
    try:
        path = Path(os.path.abspath(path))
        for parent in (*reversed(path.parents), path):
            info = parent.lstat()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise PreparationRejected("file_boundary")
            if parent != path and not stat.S_ISDIR(info.st_mode):
                raise PreparationRejected("file_boundary")
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_ARCHIVE:
            raise PreparationRejected("file_boundary")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        flags |= getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                    or not 0 < opened.st_size <= MAX_ARCHIVE):
                raise PreparationRejected("file_boundary")
            data = stream.read(MAX_ARCHIVE + 1)
    except OSError:
        raise PreparationRejected("file_boundary") from None
    if len(data) != ARCHIVE_BYTES or sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise PreparationRejected("archive_digest")
    return data


def executable(data: bytes) -> bytes:
    if type(data) is not bytes or not 0 < len(data) <= MAX_ARCHIVE:
        raise PreparationRejected("archive_boundary")
    binary = None
    expanded = 0
    names: set[str] = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for info in archive:
                parts = PurePosixPath(info.name).parts
                expanded += info.size
                if (len(names) >= 1024 or info.name in names or not parts
                        or info.name.startswith("/") or ".." in parts
                        or "\\" in info.name or ":" in info.name
                        or info.size < 0 or expanded > MAX_EXPANDED
                        or not (info.isfile() or info.isdir()) or info.issparse()):
                    raise PreparationRejected("archive_boundary")
                names.add(info.name)
                if info.name == MEMBER:
                    if not info.isfile() or info.size != BINARY_BYTES:
                        raise PreparationRejected("executable_boundary")
                    source = archive.extractfile(info)
                    if source is None:
                        raise PreparationRejected("executable_boundary")
                    with source:
                        binary = source.read(BINARY_BYTES + 1)
    except (tarfile.TarError, EOFError, OSError):
        raise PreparationRejected("archive_boundary") from None
    if binary is None or len(binary) != BINARY_BYTES:
        raise PreparationRejected("executable_boundary")
    if (binary[:6] != b"\x7fELF\x02\x01" or binary[18:20] != b"\x3e\x00"
            or sha256(binary).hexdigest() != BINARY_SHA256):
        raise PreparationRejected("executable_digest")
    return binary


def prepare(archive: Path, output: Path) -> dict[str, object]:
    binary = executable(authenticated_archive(archive))
    try:
        if (not output.is_absolute() or output.exists() or output.is_symlink()
                or output.parent.resolve(strict=True) != output.parent):
            raise PreparationRejected("output_boundary")
        output.mkdir(mode=0o700)
        target = output / "gh"
        with target.open("xb") as stream:
            stream.write(binary)
        target.chmod(0o700)
        receipt: dict[str, object] = {
            "schema_version": "tuc.research_verifier_preparation.v0", "status": "PASS",
            "version": VERSION, "platform": "linux_amd64", "archive_url": ARCHIVE_URL,
            "archive_sha256": ARCHIVE_SHA256, "archive_bytes": ARCHIVE_BYTES,
            "executable_sha256": BINARY_SHA256, "executable_bytes": BINARY_BYTES,
            "vendor_checksums_sha256": CHECKSUMS_SHA256,
            "system_installation": False, "executable_run_by_preparation": False,
        }
        with (output / "tool.json").open("xb") as stream:
            stream.write(encoded(receipt))
        return receipt
    except OSError:
        raise PreparationRejected("output_boundary") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.archive, args.output)
    except PreparationRejected as error:
        sys.stdout.buffer.write(encoded({"status": "REJECTED", "reason": str(error)}))
        return 1
    sys.stdout.buffer.write(encoded(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
