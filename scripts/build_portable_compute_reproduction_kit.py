"""Build the deterministic Objective Delta reproduction kit."""

from __future__ import annotations

import argparse
from pathlib import Path

from tuc.portable_compute_reproduction import build_portable_compute_reproduction_kit


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--consumer",
        type=Path,
        default=Path("integration/objective_delta"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/tuc-objective-delta-reproduction-kit-v0.zip"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_portable_compute_reproduction_kit(args.consumer, args.output)


if __name__ == "__main__":
    main()
