"""Emit the Runtime Execution Receipt for the current execution proof."""

from examples.proof_of_execution import run_proof
from tuc import (
    RuntimeExecutionReceiptReport,
    build_runtime_execution_receipt_report,
    build_runtime_input_manifest_report,
    build_runtime_output_manifest_report,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_execution_receipt_report,
)


def build_execution_receipt_report() -> RuntimeExecutionReceiptReport:
    """Return the current proof-of-execution receipt report."""

    proof = run_proof()
    graph = proof.compiled.hac_ir.graph
    tensor_store = build_runtime_tensor_store_evidence_report(graph, proof.execution)
    input_manifest = build_runtime_input_manifest_report(graph, proof.execution)
    output_manifest = build_runtime_output_manifest_report(graph, proof.execution)
    return build_runtime_execution_receipt_report(
        proof.execution,
        tensor_store,
        input_manifest,
        output_manifest,
        proof.correctness,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Execution Receipt report."""

    return dump_runtime_execution_receipt_report(build_execution_receipt_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
