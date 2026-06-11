"""Emit the Runtime Output Contract for the multi-output runtime fixture."""

from __future__ import annotations

from examples.runtime_multi_output_evidence import run_evidence
from tuc import (
    RuntimeOutputContractReport,
    build_runtime_output_contract_report,
    dump_runtime_output_contract_report,
)

OUTPUT_ALIASES = {
    "api_positive_projection": "positive_projection",
    "api_row_sums": "row_sum",
}


def build_output_contract_report() -> RuntimeOutputContractReport:
    """Return public output aliases resolved against terminal runtime outputs."""

    evidence = run_evidence()
    return build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        OUTPUT_ALIASES,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Output Contract report."""

    return dump_runtime_output_contract_report(build_output_contract_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
