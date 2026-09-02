"""Trusted in-process materialization for bounded simulator transfer edges."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import TensorRef
from tuc.runtime.plan import RuntimeTransferEdge

RUNTIME_TRANSFER_EXECUTOR_CONTRACT = "runtime_transfer_executor.trusted_simulator.v0"
RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE = "in_process_owned_numpy_copy"
RUNTIME_TRANSFER_EXECUTOR_NAME = "trusted-device-sram-to-host-ram-copy"
RUNTIME_TRANSFER_EXECUTOR_STATUS = "trusted"
RUNTIME_TRANSFER_EXECUTOR_SEQUENCING = "layout_ready_then_domain_copy"
RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR = (
    MemoryDomainKind.DEVICE_SRAM,
    MemoryDomainKind.HOST_RAM,
)
RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES = (
    "allocation_handles",
    "backend_plugin_discovery",
    "device_access",
    "physical_device_selection",
    "dynamic_import",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "pointer_or_address_exposure",
    "network_access",
    "subprocess_execution",
)
MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS = 2_000_000
MAX_RUNTIME_TRANSFER_EXECUTOR_NAME_BYTES = 256

FloatArray = NDArray[np.float64]
_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class RuntimeTransferExecutorContract:
    """Pure-data contract for the fixed trusted simulator transfer primitive."""

    executor_name: str = RUNTIME_TRANSFER_EXECUTOR_NAME
    source_domain: MemoryDomainKind = (
        RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR[0]
    )
    target_domain: MemoryDomainKind = (
        RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR[1]
    )
    executor_contract: str = RUNTIME_TRANSFER_EXECUTOR_CONTRACT
    execution_mode: str = RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE
    sequencing_policy: str = RUNTIME_TRANSFER_EXECUTOR_SEQUENCING
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    external_artifacts: str = "forbidden"
    physical_residency: str = "not_claimed"
    status: str = RUNTIME_TRANSFER_EXECUTOR_STATUS

    def __post_init__(self) -> None:
        _require_name(self.executor_name, "transfer executor name")
        if (self.source_domain, self.target_domain) != (
            RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR
        ):
            raise ValueError("trusted transfer executor domain pair mismatch")
        if self.executor_contract != RUNTIME_TRANSFER_EXECUTOR_CONTRACT:
            raise ValueError("trusted transfer executor contract mismatch")
        if self.execution_mode != RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE:
            raise ValueError("trusted transfer executor execution mode mismatch")
        if self.sequencing_policy != RUNTIME_TRANSFER_EXECUTOR_SEQUENCING:
            raise ValueError("trusted transfer executor sequencing policy mismatch")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("trusted transfer executor security boundary changed")
        if self.external_artifacts != "forbidden":
            raise ValueError("trusted transfer executor external artifacts must be forbidden")
        if self.physical_residency != "not_claimed":
            raise ValueError("trusted transfer executor cannot claim physical residency")
        if self.status != RUNTIME_TRANSFER_EXECUTOR_STATUS:
            raise ValueError("trusted transfer executor status must be trusted")


@dataclass(frozen=True)
class RuntimeTransferExecutionStep:
    """Observable facts for one materialized simulator-domain copy."""

    tensor_name: str
    source_operation: str
    target_operation: str
    source_backend: str
    target_backend: str
    source_domain: MemoryDomainKind
    target_domain: MemoryDomainKind
    source_layout: LayoutKind
    target_layout: LayoutKind
    copy_input_layout: LayoutKind
    logical_shape: tuple[int, ...]
    planned_bytes: int
    runtime_bytes: int
    element_count: int
    executor_name: str = RUNTIME_TRANSFER_EXECUTOR_NAME
    executor_contract: str = RUNTIME_TRANSFER_EXECUTOR_CONTRACT
    sequencing_policy: str = RUNTIME_TRANSFER_EXECUTOR_SEQUENCING
    ownership_verification: str = "distinct_owned_buffer"
    semantic_verification: str = "exact_logical_values"
    status: str = "executed_and_verified"

    def __post_init__(self) -> None:
        for value, label in (
            (self.tensor_name, "transfer tensor name"),
            (self.source_operation, "transfer source operation"),
            (self.target_operation, "transfer target operation"),
            (self.source_backend, "transfer source backend"),
            (self.target_backend, "transfer target backend"),
            (self.executor_name, "transfer executor name"),
        ):
            _require_name(value, label)
        if (self.source_domain, self.target_domain) != (
            RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR
        ):
            raise ValueError("materialized transfer domain pair unsupported")
        for layout, label in (
            (self.source_layout, "transfer source layout"),
            (self.target_layout, "transfer target layout"),
            (self.copy_input_layout, "transfer copy input layout"),
        ):
            if not isinstance(layout, LayoutKind):
                raise TypeError(f"{label} must be LayoutKind")
        if self.copy_input_layout is not self.target_layout:
            raise ValueError("materialized transfer input must use target layout")
        _require_positive_shape(self.logical_shape)
        _require_positive_int(self.planned_bytes, "transfer planned bytes")
        _require_positive_int(self.runtime_bytes, "transfer runtime bytes")
        _require_positive_int(self.element_count, "transfer element count")
        if self.element_count > MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS:
            raise ValueError("materialized transfer element limit exceeded")
        expected_elements = 1
        for dimension in self.logical_shape:
            expected_elements *= dimension
        if self.element_count != expected_elements:
            raise ValueError("materialized transfer element count mismatch")
        if self.runtime_bytes != self.element_count * 8:
            raise ValueError("materialized transfer runtime byte count mismatch")
        if self.executor_contract != RUNTIME_TRANSFER_EXECUTOR_CONTRACT:
            raise ValueError("materialized transfer executor contract mismatch")
        if self.sequencing_policy != RUNTIME_TRANSFER_EXECUTOR_SEQUENCING:
            raise ValueError("materialized transfer sequencing policy mismatch")
        if self.ownership_verification != "distinct_owned_buffer":
            raise ValueError("materialized transfer ownership verification mismatch")
        if self.semantic_verification != "exact_logical_values":
            raise ValueError("materialized transfer semantic verification mismatch")
        if self.status != "executed_and_verified":
            raise ValueError("materialized transfer status mismatch")

    def dump_line(self) -> str:
        """Render one deterministic materialized-transfer trace line."""

        return (
            f"{self.tensor_name}"
            f" source_operation={self.source_operation}"
            f" target_operation={self.target_operation}"
            f" source_backend={self.source_backend}"
            f" target_backend={self.target_backend}"
            f" source_domain={self.source_domain.value}"
            f" target_domain={self.target_domain.value}"
            f" source_layout={self.source_layout.value}"
            f" target_layout={self.target_layout.value}"
            f" copy_input_layout={self.copy_input_layout.value}"
            f" logical_shape={_format_shape(self.logical_shape)}"
            f" planned_bytes={self.planned_bytes}"
            f" runtime_bytes={self.runtime_bytes}"
            f" elements={self.element_count}"
            f" executor={self.executor_name}"
            f" ownership_verification={self.ownership_verification}"
            f" semantic_verification={self.semantic_verification}"
            f" status={self.status}"
        )


def trusted_runtime_transfer_executor_contract() -> RuntimeTransferExecutorContract:
    """Return the fixed execution-free trusted transfer contract."""

    return RuntimeTransferExecutorContract()


def assert_materializable_runtime_transfer(
    transfer: RuntimeTransferEdge,
    tensor: TensorRef,
) -> RuntimeTransferExecutorContract:
    """Validate one planned transfer before any runtime value is touched."""

    if not isinstance(transfer, RuntimeTransferEdge):
        raise TypeError("materialized transfer must use RuntimeTransferEdge")
    if not isinstance(tensor, TensorRef):
        raise TypeError("materialized transfer tensor must be TensorRef")
    if transfer.tensor_name != tensor.name:
        raise ValueError("materialized transfer tensor mismatch")
    contract = trusted_runtime_transfer_executor_contract()
    if (transfer.source_domain, transfer.target_domain) != (
        contract.source_domain,
        contract.target_domain,
    ):
        raise ValueError("materialized transfer domain pair unsupported")
    element_count = 1
    for dimension in tensor.shape:
        element_count *= dimension
    if element_count > MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS:
        raise ValueError("materialized transfer element limit exceeded")
    expected_planned_bytes = element_count * dtype_size_bytes(tensor.dtype)
    if transfer.bytes_moved != expected_planned_bytes:
        raise ValueError("materialized transfer planned byte count mismatch")
    return contract


def materialize_runtime_transfer(
    transfer: RuntimeTransferEdge,
    tensor: TensorRef,
    value: FloatArray,
    *,
    input_layout: LayoutKind,
) -> tuple[FloatArray, RuntimeTransferExecutionStep]:
    """Copy one logical tensor into a distinct read-only simulator buffer."""

    contract = assert_materializable_runtime_transfer(transfer, tensor)
    if not isinstance(input_layout, LayoutKind):
        raise TypeError("materialized transfer input_layout must be LayoutKind")
    if input_layout is not transfer.target_layout:
        raise ValueError("materialized transfer input layout is not target-ready")
    if not isinstance(value, np.ndarray):
        raise TypeError("materialized transfer value must be NumPy array")
    if tuple(value.shape) != tensor.shape:
        raise ValueError("materialized transfer value shape mismatch")
    if value.dtype != np.dtype(np.float64):
        raise TypeError("materialized transfer value dtype must be float64")
    if not bool(np.all(np.isfinite(value))):
        raise ValueError("materialized transfer value must be finite")

    transferred = np.array(value, dtype=np.float64, copy=True, order="C")
    if bool(np.shares_memory(transferred, value)):
        raise ValueError("materialized transfer must create a distinct buffer")
    if not bool(np.array_equal(transferred, value)):
        raise ValueError("materialized transfer changed logical values")
    transferred.setflags(write=False)

    step = RuntimeTransferExecutionStep(
        tensor_name=tensor.name,
        source_operation=transfer.source_operation,
        target_operation=transfer.target_operation,
        source_backend=transfer.source_backend,
        target_backend=transfer.target_backend,
        source_domain=transfer.source_domain,
        target_domain=transfer.target_domain,
        source_layout=transfer.source_layout,
        target_layout=transfer.target_layout,
        copy_input_layout=input_layout,
        logical_shape=tensor.shape,
        planned_bytes=transfer.bytes_moved,
        runtime_bytes=int(transferred.nbytes),
        element_count=int(transferred.size),
        executor_name=contract.executor_name,
    )
    return transferred, step


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or _NAME_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe runtime name")
    if len(value.encode("utf-8")) > MAX_RUNTIME_TRANSFER_EXECUTOR_NAME_BYTES:
        raise ValueError(f"{label} exceeds runtime name byte limit")


def _require_positive_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise ValueError("materialized transfer shape must be non-empty")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
        ):
            raise ValueError("materialized transfer shape must be positive")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _format_shape(shape: tuple[int, ...]) -> str:
    return "x".join(str(item) for item in shape)


__all__ = [
    "MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS",
    "MAX_RUNTIME_TRANSFER_EXECUTOR_NAME_BYTES",
    "RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_TRANSFER_EXECUTOR_CONTRACT",
    "RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE",
    "RUNTIME_TRANSFER_EXECUTOR_NAME",
    "RUNTIME_TRANSFER_EXECUTOR_SEQUENCING",
    "RUNTIME_TRANSFER_EXECUTOR_STATUS",
    "RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR",
    "RuntimeTransferExecutionStep",
    "RuntimeTransferExecutorContract",
    "assert_materializable_runtime_transfer",
    "materialize_runtime_transfer",
    "trusted_runtime_transfer_executor_contract",
]
