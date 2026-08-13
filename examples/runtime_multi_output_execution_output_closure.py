"""Emit Runtime Execution Output Closure for the multi-output fixture."""

from __future__ import annotations

from typing import NamedTuple

from examples.runtime_multi_output_evidence import (
    build_graph,
    proof_inputs,
    reference_outputs,
)
from examples.runtime_output_contract import OUTPUT_ALIASES
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
    compile_graph,
    dump_runtime_execution_output_closure_report,
)
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.runtime import execute_graph


class MultiOutputExecutionClosureEvidenceReports(NamedTuple):
    """Evidence reports required to close multi-output execution outputs."""

    execution: RuntimeExecutionResult
    tensor_store: RuntimeTensorStoreEvidenceReport
    input_manifest: RuntimeInputManifestReport
    output_manifest: RuntimeOutputManifestReport
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    reference_correctness: RuntimeReferenceCorrectnessReport


def build_multi_output_execution_closure_evidence_reports() -> (
    MultiOutputExecutionClosureEvidenceReports
):
    """Return metadata-only evidence reports for the multi-output fixture."""

    graph = build_graph()
    inputs = proof_inputs()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    tensor_store = build_runtime_tensor_store_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        execution,
    )
    input_manifest = build_runtime_input_manifest_report(
        compiled.hac_ir.graph,
        execution,
    )
    output_manifest = build_runtime_output_manifest_report(
        compiled.hac_ir.graph,
        execution,
    )
    output_contract = build_runtime_output_contract_report(
        compiled.hac_ir.graph,
        execution,
        OUTPUT_ALIASES,
    )
    public_output_bundle = build_runtime_public_output_bundle(
        execution,
        output_contract,
    )
    reference_correctness = build_runtime_reference_correctness_report(
        compiled.hac_ir.graph,
        execution,
        reference_outputs(inputs),
    )
    return MultiOutputExecutionClosureEvidenceReports(
        execution=execution,
        tensor_store=tensor_store,
        input_manifest=input_manifest,
        output_manifest=output_manifest,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        reference_correctness=reference_correctness,
    )


def build_multi_output_execution_output_closure_report() -> (
    RuntimeExecutionOutputClosureReport
):
    """Return the multi-output public output closure report."""

    evidence = build_multi_output_execution_closure_evidence_reports()
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
    """Return stable serialized multi-output closure evidence."""

    return dump_runtime_execution_output_closure_report(
        build_multi_output_execution_output_closure_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
