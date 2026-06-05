"""Write SHA-256 checksums for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(artifact_dir: Path, output: Path) -> list[str]:
    resolved_output = output.resolve()
    artifacts = sorted(
        path
        for path in artifact_dir.iterdir()
        if path.is_file() and path.resolve() != resolved_output
    )
    lines = [f"{_sha256(path)}  {path.name}" for path in artifacts]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return lines


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path, help="Directory containing release artifacts.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/SHA256SUMS"),
        help="Checksum manifest output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_checksums(args.artifact_dir.resolve(), args.output)


if __name__ == "__main__":
    main()
