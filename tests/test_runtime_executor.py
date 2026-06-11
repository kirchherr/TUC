from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from examples.proof_of_execution import build_graph, proof_inputs
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import (
    ComputeGraph,
    ComputeOperation,
    LayoutKind,
    MemoryDomainKind,
    OperationKind,
    TensorRef,
)
from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE,
    TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT,
    TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT,
    Assignment,
    PartitionPlan,
    RuntimeBackendExecutorContract,
    RuntimeExecutionResult,
    RuntimeExecutionTrace,
    dump_runtime_execution_readiness,
    dump_trusted_runtime_executor_contracts,
    execute_graph,
    runtime_execution_readiness_report,
    trusted_runtime_executor_contracts,
    trusted_runtime_executor_registry,
)
from tuc.runtime.executor import RuntimeTensorStore, RuntimeValueRecord

_GOLDEN_TRACE = (
    Path(__file__).parent / "golden" / "execution_traces" / "proof_of_execution.txt"
)
_GOLDEN_BACKEND_CONTRACTS = (
    Path(__file__).parent
    / "golden"
    / "runtime_backend_contracts"
    / "trusted_runtime_executor_registry.txt"
)
_GOLDEN_READINESS = (
    Path(__file__).parent / "golden" / "execution_readiness" / "proof_of_execution.txt"
)


def _single_operation_plan(graph: ComputeGraph) -> PartitionPlan:
    operation = graph.operations[0]
    return PartitionPlan(
        graph_name=graph.name,
        assignments=(
            Assignment(
                operation_name=operation.name,
                backend_name="reference-cpu",
                reason="test",
                memory_domain=MemoryDomainKind.HOST_RAM,
                produced_layout=LayoutKind.ROW_MAJOR,
            ),
        ),
    )


def _reference_plan(graph: ComputeGraph) -> PartitionPlan:
    return PartitionPlan(
        graph_name=graph.name,
        assignments=tuple(
            Assignment(
                operation_name=operation.name,
                backend_name="reference-cpu",
                reason="test",
                memory_domain=MemoryDomainKind.HOST_RAM,
                produced_layout=LayoutKind.ROW_MAJOR,
            )
            for operation in graph.operations
        ),
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


def test_runtime_executor_rejects_input_shape_mismatch() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs["lhs"] = np.zeros((3, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="input shape mismatch for lhs"):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)


def test_runtime_executor_rejects_non_float64_input() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs["lhs"] = np.zeros((2, 3), dtype=np.float32)

    with pytest.raises(TypeError, match="input lhs dtype must be float64"):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)


def test_runtime_executor_rejects_non_finite_input() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs["lhs"] = inputs["lhs"].copy()
    inputs["lhs"][0, 0] = np.nan

    with pytest.raises(ValueError, match="input lhs must contain only finite values"):
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


def test_runtime_executor_stores_read_only_value_records() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    inputs["lhs"][0, 0] = 999.0

    assert execution.values["lhs"][0, 0] != 999.0
    assert execution.values["lhs"].flags.writeable is False
    assert execution.output_for("activated").flags.writeable is False


def test_runtime_value_record_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="shape mismatch"):
        RuntimeValueRecord(
            tensor_name="value",
            value=np.zeros((2, 2), dtype=np.float64),
            shape=(2,),
            dtype="float64",
            value_role="input",
        )


def test_runtime_tensor_store_rejects_duplicate_records() -> None:
    record = RuntimeValueRecord(
        tensor_name="value",
        value=np.zeros((2,), dtype=np.float64),
        shape=(2,),
        dtype="float64",
        value_role="input",
    )

    with pytest.raises(ValueError, match="duplicate value"):
        RuntimeTensorStore((record, record))


def test_runtime_execution_result_rejects_record_value_mismatch() -> None:
    record = RuntimeValueRecord(
        tensor_name="value",
        value=np.zeros((2,), dtype=np.float64),
        shape=(2,),
        dtype="float64",
        value_role="input",
    )

    with pytest.raises(ValueError, match="record values must match values"):
        RuntimeExecutionResult(
            values={"value": np.ones((2,), dtype=np.float64)},
            trace=RuntimeExecutionTrace(
                graph_name="record_mismatch",
                executor_contract=RUNTIME_EXECUTOR_CONTRACT,
                steps=(),
            ),
            records=(record,),
        )


