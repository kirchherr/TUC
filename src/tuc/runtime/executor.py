"""Trusted in-process runtime executor for the prototype graph subset.

Runtime Executor v0 executes already-compiled graphs with deterministic
reference kernels. It is intentionally not a plugin system: it does not discover
backends, import modules, spawn subprocesses, access devices, load generated
artifacts, or execute user-provided code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import numpy as np
from numpy.typing import NDArray

from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.reference import (
    ElementwiseKernel,
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)
from tuc.runtime.partitioning import Assignment, PartitionPlan

RUNTIME_EXECUTOR_CONTRACT = "runtime_executor.trusted_backend.v0"
TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT = "runtime_backend_executor.trusted.v0"
TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE = "in_process_reference_kernel"
TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT = "runtime_executor.numpy_float64_inputs.v0"
TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT = (
    "runtime_executor.declared_shape_float64_output.v0"
)
TRUSTED_REFERENCE_EXECUTOR_BACKEND = "trusted-reference-kernel"
TRUSTED_RUNTIME_EXECUTOR_REGISTRY = "trusted_runtime_executor_registry.v0"
RUNTIME_VALUE_RECORD_CONTRACT = "runtime_value_record.internal.v0"
RUNTIME_TENSOR_STORE_CONTRACT = "runtime_tensor_store.internal.v0"
RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES = (
    "backend_plugin_discovery",
    "device_access",
    "dynamic_import",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "subprocess_execution",
)
MAX_RUNTIME_EXECUTION_VALUES = 4096
MAX_TRUSTED_RUNTIME_BACKEND_CONTRACTS = 64
_RUNTIME_VALUE_ROLES = frozenset({"input", "computed"})

FloatArray = NDArray[np.float64]

_TRACE_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class RuntimeBackendExecutorContract:
    """Pure-data execution contract for one trusted prototype runtime backend."""

    backend_name: str
    supported_ops: frozenset[OperationKind]
    backend_contract: str = TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT
    execution_mode: str = TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE
    input_contract: str = TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
    output_contract: str = TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    external_artifacts: str = "forbidden"
    device_access: str = "forbidden"
    status: str = "trusted"

    def __post_init__(self) -> None:
        _require_trace_name(self.backend_name, "runtime backend contract name")
        if self.backend_contract != TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT:
            raise ValueError(
                "runtime backend contract must use "
                f"{TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT!r}"
            )
        if self.execution_mode != TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE:
            raise ValueError("runtime backend execution mode is not trusted for v0")
        if self.input_contract != TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT:
            raise ValueError("runtime backend input contract is not trusted for v0")
        if self.output_contract != TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT:
            raise ValueError("runtime backend output contract is not trusted for v0")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime backend blocked execution surfaces must match Runtime Executor v0"
            )
        if self.external_artifacts != "forbidden":
            raise ValueError("runtime backend external artifacts must be forbidden")
        if self.device_access != "forbidden":
            raise ValueError("runtime backend device access must be forbidden")
        if self.status != "trusted":
            raise ValueError("runtime backend contract status must be trusted")
        _require_operation_set(
            self.supported_ops,
            "runtime backend contract supported_ops",
        )

    def dump_line(self) -> str:
        """Render one stable backend-contract line."""

        return _format_backend_contract(self)


@dataclass(frozen=True)
class TrustedRuntimeBackendExecutor:
    """Trusted in-repository executor for one prototype backend name."""

    name: str
    supported_ops: frozenset[OperationKind]

    def __post_init__(self) -> None:
        _require_trace_name(self.name, "executor name")
        _require_operation_set(self.supported_ops, "executor supported_ops")

    @property
    def contract(self) -> RuntimeBackendExecutorContract:
        """Return the pure-data contract for this trusted executor."""

        return RuntimeBackendExecutorContract(
            backend_name=self.name,
            supported_ops=self.supported_ops,
        )

    def execute(
        self,
        operation: ComputeOperation,
        values: Mapping[str, FloatArray],
    ) -> FloatArray:
        """Execute one operation with trusted reference semantics."""

        if operation.kind not in self.supported_ops:
            raise ValueError(
                f"executor {self.name!r} does not support {operation.kind.value!r}"
            )
        return _execute_reference_operation(operation, values)


@dataclass(frozen=True)
class RuntimeExecutionStep:
    """One executed runtime operation and its observable execution facts."""

    operation_name: str
    operation_kind: OperationKind
    planned_backend: str
    executor_backend: str
    input_tensors: tuple[str, ...]
    output_tensors: tuple[str, ...]
    output_shapes: tuple[tuple[int, ...], ...]
    output_dtypes: tuple[str, ...]
    status: str = "executed"

    def __post_init__(self) -> None:
        _require_trace_name(self.operation_name, "operation_name")
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("operation_kind must be OperationKind")
        _require_trace_name(self.planned_backend, "planned_backend")
        _require_trace_name(self.executor_backend, "executor_backend")
        _require_name_sequence(self.input_tensors, "input_tensors")
        _require_name_sequence(self.output_tensors, "output_tensors")
        if len(self.output_shapes) != len(self.output_tensors):
            raise ValueError("output_shapes must match output_tensors")
        if len(self.output_dtypes) != len(self.output_tensors):
            raise ValueError("output_dtypes must match output_tensors")
        for shape in self.output_shapes:
            _require_shape(shape)
        _require_name_sequence(self.output_dtypes, "output_dtypes")
        if self.status != "executed":
            raise ValueError("runtime execution step status must be executed")


@dataclass(frozen=True)
class RuntimeExecutionTrace:
    """Deterministic execution trace for one graph run."""

    graph_name: str
    executor_contract: str
    steps: tuple[RuntimeExecutionStep, ...]
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _require_trace_name(self.graph_name, "graph_name")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError(
                "runtime execution trace requires contract "
                f"{RUNTIME_EXECUTOR_CONTRACT!r}"
            )
        if len(self.steps) > MAX_RUNTIME_EXECUTION_VALUES:
            raise ValueError("runtime execution trace step count exceeds limit")
        _require_name_sequence(
            self.blocked_execution_surfaces,
            "blocked_execution_surfaces",
        )

    def dump(self) -> str:
        """Render a stable execution trace."""

        lines = [f"runtime.execution_trace @{self.graph_name} {{"]
        lines.append(f'  executor_contract = "{self.executor_contract}"')
        lines.append(
            f'  trusted_executor_registry = "{TRUSTED_RUNTIME_EXECUTOR_REGISTRY}"'
        )
        lines.append(
            "  blocked_execution_surfaces = "
            f'"{",".join(self.blocked_execution_surfaces)}"'
        )
        lines.append("  steps {")
        for step in self.steps:
            lines.append(f"    {_format_step(step)}")
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)


@dataclass(frozen=True)
class RuntimeExecutionReadinessStep:
    """One pre-execution contract check for a planned runtime operation."""

    operation_name: str
    operation_kind: OperationKind
    planned_backend: str
    backend_contract: str
    supported_ops: frozenset[OperationKind]
    status: str = "ready"
    reason: str = "contract_allows_operation"

    def __post_init__(self) -> None:
        _require_trace_name(self.operation_name, "readiness operation_name")
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("readiness operation_kind must be OperationKind")
        _require_trace_name(self.planned_backend, "readiness planned_backend")
        if self.backend_contract != TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT:
            raise ValueError("readiness backend_contract is not trusted for v0")
        _require_operation_set(self.supported_ops, "readiness supported_ops")
        if self.status != "ready":
            raise ValueError("runtime execution readiness status must be ready")
        _require_trace_name(self.reason, "readiness reason")


@dataclass(frozen=True)
class RuntimeExecutionReadinessReport:
    """Deterministic pre-execution contract report for one planned graph."""

    graph_name: str
    executor_contract: str
    backend_contract: str
    steps: tuple[RuntimeExecutionReadinessStep, ...]
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    status: str = "ready"

    def __post_init__(self) -> None:
        _require_trace_name(self.graph_name, "readiness graph_name")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("readiness executor_contract is not trusted for v0")
        if self.backend_contract != TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT:
            raise ValueError("readiness backend_contract is not trusted for v0")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("readiness trusted registry is not trusted for v0")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("readiness blocked execution surfaces changed")
        if self.status != "ready":
            raise ValueError("runtime execution readiness report status must be ready")
        if type(self.steps) is not tuple:
            raise TypeError("runtime execution readiness steps must be a tuple")
        if not self.steps:
            raise ValueError("runtime execution readiness report must contain steps")
        if len(self.steps) > MAX_RUNTIME_EXECUTION_VALUES:
            raise ValueError("runtime execution readiness step count exceeds limit")
        for step in self.steps:
            if not isinstance(step, RuntimeExecutionReadinessStep):
                raise TypeError(
                    "runtime execution readiness steps must be "
                    "RuntimeExecutionReadinessStep"
                )

    def dump(self) -> str:
        """Render a stable execution-readiness report."""

        lines = [f"runtime.execution_readiness @{self.graph_name} {{"]
        lines.append(f'  executor_contract = "{self.executor_contract}"')
        lines.append(f'  backend_contract = "{self.backend_contract}"')
        lines.append(
            f'  trusted_executor_registry = "{self.trusted_executor_registry}"'
        )
        lines.append(
            "  blocked_execution_surfaces = "
            f'"{",".join(self.blocked_execution_surfaces)}"'
        )
        lines.append(f'  status = "{self.status}"')
        lines.append("  steps {")
        for step in self.steps:
            lines.append(f"    {_format_readiness_step(step)}")
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)


@dataclass(frozen=True)
class RuntimeValueRecord:
    """Internal immutable tensor value record for Runtime Executor v0."""

    tensor_name: str
    value: FloatArray
    shape: tuple[int, ...]
    dtype: str
    value_role: str
    record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT

    def __post_init__(self) -> None:
        _require_trace_name(self.tensor_name, "runtime value record tensor_name")
        if self.record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime value record contract mismatch")
        _require_shape(self.shape)
        if self.value_role not in _RUNTIME_VALUE_ROLES:
            raise ValueError("runtime value record role is unsupported")
        if not isinstance(self.value, np.ndarray):
            raise TypeError("runtime value record value must be NumPy array")
        if self.dtype != str(self.value.dtype):
            raise ValueError("runtime value record dtype must match value dtype")
        _validate_runtime_tensor_value(
            tensor_name=self.tensor_name,
            value=self.value,
            expected_shape=self.shape,
            value_role=self.value_role,
        )
        stored_value = np.array(self.value, copy=True)
        stored_value.setflags(write=False)
        object.__setattr__(self, "value", stored_value)


class RuntimeTensorStore:
    """Internal bounded tensor-value store backed by RuntimeValueRecord objects."""

    store_contract = RUNTIME_TENSOR_STORE_CONTRACT

    def __init__(self, records: tuple[RuntimeValueRecord, ...] = ()) -> None:
        if type(records) is not tuple:
            raise TypeError("runtime tensor store records must be a tuple")
        self._records: dict[str, RuntimeValueRecord] = {}
        for record in records:
            self.add(record)

    @property
    def record_count(self) -> int:
        """Return stored tensor value count."""

        return len(self._records)

    @property
    def records(self) -> tuple[RuntimeValueRecord, ...]:
        """Return stored tensor records in insertion order."""

        return tuple(self._records.values())

    @property
    def values(self) -> Mapping[str, FloatArray]:
        """Return a read-only tensor-name to tensor-value mapping."""

        return MappingProxyType(
            {name: record.value for name, record in self._records.items()}
        )

    def add(self, record: RuntimeValueRecord) -> None:
        """Add one tensor value record fail-closed on duplicate or excessive values."""

        if not isinstance(record, RuntimeValueRecord):
            raise TypeError("runtime tensor store records must be RuntimeValueRecord")
        if record.tensor_name in self._records:
            raise ValueError(f"runtime tensor store duplicate value: {record.tensor_name}")
        if len(self._records) >= MAX_RUNTIME_EXECUTION_VALUES:
            raise ValueError("runtime executor value count exceeds limit")
        self._records[record.tensor_name] = record

    def value_for(self, tensor_name: str) -> FloatArray:
        """Return one tensor value by name."""

        return self.record_for(tensor_name).value

    def record_for(self, tensor_name: str) -> RuntimeValueRecord:
        """Return one tensor value record by name."""

        _require_trace_name(tensor_name, "tensor_name")
        record = self._records.get(tensor_name)
        if record is None:
            raise KeyError(tensor_name)
        return record

    def store_computed(self, tensor: TensorRef, value: FloatArray) -> None:
        """Store one computed tensor output value."""

        self.add(
            RuntimeValueRecord(
                tensor_name=tensor.name,
                value=value,
                shape=tensor.shape,
                dtype=str(value.dtype),
                value_role="computed",
            )
        )


@dataclass(frozen=True)
class RuntimeExecutionResult:
    """Executed graph values plus deterministic trace evidence."""

    values: Mapping[str, FloatArray]
    trace: RuntimeExecutionTrace

    def __post_init__(self) -> None:
        if not isinstance(self.values, Mapping):
            raise TypeError("runtime execution result values must be a mapping")
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def output_for(self, tensor_name: str) -> FloatArray:
        """Return one output value by tensor name."""

        _require_trace_name(tensor_name, "tensor_name")
        value = self.values.get(tensor_name)
        if value is None:
            raise KeyError(tensor_name)
        return value


def execute_graph(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    inputs: Mapping[str, object],
) -> RuntimeExecutionResult:
    """Execute a graph with trusted reference kernels and trace every step."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime executor graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("runtime executor partition_plan must be PartitionPlan")
    _validate_partition_plan(graph, partition_plan)
    runtime_execution_readiness_report(graph, partition_plan)
    tensor_store = _normalize_inputs(graph, inputs)
    assignments = {
        assignment.operation_name: assignment for assignment in partition_plan.assignments
    }
    executors = trusted_runtime_executor_registry()
    steps: list[RuntimeExecutionStep] = []

    for operation in graph.operations:
        assignment = assignments[operation.name]
        executor = _executor_for_assignment(assignment, executors)
        result = executor.execute(operation, tensor_store.values)
        if len(operation.outputs) != 1:
            raise ValueError("runtime executor v0 supports one output per operation")
        output = operation.outputs[0]
        _validate_declared_output(operation, result)
        tensor_store.store_computed(output, result)
        steps.append(_build_step(operation, assignment, executor, result))
        if tensor_store.record_count > MAX_RUNTIME_EXECUTION_VALUES:
            raise ValueError("runtime executor value count exceeds limit")

    return RuntimeExecutionResult(
        values=tensor_store.values,
        trace=RuntimeExecutionTrace(
            graph_name=graph.name,
            executor_contract=RUNTIME_EXECUTOR_CONTRACT,
            steps=tuple(steps),
        ),
    )


