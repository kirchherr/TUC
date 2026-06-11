"""Emit metadata-only Runtime Public Output Bundle evidence."""

from __future__ import annotations

from examples.runtime_multi_output_evidence import run_evidence
from examples.runtime_output_contract import OUTPUT_ALIASES
from tuc import (
    RuntimePublicOutputBundle,
    build_runtime_output_contract_report,
    build_runtime_public_output_bundle,
    dump_runtime_public_output_bundle_report,
)


def build_public_output_bundle() -> RuntimePublicOutputBundle:
    """Return public output values resolved from the current output contract."""

    evidence = run_evidence()
    output_contract = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        OUTPUT_ALIASES,
    )
    return build_runtime_public_output_bundle(evidence.execution, output_contract)


def build_report() -> str:
    """Return stable metadata-only Runtime Public Output Bundle evidence."""

    return dump_runtime_public_output_bundle_report(build_public_output_bundle())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