def test_runtime_tensor_store_is_documented() -> None:
    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_EXECUTOR.md"),
        Path("docs/RUNTIME_TENSOR_STORE.md"),
        Path("rfcs/0105-runtime-tensor-store.md"),
    ):
        assert "Runtime Tensor Store" in path.read_text(encoding="utf-8")


def test_runtime_graph_topology_contract_is_documented() -> None:
    for path in (
        Path("docs/RUNTIME_EXECUTOR.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0107-runtime-graph-topology-contract.md"),
    ):
        assert "topology" in path.read_text(encoding="utf-8").lower()


def test_runtime_executor_rejects_partition_plan_mismatch() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    bad_plan = replace(
        compiled.partition_plan,
        assignments=compiled.partition_plan.assignments[:-1],
    )

    with pytest.raises(ValueError, match="partition plan must match graph operations"):
        execute_graph(compiled.hac_ir.graph, bad_plan, proof_inputs())


def test_runtime_readiness_rejects_non_topological_graph_order() -> None:
    mid = TensorRef("mid", (2,))
    x = TensorRef("x", (2,))
    y = TensorRef("y", (2,))
    graph = ComputeGraph(
        name="bad_runtime_order",
        operations=(
            ComputeOperation(
                name="consumer",
                kind=OperationKind.ELEMENTWISE,
                inputs=(mid,),
                outputs=(y,),
                attributes={"kernel": "relu"},
            ),
            ComputeOperation(
                name="producer",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(mid,),
                attributes={"kernel": "relu"},
            ),
        ),
    )

    with pytest.raises(ValueError, match="not topologically ordered"):
        runtime_execution_readiness_report(graph, _reference_plan(graph))


def test_runtime_readiness_rejects_duplicate_output_tensor_definitions() -> None:
    out = TensorRef("dup", (2,))
    graph = ComputeGraph(
        name="bad_duplicate_outputs",
        operations=(
            ComputeOperation(
                name="first",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (2,)),),
                outputs=(out,),
                attributes={"kernel": "relu"},
            ),
            ComputeOperation(
                name="second",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("y", (2,)),),
                outputs=(out,),
                attributes={"kernel": "relu"},
            ),
        ),
    )

    with pytest.raises(ValueError, match="duplicate output tensor definitions"):
        runtime_execution_readiness_report(graph, _reference_plan(graph))


