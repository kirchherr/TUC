"""Emit Runtime Planning Explanation evidence for mixed accelerator placement."""

from __future__ import annotations

try:
    from examples.runtime_planning_explanation import (
        build_mixed_backend_equivalence_runtime_planning_explanation_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_planning_explanation import (
        build_mixed_backend_equivalence_runtime_planning_explanation_report,
    )

from tuc import dump_runtime_planning_explanation_report


def build_report() -> str:
    """Return the stable serialized mixed planning explanation report."""

    return dump_runtime_planning_explanation_report(
        build_mixed_backend_equivalence_runtime_planning_explanation_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
