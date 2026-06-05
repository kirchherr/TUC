"""Run TUC's baseline reference-kernel benchmark harness."""

from __future__ import annotations

import argparse
import sys

from tuc.benchmarks import BenchmarkError, run_baseline_benchmarks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument(
        "--include-cuda",
        action="store_true",
        help="include CUDA capability status in the report",
    )
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="fail closed if CUDA benchmarks are unavailable",
    )
    args = parser.parse_args(argv)

    try:
        report = run_baseline_benchmarks(
            iterations=args.iterations,
            warmup=args.warmup,
            include_cuda=args.include_cuda,
            require_cuda=args.require_cuda,
        )
    except BenchmarkError as exc:
        print(f"benchmark error: {exc}", file=sys.stderr)
        return 2

    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
