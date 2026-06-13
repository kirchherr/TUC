"""Emit data-only membership policy for backend equivalence portfolio evidence."""

from __future__ import annotations

from tuc import (
    RuntimeBackendEquivalencePortfolioPolicyReport,
    build_default_runtime_backend_equivalence_portfolio_policy_report,
    dump_runtime_backend_equivalence_portfolio_policy_report,
)


def build_backend_equivalence_portfolio_policy_report() -> (
    RuntimeBackendEquivalencePortfolioPolicyReport
):
    """Return the current accepted backend-equivalence portfolio policy."""

    return build_default_runtime_backend_equivalence_portfolio_policy_report()


def build_report() -> str:
    """Return the stable serialized backend-equivalence portfolio policy."""

    return dump_runtime_backend_equivalence_portfolio_policy_report(
        build_backend_equivalence_portfolio_policy_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
