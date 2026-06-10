from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from examples.proof_of_execution import build_graph, proof_inputs
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, OperationKind
from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE,
    TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT,
    TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT,
    RuntimeBackendExecutorContract,
    dump_trusted_runtime_executor_contracts,
    execute_graph,
    trusted_runtime_executor_contracts,
    trusted_runtime_executor_registry,
)

_GOLDEN_TRACE = (
    Path(__file__).parent / "golden" / "execution_traces" / "proof_of_execution.txt"
)
_GOLDEN_BACKEND_CONTRACTS = (
    Path(__file__).parent
    / "golden"
    / "runtime_backend_contracts"
    / "trusted_runtime_executor_registry.txt"
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


def test_runtime_executor_uses_trusted_registry_for_planned_backends() -> None:
    registry = trusted_runtime_executor_registry()

    assert sorted(registry) == ["linear-sim", "reference-cpu"]


def test_trusted_runtime_executor_contracts_are_stable_and_execution_free() -> None:
    contracts = trusted_runtime_executor_contracts()

    assert tuple(contract.backend_name for contract in contracts) == (
        "linear-sim",
        "reference-cpu",
    )
    assert contracts[0].supported_ops == frozenset(
        {OperationKind.MATMUL, OperationKind.REDUCTION}
    )
    assert contracts[1].supported_ops == frozenset(OperationKind)
    for contract in contracts:
        assert contract.backend_contract == TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT
        assert contract.execution_mode == TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE
        assert contract.input_contract == TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
        assert contract.output_contract == TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT
        assert contract.blocked_execution_surfaces == (
            RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        )
        assert contract.external_artifacts == "forbidden"
        assert contract.device_access == "forbidden"


def test_trusted_runtime_executor_contract_dump_matches_golden() -> None:
    assert dump_trusted_runtime_executor_contracts() == _GOLDEN_BACKEND_CONTRACTS.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_runtime_backend_executor_contract_rejects_untrusted_execution_mode() -> None:
    with pytest.raises(ValueError, match="execution mode"):
        RuntimeBackendExecutorContract(
            backend_name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
            execution_mode="artifact_jit",
        )


def test_runtime_backend_executor_contract_rejects_weakened_security_boundary() -> None:
    with pytest.raises(ValueError, match="blocked execution surfaces"):
        RuntimeBackendExecutorContract(
            backend_name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
            blocked_execution_surfaces=("network_access",),
        )


def test_runtime_backend_executor_contract_rejects_external_artifacts() -> None:
    with pytest.raises(ValueError, match="external artifacts"):
        RuntimeBackendExecutorContract(
            backend_name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
            external_artifacts="allowed",
        )


def test_runtime_executor_rejects_missing_trusted_executor() -> None:
    graph = build_graph()
    compiled = compile_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability],
        fallback_backend="unknown-executor",
    )

    with pytest.raises(ValueError, match="no trusted executor"):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, proof_inputs())


def test_runtime_executor_rejects_unsupported_executor_operation() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    activation_assignment = replace(
        compiled.partition_plan.assignments[2],
        backend_name="linear-sim",
    )
    bad_plan = replace(
        compiled.partition_plan,
        assignments=(
            compiled.partition_plan.assignments[0],
            compiled.partition_plan.assignments[1],
            activation_assignment,
        ),
    )

    with pytest.raises(ValueError, match="does not support"):
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
