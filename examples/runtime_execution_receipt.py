"""Emit the Runtime Execution Receipt for the current execution proof."""

from typing import NamedTuple

from examples.proof_of_execution import run_proof
from tuc import (
    RuntimeExecutionReceiptReport,
    RuntimeExecutionResult,
    RuntimeInputManifestReport,
    RuntimeOutputContractReport,
    RuntimeOutputManifestReport,
    RuntimePublicOutputBundle,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceReport,
    build_runtime_execution_receipt_report,
    build_runtime_input_manifest_report,
    build_runtime_output_contract_report,
    build_runtime_output_manifest_report,
    build_runtime_public_output_bundle,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_execution_receipt_report,
)

PROOF_OUTPUT_ALIASES = {"public_activated": "activated"}


class ExecutionReceiptEvidenceReports(NamedTuple):
    """Evidence reports required to close one proof-of-execution receipt."""

    execution: RuntimeExecutionResult
    tensor_store: RuntimeTensorStoreEvidenceReport
    input_manifest: RuntimeInputManifestReport
    output_manifest: RuntimeOutputManifestReport
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    reference_correctness: RuntimeReferenceCorrectnessReport


def build_execution_receipt_evidence_reports() -> ExecutionReceiptEvidenceReports:
    """Return metadata-only evidence reports for the execution proof."""

    proof = run_proof()
    graph = proof.compiled.hac_ir.graph
    tensor_store = build_runtime_tensor_store_evidence_report(
        graph,
        proof.compiled.partition_plan,
        proof.execution,
    )
    input_manifest = build_runtime_input_manifest_report(graph, proof.execution)
    output_manifest = build_runtime_output_manifest_report(graph, proof.execution)
    output_contract = build_runtime_output_contract_report(
        graph,
        proof.execution,
        PROOF_OUTPUT_ALIASES,
    )
    public_output_bundle = build_runtime_public_output_bundle(
        proof.execution,
        output_contract,
    )
    return ExecutionReceiptEvidenceReports(
        execution=proof.execution,
        tensor_store=tensor_store,
        input_manifest=input_manifest,
        output_manifest=output_manifest,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        reference_correctness=proof.correctness,
    )


def build_execution_receipt_report() -> RuntimeExecutionReceiptReport:
    """Return the current proof-of-execution receipt report."""

    evidence = build_execution_receipt_evidence_reports()
    return build_runtime_execution_receipt_report(
        evidence.execution,
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Execution Receipt report."""

    return dump_runtime_execution_receipt_report(build_execution_receipt_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
