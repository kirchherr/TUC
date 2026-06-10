from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from examples.proof_of_execution import build_graph, proof_inputs
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph
from tuc.runtime import execute_graph

_GOLDEN_TRACE = (
    Path(__file__).parent / "golden" / "execution_traces" / "proof_of_execution.txt"
)


def test_runtime_executor_executes_compiled_graph_and_trace_matches_golden() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, proof_inputs())

    assert_allclose(execution.output_for("activated"), np.array([0.0, 1.75]))
    assert execution.trace.dump() == _GOLDEN_TRACE.read_text(encoding="utf-8").rstrip(
        "\n"
    )


def test_runtime_executor_rejects_missing_input() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs.pop("rhs")

    with pytest.raises(ValueError, match="missing inputs: rhs"):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)


def test_runtime_executor_rejects_unexpected_input() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs["projection"] = np.zeros((2, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="unexpected inputs: projection"):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)


def test_runtime_executor_rejects_non_plain_input_mapping() -> None:
    class CustomInputs(dict[str, object]):
        pass

    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    with pytest.raises(TypeError, match="plain mapping"):
        execute_graph(
            compiled.hac_ir.graph,
            compiled.partition_plan,
            CustomInputs(proof_inputs()),
        )


def test_runtime_executor_rejects_partition_plan_mismatch() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    bad_plan = replace(
        compiled.partition_plan,
        assignments=compiled.partition_plan.assignments[:-1],
    )

    with pytest.raises(ValueError, match="partition plan must match graph operations"):
        execute_graph(compiled.hac_ir.graph, bad_plan, proof_inputs())


def test_runtime_executor_rejects_output_shape_mismatch() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    bad_activation = replace(
        compiled.hac_ir.graph.operations[2],
        outputs=(replace(compiled.hac_ir.graph.operations[2].outputs[0], shape=(3,)),),
    )
    bad_graph = ComputeGraph(
        name=compiled.hac_ir.graph.name,
        operations=(
            compiled.hac_ir.graph.operations[0],
            compiled.hac_ir.graph.operations[1],
            bad_activation,
        ),
    )

    with pytest.raises(ValueError, match="output shape mismatch"):
        execute_graph(bad_graph, compiled.partition_plan, proof_inputs())
