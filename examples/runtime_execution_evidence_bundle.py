"""Emit the Runtime Execution Evidence Bundle for the current execution proof."""

from examples.runtime_execution_receipt import build_execution_receipt_evidence_reports
from tuc import (
    RuntimeExecutionEvidenceBundleReport,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_receipt_report,
    dump_runtime_execution_evidence_bundle_report,
)


def build_execution_evidence_bundle_report() -> RuntimeExecutionEvidenceBundleReport:
    """Return the current proof-of-execution evidence bundle report."""

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
    return build_runtime_execution_evidence_bundle_report(
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
        receipt,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Execution Evidence Bundle report."""

    return dump_runtime_execution_evidence_bundle_report(
        build_execution_evidence_bundle_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
