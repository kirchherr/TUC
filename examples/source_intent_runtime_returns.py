"""Resolve Source Intent public returns through runtime public outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from examples.source_intent_return_semantics import build_source_intent_return_data
from tuc import (
    CompilationResult,
    ComputeGraph,
    RuntimeExecutionResult,
    RuntimeOutputContractReport,
    RuntimePublicOutputBundle,
    SourceIntentModule,
    SourceIntentRuntimeReturnsReport,
    build_runtime_output_contract_report,
    build_runtime_public_output_bundle,
    build_source_intent_runtime_returns_report,
    compile_graph,
    dump_source_intent_runtime_returns_report,
    execute_graph,
    source_intent_from_mapping,
    source_intent_return_aliases,
    source_intent_to_triton_metadata,
)
from tuc.backends import LinearAlgebraSimulatorBackend

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SourceIntentRuntimeReturnsEvidence:
    """Runtime evidence derived from Source Intent explicit public returns."""

    module: SourceIntentModule
    graph: ComputeGraph
    compiled: CompilationResult
    execution: RuntimeExecutionResult
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    runtime_returns: SourceIntentRuntimeReturnsReport


def runtime_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for the Source Intent return graph."""

    return {
        "a": np.array(
            [
                [1.0, -2.0, 0.5, 3.0, 0.0, 1.5, -1.0, 2.0],
                [0.0, 1.0, -1.0, 2.0, 3.0, -0.5, 1.5, -2.0],
                [2.0, 0.5, 1.0, -1.5, 0.5, 2.5, -3.0, 1.0],
                [-1.0, 2.0, 0.0, 1.0, -2.0, 1.0, 0.5, 3.0],
            ],
            dtype=np.float64,
        ),
        "b": np.array(
            [
                [1.0, -1.0],
                [2.0, 0.5],
                [-1.0, 3.0],
                [0.5, -2.0],
                [1.5, 1.0],
                [-0.5, 0.25],
                [2.5, -1.5],
                [0.0, 2.0],
            ],
            dtype=np.float64,
        ),
    }


def run_evidence() -> SourceIntentRuntimeReturnsEvidence:
    """Compile, execute, and link Source Intent returns to runtime outputs."""

    module = source_intent_from_mapping(build_source_intent_return_data())
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, runtime_inputs())
    aliases = source_intent_return_aliases(module)
    output_contract = build_runtime_output_contract_report(
        compiled.hac_ir.graph,
        execution,
        aliases,
    )
    public_output_bundle = build_runtime_public_output_bundle(execution, output_contract)
    runtime_returns = build_source_intent_runtime_returns_report(
        module,
        compiled.hac_ir.graph,
        execution,
    )
    return SourceIntentRuntimeReturnsEvidence(
        module=module,
        graph=compiled.hac_ir.graph,
        compiled=compiled,
        execution=execution,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        runtime_returns=runtime_returns,
    )


def build_report() -> str:
    """Return stable Source Intent runtime returns evidence."""

    return dump_source_intent_runtime_returns_report(run_evidence().runtime_returns)


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