def test_runtime_readiness_rejects_output_external_input_collision() -> None:
    graph = ComputeGraph(
        name="bad_external_collision",
        operations=(
            ComputeOperation(
                name="overwrite_input",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (2,)),),
                outputs=(TensorRef("x", (2,)),),
                attributes={"kernel": "relu"},
            ),
        ),
    )

    with pytest.raises(ValueError, match="output collides with external input"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_executor_uses_trusted_registry_for_planned_backends() -> None:
    registry = trusted_runtime_executor_registry()

    assert sorted(registry) == ["linear-sim", "reference-cpu", "systolic-sim"]


def test_runtime_execution_readiness_report_matches_golden() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    report = runtime_execution_readiness_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )

    assert tuple(step.operation_name for step in report.steps) == (
        "linear_projection",
        "row_reduction",
        "activation",
    )
    assert tuple(step.planned_backend for step in report.steps) == (
        "linear-sim",
        "linear-sim",
        "reference-cpu",
    )
    assert dump_runtime_execution_readiness(report) == _GOLDEN_READINESS.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_runtime_readiness_rejects_matmul_dimension_mismatch() -> None:
    graph = ComputeGraph(
        name="bad_matmul",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(TensorRef("a", (2, 3)), TensorRef("b", (4, 2))),
                outputs=(TensorRef("c", (2, 2)),),
            ),
        ),
    )

    with pytest.raises(ValueError, match="matmul input dimensions must agree"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_elementwise_output_shape_mismatch() -> None:
    graph = ComputeGraph(
        name="bad_elementwise",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (2,)),),
                outputs=(TensorRef("y", (3,)),),
                attributes={"kernel": "relu"},
            ),
        ),
    )

    with pytest.raises(ValueError, match="elementwise output shape mismatch"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_unsupported_elementwise_kernel() -> None:
    graph = ComputeGraph(
        name="bad_elementwise_kernel",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (2,)),),
                outputs=(TensorRef("y", (2,)),),
                attributes={"kernel": "sigmoid"},
            ),
        ),
    )

    with pytest.raises(ValueError, match="unsupported elementwise kernel"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_reduction_axis_out_of_bounds() -> None:
    graph = ComputeGraph(
        name="bad_reduction_axis",
        operations=(
            ComputeOperation(
                name="row_sum",
                kind=OperationKind.REDUCTION,
                inputs=(TensorRef("x", (2, 3)),),
                outputs=(TensorRef("y", (2,)),),
                attributes={"axis": 2},
            ),
        ),
    )

    with pytest.raises(ValueError, match="reduction axis is out of bounds"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_reduction_without_axis() -> None:
    graph = ComputeGraph(
        name="bad_reduction_without_axis",
        operations=(
            ComputeOperation(
                name="row_sum",
                kind=OperationKind.REDUCTION,
                inputs=(TensorRef("x", (2, 3)),),
                outputs=(TensorRef("y", (2,)),),
            ),
        ),
    )

    with pytest.raises(ValueError, match="reduction axis is required"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_scalar_reduction_output() -> None:
    graph = ComputeGraph(
        name="bad_scalar_reduction",
        operations=(
            ComputeOperation(
                name="total_sum",
                kind=OperationKind.REDUCTION,
                inputs=(TensorRef("x", (2,)),),
                outputs=(TensorRef("y", (1,)),),
                attributes={"axis": 0},
            ),
        ),
    )

    with pytest.raises(ValueError, match="reduction output would be scalar"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_reduction_output_shape_mismatch() -> None:
    graph = ComputeGraph(
        name="bad_reduction_output",
        operations=(
            ComputeOperation(
                name="row_sum",
                kind=OperationKind.REDUCTION,
                inputs=(TensorRef("x", (2, 3)),),
                outputs=(TensorRef("y", (3,)),),
                attributes={"axis": 1},
            ),
        ),
    )

    with pytest.raises(ValueError, match="reduction output shape mismatch"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_softmax_output_shape_mismatch() -> None:
    graph = ComputeGraph(
        name="bad_softmax_output",
        operations=(
            ComputeOperation(
                name="softmax",
                kind=OperationKind.SOFTMAX,
                inputs=(TensorRef("x", (2, 3)),),
                outputs=(TensorRef("y", (2,)),),
                attributes={"axis": 1},
            ),
        ),
    )

    with pytest.raises(ValueError, match="softmax output shape mismatch"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_runtime_readiness_rejects_softmax_axis_out_of_bounds() -> None:
    graph = ComputeGraph(
        name="bad_softmax_axis",
        operations=(
            ComputeOperation(
                name="softmax",
                kind=OperationKind.SOFTMAX,
                inputs=(TensorRef("x", (2, 3)),),
                outputs=(TensorRef("y", (2, 3)),),
                attributes={"axis": 2},
            ),
        ),
    )

    with pytest.raises(ValueError, match="softmax axis is out of bounds"):
        runtime_execution_readiness_report(graph, _single_operation_plan(graph))


def test_trusted_runtime_executor_contracts_are_stable_and_execution_free() -> None:
    contracts = trusted_runtime_executor_contracts()

    assert tuple(contract.backend_name for contract in contracts) == (
        "linear-sim",
        "reference-cpu",
        "systolic-sim",
    )
    assert contracts[0].supported_ops == frozenset(
        {OperationKind.MATMUL, OperationKind.REDUCTION}
    )
    assert contracts[1].supported_ops == frozenset(OperationKind)
    assert contracts[2].supported_ops == frozenset({OperationKind.MATMUL})
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

    with pytest.raises(ValueError, match="contract does not support operation"):
        runtime_execution_readiness_report(compiled.hac_ir.graph, bad_plan)

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


def test_runtime_executor_rejects_non_finite_output() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = proof_inputs()
    inputs["lhs"] = np.full((2, 3), 1e308, dtype=np.float64)
    inputs["rhs"] = np.full((3, 2), 1e308, dtype=np.float64)

    with np.errstate(over="ignore"), pytest.raises(
        ValueError,
        match="output projection must contain only finite values",
    ):
        execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
