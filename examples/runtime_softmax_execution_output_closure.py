"""Emit Runtime Execution Output Closure for the softmax proof fixture."""

from __future__ import annotations

from typing import NamedTuple

from examples.proof_of_softmax import run_proof
from tuc import (
    RuntimeExecutionOutputClosureReport,
    RuntimeExecutionResult,
    RuntimeInputManifestReport,
    RuntimeOutputContractReport,
    RuntimeOutputManifestReport,
    RuntimePublicOutputBundle,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceReport,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_output_closure_report,
    build_runtime_execution_receipt_report,
    build_runtime_input_manifest_report,
    build_runtime_output_contract_report,
    build_runtime_output_manifest_report,
    build_runtime_public_output_bundle,
    build_runtime_reference_correctness_report,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_execution_output_closure_report,
)

SOFTMAX_OUTPUT_ALIASES = {"public_probabilities": "probabilities"}


class SoftmaxExecutionClosureEvidenceReports(NamedTuple):
    """Evidence reports required to close softmax execution outputs."""

    execution: RuntimeExecutionResult
    tensor_store: RuntimeTensorStoreEvidenceReport
    input_manifest: RuntimeInputManifestReport
    output_manifest: RuntimeOutputManifestReport
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    reference_correctness: RuntimeReferenceCorrectnessReport


def build_softmax_execution_closure_evidence_reports() -> (
    SoftmaxExecutionClosureEvidenceReports
):
    """Return metadata-only evidence reports for the softmax proof fixture."""

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
        SOFTMAX_OUTPUT_ALIASES,
    )
    public_output_bundle = build_runtime_public_output_bundle(
        proof.execution,
        output_contract,
    )
    reference_correctness = build_runtime_reference_correctness_report(
        graph,
        proof.execution,
        {"probabilities": proof.reference},
    )
    return SoftmaxExecutionClosureEvidenceReports(
        execution=proof.execution,
        tensor_store=tensor_store,
        input_manifest=input_manifest,
        output_manifest=output_manifest,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        reference_correctness=reference_correctness,
    )


def build_softmax_execution_output_closure_report() -> (
    RuntimeExecutionOutputClosureReport
):
    """Return the softmax public output closure report."""

    evidence = build_softmax_execution_closure_evidence_reports()
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
    """Return stable serialized softmax closure evidence."""

    return dump_runtime_execution_output_closure_report(
        build_softmax_execution_output_closure_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