def dump_execution_trace(trace: RuntimeExecutionTrace) -> str:
    """Return a stable runtime execution trace dump."""

    if not isinstance(trace, RuntimeExecutionTrace):
        raise TypeError("trace must be RuntimeExecutionTrace")
    return trace.dump()


def runtime_execution_readiness_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> RuntimeExecutionReadinessReport:
    """Validate a planned graph against trusted executor contracts."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime execution readiness graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError(
            "runtime execution readiness partition_plan must be PartitionPlan"
        )
    _validate_partition_plan(graph, partition_plan)
    contracts = _backend_contracts_by_name(trusted_runtime_executor_contracts())
    assignments = {
        assignment.operation_name: assignment for assignment in partition_plan.assignments
    }
    steps = tuple(
        _build_readiness_step(operation, assignments[operation.name], contracts)
        for operation in graph.operations
    )
    return RuntimeExecutionReadinessReport(
        graph_name=graph.name,
        executor_contract=RUNTIME_EXECUTOR_CONTRACT,
        backend_contract=TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT,
        steps=steps,
    )


def dump_runtime_execution_readiness(
    report: RuntimeExecutionReadinessReport,
) -> str:
    """Return a stable runtime execution readiness dump."""

    if not isinstance(report, RuntimeExecutionReadinessReport):
        raise TypeError("report must be RuntimeExecutionReadinessReport")
    return report.dump()


def trusted_runtime_executor_contracts() -> tuple[RuntimeBackendExecutorContract, ...]:
    """Return deterministic pure-data contracts for the fixed trusted registry."""

    registry = trusted_runtime_executor_registry()
    return tuple(registry[name].contract for name in sorted(registry))


def dump_trusted_runtime_executor_contracts(
    contracts: tuple[RuntimeBackendExecutorContract, ...] | None = None,
) -> str:
    """Return a stable dump of trusted prototype runtime backend contracts."""

    selected_contracts = (
        trusted_runtime_executor_contracts() if contracts is None else contracts
    )
    _validate_backend_contracts(selected_contracts)

    lines = [
        f"runtime.backend_executor_contracts @{TRUSTED_RUNTIME_EXECUTOR_REGISTRY} {{"
    ]
    lines.append(f'  executor_contract = "{RUNTIME_EXECUTOR_CONTRACT}"')
    lines.append(
        f'  backend_contract = "{TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append("  backends {")
    for contract in sorted(selected_contracts, key=lambda item: item.backend_name):
        lines.append(f"    {contract.dump_line()}")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def trusted_runtime_executor_registry() -> dict[str, TrustedRuntimeBackendExecutor]:
    """Return the fixed trusted in-repository runtime executor registry."""

    executors = (
        TrustedRuntimeBackendExecutor(
            name="linear-sim",
            supported_ops=frozenset({OperationKind.MATMUL, OperationKind.REDUCTION}),
        ),
        TrustedRuntimeBackendExecutor(
            name="reference-cpu",
            supported_ops=frozenset(OperationKind),
        ),
        TrustedRuntimeBackendExecutor(
            name="systolic-sim",
            supported_ops=frozenset({OperationKind.MATMUL}),
        ),
    )
    return {executor.name: executor for executor in executors}


def _backend_contracts_by_name(
    contracts: tuple[RuntimeBackendExecutorContract, ...],
) -> dict[str, RuntimeBackendExecutorContract]:
    _validate_backend_contracts(contracts)
    return {contract.backend_name: contract for contract in contracts}


def _build_readiness_step(
    operation: ComputeOperation,
    assignment: Assignment,
    contracts: Mapping[str, RuntimeBackendExecutorContract],
) -> RuntimeExecutionReadinessStep:
    _validate_runtime_operation_contract(operation)
    contract = contracts.get(assignment.backend_name)
    if contract is None:
        raise ValueError(
            "runtime execution readiness has no trusted executor contract for "
            f"backend: {assignment.backend_name}"
        )
    if operation.kind not in contract.supported_ops:
        raise ValueError(
            "runtime execution readiness contract does not support operation: "
            f"{operation.name}->{assignment.backend_name}"
        )
    return RuntimeExecutionReadinessStep(
        operation_name=operation.name,
        operation_kind=operation.kind,
        planned_backend=assignment.backend_name,
        backend_contract=contract.backend_contract,
        supported_ops=contract.supported_ops,
    )


def _executor_for_assignment(
    assignment: Assignment,
    executors: Mapping[str, TrustedRuntimeBackendExecutor],
) -> TrustedRuntimeBackendExecutor:
    executor = executors.get(assignment.backend_name)
    if executor is None:
        raise ValueError(
            f"runtime executor has no trusted executor for backend: "
            f"{assignment.backend_name}"
        )
    return executor


def _execute_reference_operation(
    operation: ComputeOperation,
    values: Mapping[str, FloatArray],
) -> FloatArray:
    _validate_runtime_operation_contract(operation)
    if operation.kind is OperationKind.MATMUL:
        _require_arity(operation, inputs=2, outputs=1)
        return reference_matmul(
            values[operation.inputs[0].name],
            values[operation.inputs[1].name],
        )
    if operation.kind is OperationKind.ELEMENTWISE:
        _require_arity(operation, inputs=1, outputs=1)
        kernel = operation.attributes.get("kernel", "identity")
        if not isinstance(kernel, str):
            raise TypeError("runtime executor elementwise kernel must be a string")
        return reference_elementwise(values[operation.inputs[0].name], kernel)
    if operation.kind is OperationKind.REDUCTION:
        _require_arity(operation, inputs=1, outputs=1)
        return reference_reduction_sum(
            values[operation.inputs[0].name],
            axis=_required_axis(operation, "reduction"),
        )
    if operation.kind is OperationKind.SOFTMAX:
        _require_arity(operation, inputs=1, outputs=1)
        return reference_softmax(
            values[operation.inputs[0].name],
            axis=_required_axis(operation, "softmax"),
        )
    raise ValueError(f"runtime executor unsupported operation: {operation.kind.value}")


def _validate_runtime_operation_contract(operation: ComputeOperation) -> None:
    if operation.kind is OperationKind.MATMUL:
        _validate_matmul_operation(operation)
        return
    if operation.kind is OperationKind.ELEMENTWISE:
        _validate_elementwise_operation(operation)
        return
    if operation.kind is OperationKind.REDUCTION:
        _validate_reduction_operation(operation)
        return
    if operation.kind is OperationKind.SOFTMAX:
        _validate_softmax_operation(operation)
        return
    raise ValueError(f"runtime executor unsupported operation: {operation.kind.value}")


def _validate_matmul_operation(operation: ComputeOperation) -> None:
    _require_arity(operation, inputs=2, outputs=1)
    left, right = operation.inputs
    output = operation.outputs[0]
    _require_rank(left, rank=2, operation=operation, role="left input")
    _require_rank(right, rank=2, operation=operation, role="right input")
    _require_rank(output, rank=2, operation=operation, role="output")
    if left.shape[1] != right.shape[0]:
        raise ValueError(
            f"runtime executor matmul input dimensions must agree for {operation.name}"
        )
    expected = (left.shape[0], right.shape[1])
    if output.shape != expected:
        raise ValueError(
            f"runtime executor matmul output shape mismatch for {operation.name}: "
            f"expected {_format_shape(expected)}, got {_format_shape(output.shape)}"
        )


def _validate_elementwise_operation(operation: ComputeOperation) -> None:
    _require_arity(operation, inputs=1, outputs=1)
    input_tensor = operation.inputs[0]
    output = operation.outputs[0]
    kernel = operation.attributes.get("kernel", "identity")
    if not isinstance(kernel, str):
        raise TypeError("runtime executor elementwise kernel must be a string")
    try:
        ElementwiseKernel(kernel)
    except ValueError as exc:
        raise ValueError(
            f"runtime executor unsupported elementwise kernel for {operation.name}: "
            f"{kernel!r}"
        ) from exc
    if output.shape != input_tensor.shape:
        raise ValueError(
            f"runtime executor elementwise output shape mismatch for {operation.name}: "
            f"expected {_format_shape(input_tensor.shape)}, got {_format_shape(output.shape)}"
        )


def _validate_reduction_operation(operation: ComputeOperation) -> None:
    _require_arity(operation, inputs=1, outputs=1)
    input_tensor = operation.inputs[0]
    output = operation.outputs[0]
    axis = _required_axis(operation, "reduction")
    normalized_axis = _normalize_axis(axis, rank=len(input_tensor.shape), label="reduction")
    expected = input_tensor.shape[:normalized_axis] + input_tensor.shape[normalized_axis + 1 :]
    if not expected:
        raise ValueError(
            f"runtime executor reduction output would be scalar for {operation.name}"
        )
    if output.shape != expected:
        raise ValueError(
            f"runtime executor reduction output shape mismatch for {operation.name}: "
            f"expected {_format_shape(expected)}, got {_format_shape(output.shape)}"
        )


def _validate_softmax_operation(operation: ComputeOperation) -> None:
    _require_arity(operation, inputs=1, outputs=1)
    input_tensor = operation.inputs[0]
    output = operation.outputs[0]
    axis = _required_axis(operation, "softmax")
    _normalize_axis(axis, rank=len(input_tensor.shape), label="softmax")
    if output.shape != input_tensor.shape:
        raise ValueError(
            f"runtime executor softmax output shape mismatch for {operation.name}: "
            f"expected {_format_shape(input_tensor.shape)}, got {_format_shape(output.shape)}"
        )


def _normalize_inputs(
    graph: ComputeGraph,
    inputs: Mapping[str, object],
) -> RuntimeTensorStore:
    if type(inputs) is not dict:
        raise TypeError("runtime executor inputs must be a plain mapping")
    external_inputs = _external_input_tensors(graph)
    required_inputs = frozenset(external_inputs)
    supplied_inputs = frozenset(inputs)
    missing = sorted(required_inputs - supplied_inputs)
    if missing:
        raise ValueError(f"runtime executor missing inputs: {','.join(missing)}")
    extra = sorted(supplied_inputs - required_inputs)
    if extra:
        raise ValueError(f"runtime executor unexpected inputs: {','.join(extra)}")
    records: list[RuntimeValueRecord] = []
    for name in sorted(required_inputs):
        _require_trace_name(name, "input name")
        value = inputs[name]
        if not isinstance(value, np.ndarray):
            raise TypeError(f"runtime executor input {name} must be NumPy array")
        _validate_runtime_tensor_value(
            tensor_name=name,
            value=value,
            expected_shape=external_inputs[name].shape,
            value_role="input",
        )
        records.append(
            RuntimeValueRecord(
                tensor_name=name,
                value=cast(FloatArray, value),
                shape=external_inputs[name].shape,
                dtype=str(value.dtype),
                value_role="input",
            )
        )
    return RuntimeTensorStore(tuple(records))


def _external_input_tensors(graph: ComputeGraph) -> dict[str, TensorRef]:
    produced: set[str] = set()
    required: dict[str, TensorRef] = {}
    for operation in graph.operations:
        for tensor in operation.inputs:
            if tensor.name not in produced:
                required.setdefault(tensor.name, tensor)
        for tensor in operation.outputs:
            produced.add(tensor.name)
    return required


def _validate_partition_plan(graph: ComputeGraph, partition_plan: PartitionPlan) -> None:
    if graph.name != partition_plan.graph_name:
        raise ValueError("runtime executor graph and partition plan names must match")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(assignment.operation_name for assignment in partition_plan.assignments)
    if assignment_names != operation_names:
        raise ValueError("runtime executor partition plan must match graph operations")


def _validate_declared_output(operation: ComputeOperation, value: FloatArray) -> None:
    output = operation.outputs[0]
    _validate_runtime_tensor_value(
        tensor_name=output.name,
        value=value,
        expected_shape=output.shape,
        value_role="output",
    )


def _validate_runtime_tensor_value(
    *,
    tensor_name: str,
    value: NDArray[np.generic],
    expected_shape: tuple[int, ...],
    value_role: str,
) -> None:
    _require_trace_name(tensor_name, f"runtime executor {value_role} name")
    if tuple(value.shape) != expected_shape:
        raise ValueError(
            f"runtime executor {value_role} shape mismatch for {tensor_name}: "
            f"expected {_format_shape(expected_shape)}, got {_format_shape(value.shape)}"
        )
    if value.dtype != np.dtype(np.float64):
        raise TypeError(
            f"runtime executor {value_role} {tensor_name} dtype must be float64"
        )
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(
            f"runtime executor {value_role} {tensor_name} must contain only finite values"
        )


def _build_step(
    operation: ComputeOperation,
    assignment: Assignment,
    executor: TrustedRuntimeBackendExecutor,
    value: FloatArray,
) -> RuntimeExecutionStep:
    return RuntimeExecutionStep(
        operation_name=operation.name,
        operation_kind=operation.kind,
        planned_backend=assignment.backend_name,
        executor_backend=executor.name,
        input_tensors=tuple(tensor.name for tensor in operation.inputs),
        output_tensors=tuple(tensor.name for tensor in operation.outputs),
        output_shapes=(tuple(int(dimension) for dimension in value.shape),),
        output_dtypes=(str(value.dtype),),
    )


def _require_arity(
    operation: ComputeOperation,
    *,
    inputs: int,
    outputs: int,
) -> None:
    if len(operation.inputs) != inputs or len(operation.outputs) != outputs:
        raise ValueError(
            f"runtime executor {operation.kind.value} arity must be "
            f"{inputs}->{outputs}"
        )


def _required_axis(operation: ComputeOperation, label: str) -> int:
    axis = operation.attributes.get("axis")
    if axis is None:
        raise ValueError(f"runtime executor {label} axis is required")
    return _coerce_axis(axis, label)


def _coerce_axis(axis: object, label: str) -> int:
    if not isinstance(axis, int) or isinstance(axis, bool):
        raise TypeError(f"runtime executor {label} axis must be an integer")
    return axis


def _normalize_axis(axis: int, *, rank: int, label: str) -> int:
    normalized = axis + rank if axis < 0 else axis
    if normalized < 0 or normalized >= rank:
        raise ValueError(f"runtime executor {label} axis is out of bounds")
    return normalized


def _require_rank(
    tensor: TensorRef,
    *,
    rank: int,
    operation: ComputeOperation,
    role: str,
) -> None:
    if len(tensor.shape) != rank:
        raise ValueError(
            f"runtime executor {operation.kind.value} {role} rank must be "
            f"{rank} for {operation.name}"
        )


def _format_step(step: RuntimeExecutionStep) -> str:
    return (
        f"{step.operation_name}"
        f" planned_backend={step.planned_backend}"
        f" executor_backend={step.executor_backend}"
        f" kind={step.operation_kind.value}"
        f" inputs={_format_names(step.input_tensors)}"
        f" outputs={_format_names(step.output_tensors)}"
        f" output_shapes={_format_shapes(step.output_shapes)}"
        f" output_dtypes={_format_names(step.output_dtypes)}"
        f" status={step.status}"
    )


def _format_backend_contract(contract: RuntimeBackendExecutorContract) -> str:
    return (
        f"{contract.backend_name}"
        f" contract={contract.backend_contract}"
        f" execution_mode={contract.execution_mode}"
        f" supported_ops={_format_operation_kinds(contract.supported_ops)}"
        f" input_contract={contract.input_contract}"
        f" output_contract={contract.output_contract}"
        f" external_artifacts={contract.external_artifacts}"
        f" device_access={contract.device_access}"
        f" status={contract.status}"
    )


def _format_readiness_step(step: RuntimeExecutionReadinessStep) -> str:
    return (
        f"{step.operation_name}"
        f" planned_backend={step.planned_backend}"
        f" backend_contract={step.backend_contract}"
        f" kind={step.operation_kind.value}"
        f" supported_ops={_format_operation_kinds(step.supported_ops)}"
        f" status={step.status}"
        f" reason={step.reason}"
    )


def _format_operation_kinds(kinds: frozenset[OperationKind]) -> str:
    return ",".join(sorted(kind.value for kind in kinds))


def _format_names(names: tuple[str, ...]) -> str:
    return ",".join(names) if names else "-"


def _format_shapes(shapes: tuple[tuple[int, ...], ...]) -> str:
    return ",".join(_format_shape(shape) for shape in shapes)


def _format_shape(shape: tuple[int, ...]) -> str:
    return "x".join(str(dimension) for dimension in shape)


def _require_name_sequence(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    if not value:
        raise ValueError(f"{label} must not be empty")
    for item in value:
        _require_trace_name(item, label)


def _require_operation_set(operations: frozenset[OperationKind], label: str) -> None:
    if not isinstance(operations, frozenset):
        raise TypeError(f"{label} must be a frozenset")
    if not operations:
        raise ValueError(f"{label} must support at least one operation")
    if any(not isinstance(operation, OperationKind) for operation in operations):
        raise TypeError(f"{label} must contain OperationKind values")


def _validate_backend_contracts(
    contracts: tuple[RuntimeBackendExecutorContract, ...],
) -> None:
    if type(contracts) is not tuple:
        raise TypeError("runtime backend contracts must be a tuple")
    if not contracts:
        raise ValueError("runtime backend contracts must not be empty")
    if len(contracts) > MAX_TRUSTED_RUNTIME_BACKEND_CONTRACTS:
        raise ValueError("runtime backend contract count exceeds limit")
    backend_names: list[str] = []
    for contract in contracts:
        if not isinstance(contract, RuntimeBackendExecutorContract):
            raise TypeError("runtime backend contracts must be RuntimeBackendExecutorContract")
        backend_names.append(contract.backend_name)
    if len(set(backend_names)) != len(backend_names):
        raise ValueError("runtime backend contracts must have unique backend names")


def _require_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise ValueError("runtime execution output shape must be a non-empty tuple")
    for dimension in value:
        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
            raise ValueError("runtime execution output shape must be positive integers")


def _require_trace_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TRACE_NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime execution name")


__all__ = [
    "MAX_RUNTIME_EXECUTION_VALUES",
    "MAX_TRUSTED_RUNTIME_BACKEND_CONTRACTS",
    "RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_EXECUTOR_CONTRACT",
    "RUNTIME_TENSOR_STORE_CONTRACT",
    "RUNTIME_VALUE_RECORD_CONTRACT",
    "TRUSTED_RUNTIME_BACKEND_EXECUTION_MODE",
    "TRUSTED_RUNTIME_BACKEND_EXECUTOR_CONTRACT",
    "TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT",
    "TRUSTED_RUNTIME_BACKEND_OUTPUT_CONTRACT",
    "TRUSTED_RUNTIME_EXECUTOR_REGISTRY",
    "TRUSTED_REFERENCE_EXECUTOR_BACKEND",
    "RuntimeBackendExecutorContract",
    "RuntimeExecutionReadinessReport",
    "RuntimeExecutionReadinessStep",
    "RuntimeExecutionResult",
    "RuntimeExecutionStep",
    "RuntimeExecutionTrace",
    "RuntimeTensorStore",
    "RuntimeValueRecord",
    "TrustedRuntimeBackendExecutor",
    "dump_execution_trace",
    "dump_runtime_execution_readiness",
    "dump_trusted_runtime_executor_contracts",
    "execute_graph",
    "runtime_execution_readiness_report",
    "trusted_runtime_executor_contracts",
    "trusted_runtime_executor_registry",
]
