"""Emit portfolio-level metadata-only backend equivalence evidence."""

from __future__ import annotations

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from examples.runtime_vector_backend_equivalence import (
    build_vector_backend_equivalence_report,
)
from tuc import (
    RuntimeBackendEquivalencePortfolioReport,
    build_runtime_backend_equivalence_portfolio_report,
    dump_runtime_backend_equivalence_portfolio_report,
)

RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID = (
    "runtime_backend_equivalence_portfolio"
)


def build_backend_equivalence_portfolio_report() -> (
    RuntimeBackendEquivalencePortfolioReport
):
    """Aggregate the current trusted backend-equivalence slices."""

    return build_runtime_backend_equivalence_portfolio_report(
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
        (
            build_backend_equivalence_report(),
            build_vector_backend_equivalence_report(),
            build_mixed_backend_equivalence_report(),
        ),
    )


def build_report() -> str:
    """Return the stable serialized backend-equivalence portfolio report."""

    return dump_runtime_backend_equivalence_portfolio_report(
        build_backend_equivalence_portfolio_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
