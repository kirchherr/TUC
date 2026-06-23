"""Emit Runtime Execution Output Closure Report v0."""

from examples.runtime_execution_receipt import build_execution_receipt_evidence_reports
from tuc import (
    RuntimeExecutionOutputClosureReport,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_output_closure_report,
    build_runtime_execution_receipt_report,
    dump_runtime_execution_output_closure_report,
)


def build_execution_output_closure_report() -> RuntimeExecutionOutputClosureReport:
    """Return the current proof-of-execution public output closure report."""

    evidence = build_execution_receipt_evidence_reports()
    receipt = build_runtime_execution_receipt_report(
        evidence.execution,
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
    )
    bundle = build_runtime_execution_evidence_bundle_report(
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
        receipt,
    )
    return build_runtime_execution_output_closure_report(
        evidence.output_contract,
        evidence.public_output_bundle,
        receipt,
        bundle,
    )


def build_report() -> str:
    """Return stable serialized Runtime Execution Output Closure evidence."""

    return dump_runtime_execution_output_closure_report(
        build_execution_output_closure_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
