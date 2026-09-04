"""Metadata-only evidence for materialized heterogeneous runtime storage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.model import ComputeGraph
from tuc.runtime.backend_equivalence import RuntimeBackendEquivalenceReport
from tuc.runtime.heterogeneous_storage_executor import (
    MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES,
    RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE,
    RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT,
    RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS,
    RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY,
    RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM,
    RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM,
    RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY,
    RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY,
    RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY,
    RuntimeHeterogeneousStorageExecutionTrace,
    RuntimeMaterializedHeterogeneousStorageExecution,
    assert_materializable_heterogeneous_storage_execution,
    assert_materialized_heterogeneous_storage_execution,
    runtime_heterogeneous_storage_execution_trace_to_dict,
)
from tuc.runtime.heterogeneous_storage_plan import (
    RuntimeHeterogeneousStoragePlanReport,
    dump_runtime_heterogeneous_storage_plan_report,
)
from tuc.runtime.materialized_layout_conversion import (
    RuntimeMaterializedLayoutConversionReport,
    build_runtime_materialized_layout_conversion_report,
    dump_runtime_materialized_layout_conversion_report,
)
from tuc.runtime.materialized_transfer import (
    RuntimeMaterializedTransferReport,
    build_runtime_materialized_transfer_report,
    dump_runtime_materialized_transfer_report,
)
from tuc.runtime.output_manifest import build_runtime_output_manifest_report
from tuc.runtime.partitioning import PartitionPlan
from tuc.runtime.reference_correctness import RuntimeReferenceCorrectnessReport
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_materialized_heterogeneous_storage_report.v0"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT = (
    "runtime_heterogeneous_storage.materialized_trusted_simulator.v0"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_SCOPE = (
    "preallocated_produced_layout_and_transfer_staging_slots"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_POLICY = (
    "canonical_plan_preallocate_write_release_reuse"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_KERNEL_TEMPORARY_POLICY = (
    "excluded_from_storage_plan_memory_claim"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_BUDGET_INTERPRETATION = (
    "planned_float32_bytes_separate_from_float64_simulator_storage"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM = (
    "simulated_domains_not_physical_residency"
)
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_NATIVE_CLAIM = "not_claimed"
RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_STATUS = "passed"
MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_BYTES = 256 * 1024
MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_FIELD_BYTES = 256

_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeMaterializedHeterogeneousStorageReport:
    """Closed proof that one storage plan governed trusted execution."""

    graph_name: str
    source_storage_plan_digest: str
    source_storage_metadata_digest: str
    runtime_execution_trace_digest: str
    storage_execution_trace_digest: str
    output_metadata_digest: str
    reference_correctness_digest: str
    backend_equivalence_metadata_digest: str
    materialized_layout_conversion_metadata_digest: str
    materialized_transfer_metadata_digest: str
    operation_count: int
    retained_tensor_record_count: int
    terminal_output_count: int
    terminal_output_snapshot_bytes: int
    storage_execution: RuntimeHeterogeneousStorageExecutionTrace
    evidence_contract: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT
    artifact_status: str = (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_ARTIFACT_STATUS
    )
    materialization_scope: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_SCOPE
    materialization_policy: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_POLICY
    executor_contract: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT
    execution_mode: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE
    write_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY
    release_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY
    retention_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY
    kernel_temporary_policy: str = (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_KERNEL_TEMPORARY_POLICY
    )
    budget_interpretation: str = (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_BUDGET_INTERPRETATION
    )
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    handle_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY
    external_artifacts: str = RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS
    physical_memory_claim: str = RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM
    residency_claim: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM
    native_allocator_claim: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_NATIVE_CLAIM
    performance_claim: str = RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM
    reference_correctness_passed: bool = True
    backend_equivalence_passed: bool = True
    layout_conversion_passed: bool = True
    transfer_passed: bool = True
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_STATUS

    def __post_init__(self) -> None:
        _require_safe_text(self.graph_name, "graph_name")
        for value in (
            self.source_storage_plan_digest,
            self.source_storage_metadata_digest,
            self.runtime_execution_trace_digest,
            self.storage_execution_trace_digest,
            self.output_metadata_digest,
            self.reference_correctness_digest,
            self.backend_equivalence_metadata_digest,
            self.materialized_layout_conversion_metadata_digest,
            self.materialized_transfer_metadata_digest,
        ):
            _require_digest(value)
        _require_positive_int(self.operation_count, "operation_count")
        _require_positive_int(
            self.retained_tensor_record_count,
            "retained_tensor_record_count",
        )
        _require_positive_int(self.terminal_output_count, "terminal_output_count")
        _require_positive_int(
            self.terminal_output_snapshot_bytes,
            "terminal_output_snapshot_bytes",
        )
        if not isinstance(
            self.storage_execution,
            RuntimeHeterogeneousStorageExecutionTrace,
        ):
            raise TypeError("materialized heterogeneous report trace is invalid")
        if self.storage_execution.graph_name != self.graph_name:
            raise ValueError("materialized heterogeneous report graph linkage mismatch")
        if (
            self.storage_execution.trace_metadata_digest
            != self.storage_execution_trace_digest
        ):
            raise ValueError("materialized heterogeneous trace digest mismatch")
        if self.source_storage_plan_digest != (
            self.storage_execution.source_storage_plan_digest
        ):
            raise ValueError("materialized heterogeneous source plan digest mismatch")
        expected = (
            (
                self.evidence_contract,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT,
            ),
            (
                self.artifact_status,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_ARTIFACT_STATUS,
            ),
            (
                self.materialization_scope,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_SCOPE,
            ),
            (
                self.materialization_policy,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_POLICY,
            ),
            (self.executor_contract, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT),
            (self.execution_mode, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE),
            (self.write_policy, RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY),
            (self.release_policy, RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY),
            (self.retention_policy, RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY),
            (
                self.kernel_temporary_policy,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_KERNEL_TEMPORARY_POLICY,
            ),
            (
                self.budget_interpretation,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_BUDGET_INTERPRETATION,
            ),
            (self.raw_value_policy, RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS),
            (self.handle_policy, RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY),
            (self.external_artifacts, RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS),
            (
                self.physical_memory_claim,
                RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM,
            ),
            (
                self.residency_claim,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM,
            ),
            (
                self.native_allocator_claim,
                RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_NATIVE_CLAIM,
            ),
            (self.performance_claim, RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM),
            (self.status, RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_STATUS),
        )
        if any(observed != required for observed, required in expected):
            raise ValueError("materialized heterogeneous report contract mismatch")
        if not all(
            (
                self.reference_correctness_passed,
                self.backend_equivalence_passed,
                self.layout_conversion_passed,
                self.transfer_passed,
            )
        ):
            raise ValueError("materialized heterogeneous report requires all proofs")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("materialized heterogeneous security boundary changed")
        if self.runtime_reserved_bytes > MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES:
            raise ValueError("materialized heterogeneous runtime byte limit exceeded")
        if self.reuse_event_count <= 0 or self.runtime_reuse_savings_bytes <= 0:
            raise ValueError("materialized heterogeneous report requires executed reuse")

    @property
    def slot_count(self) -> int:
        return len(self.storage_execution.slots)

    @property
    def storage_write_count(self) -> int:
        return len(self.storage_execution.writes)

    @property
    def release_count(self) -> int:
        return len(self.storage_execution.releases)

    @property
    def reused_slot_count(self) -> int:
        return sum(item.storage_count > 1 for item in self.storage_execution.slots)

    @property
    def reuse_event_count(self) -> int:
        return self.storage_execution.reuse_event_count

    @property
    def planned_reserved_bytes(self) -> int:
        return self.storage_execution.planned_reserved_bytes

    @property
    def runtime_reserved_bytes(self) -> int:
        return self.storage_execution.runtime_reserved_bytes

    @property
    def runtime_unreused_storage_bytes(self) -> int:
        return self.storage_execution.runtime_unreused_storage_bytes

    @property
    def runtime_reuse_savings_bytes(self) -> int:
        return self.storage_execution.runtime_reuse_savings_bytes


def build_runtime_materialized_heterogeneous_storage_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    storage_plan: RuntimeHeterogeneousStoragePlanReport,
    materialized: RuntimeMaterializedHeterogeneousStorageExecution,
    correctness: RuntimeReferenceCorrectnessReport,
    equivalence: RuntimeBackendEquivalenceReport,
    layout_conversion: RuntimeMaterializedLayoutConversionReport,
    transfer: RuntimeMaterializedTransferReport,
) -> RuntimeMaterializedHeterogeneousStorageReport:
    """Bind planned storage, materialization, movement, and semantics."""

    if not isinstance(correctness, RuntimeReferenceCorrectnessReport):
        raise TypeError("materialized heterogeneous correctness report is invalid")
    if not isinstance(equivalence, RuntimeBackendEquivalenceReport):
        raise TypeError("materialized heterogeneous equivalence report is invalid")
    if not isinstance(layout_conversion, RuntimeMaterializedLayoutConversionReport):
        raise TypeError("materialized heterogeneous layout report is invalid")
    if not isinstance(transfer, RuntimeMaterializedTransferReport):
        raise TypeError("materialized heterogeneous transfer report is invalid")
    canonical = assert_materializable_heterogeneous_storage_execution(
        graph,
        partition_plan,
        storage_plan,
    )
    assert_materialized_heterogeneous_storage_execution(canonical, materialized)
    execution = materialized.execution
    if {
        execution.trace.graph_name,
        correctness.graph_name,
        equivalence.graph_name,
        layout_conversion.graph_name,
        transfer.graph_name,
    } != {graph.name}:
        raise ValueError("materialized heterogeneous evidence graph linkage mismatch")
    if not correctness.passed:
        raise ValueError("materialized heterogeneous storage requires correctness PASS")
    if not equivalence.passed:
        raise ValueError("materialized heterogeneous storage requires equivalence PASS")
    expected_layout = build_runtime_materialized_layout_conversion_report(
        graph,
        partition_plan,
        execution,
        equivalence,
    )
    if dump_runtime_materialized_layout_conversion_report(layout_conversion) != (
        dump_runtime_materialized_layout_conversion_report(expected_layout)
    ):
        raise ValueError("materialized heterogeneous layout evidence is not canonical")
    expected_transfer = build_runtime_materialized_transfer_report(
        graph,
        partition_plan,
        execution,
        equivalence,
        expected_layout,
    )
    if dump_runtime_materialized_transfer_report(transfer) != (
        dump_runtime_materialized_transfer_report(expected_transfer)
    ):
        raise ValueError("materialized heterogeneous transfer evidence is not canonical")
    output_manifest = build_runtime_output_manifest_report(graph, execution)
    if not output_manifest.passed:
        raise ValueError("materialized heterogeneous output manifest must pass")
    if len(execution.trace.steps) != len(graph.operations):
        raise ValueError("materialized heterogeneous operation trace count mismatch")
    terminal_snapshot_bytes = sum(
        int(execution.output_for(item.tensor_name).nbytes)
        for item in output_manifest.expected_outputs
    )
    storage_plan_dump = dump_runtime_heterogeneous_storage_plan_report(canonical)
    return RuntimeMaterializedHeterogeneousStorageReport(
        graph_name=graph.name,
        source_storage_plan_digest=_digest(storage_plan_dump),
        source_storage_metadata_digest=canonical.storage_metadata_digest,
        runtime_execution_trace_digest=_digest(execution.trace.dump()),
        storage_execution_trace_digest=(
            materialized.storage_trace.trace_metadata_digest
        ),
        output_metadata_digest=output_manifest.output_metadata_digest,
        reference_correctness_digest=correctness.comparison_metadata_digest,
        backend_equivalence_metadata_digest=equivalence.comparison_metadata_digest,
        materialized_layout_conversion_metadata_digest=_digest(
            dump_runtime_materialized_layout_conversion_report(layout_conversion)
        ),
        materialized_transfer_metadata_digest=_digest(
            dump_runtime_materialized_transfer_report(transfer)
        ),
        operation_count=len(graph.operations),
        retained_tensor_record_count=len(execution.records),
        terminal_output_count=len(output_manifest.outputs),
        terminal_output_snapshot_bytes=terminal_snapshot_bytes,
        storage_execution=materialized.storage_trace,
    )


def runtime_materialized_heterogeneous_storage_report_to_dict(
    report: RuntimeMaterializedHeterogeneousStorageReport,
) -> dict[str, object]:
    """Return deterministic review evidence without runtime values or handles."""

    if not isinstance(report, RuntimeMaterializedHeterogeneousStorageReport):
        raise TypeError("materialized heterogeneous report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "backend_equivalence_metadata_digest": (
            report.backend_equivalence_metadata_digest
        ),
        "backend_equivalence_passed": report.backend_equivalence_passed,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "budget_interpretation": report.budget_interpretation,
        "evidence_contract": report.evidence_contract,
        "execution_mode": report.execution_mode,
        "executor_contract": report.executor_contract,
        "external_artifacts": report.external_artifacts,
        "graph_name": report.graph_name,
        "handle_policy": report.handle_policy,
        "kernel_temporary_policy": report.kernel_temporary_policy,
        "layout_conversion_passed": report.layout_conversion_passed,
        "materialization_policy": report.materialization_policy,
        "materialization_scope": report.materialization_scope,
        "materialized_layout_conversion_metadata_digest": (
            report.materialized_layout_conversion_metadata_digest
        ),
        "materialized_transfer_metadata_digest": (
            report.materialized_transfer_metadata_digest
        ),
        "native_allocator_claim": report.native_allocator_claim,
        "operation_count": report.operation_count,
        "output_metadata_digest": report.output_metadata_digest,
        "performance_claim": report.performance_claim,
        "physical_memory_claim": report.physical_memory_claim,
        "planned_reserved_bytes": report.planned_reserved_bytes,
        "raw_value_policy": report.raw_value_policy,
        "reference_correctness_digest": report.reference_correctness_digest,
        "reference_correctness_passed": report.reference_correctness_passed,
        "release_count": report.release_count,
        "release_policy": report.release_policy,
        "residency_claim": report.residency_claim,
        "retained_tensor_record_count": report.retained_tensor_record_count,
        "retention_policy": report.retention_policy,
        "reuse_event_count": report.reuse_event_count,
        "reused_slot_count": report.reused_slot_count,
        "runtime_execution_trace_digest": report.runtime_execution_trace_digest,
        "runtime_reserved_bytes": report.runtime_reserved_bytes,
        "runtime_reuse_savings_bytes": report.runtime_reuse_savings_bytes,
        "runtime_unreused_storage_bytes": report.runtime_unreused_storage_bytes,
        "schema_version": (
            RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_SCHEMA_VERSION
        ),
        "slot_count": report.slot_count,
        "source_storage_metadata_digest": report.source_storage_metadata_digest,
        "source_storage_plan_digest": report.source_storage_plan_digest,
        "status": report.status,
        "storage_execution": runtime_heterogeneous_storage_execution_trace_to_dict(
            report.storage_execution
        ),
        "storage_execution_trace_digest": report.storage_execution_trace_digest,
        "storage_write_count": report.storage_write_count,
        "terminal_output_count": report.terminal_output_count,
        "terminal_output_snapshot_bytes": report.terminal_output_snapshot_bytes,
        "transfer_passed": report.transfer_passed,
        "write_policy": report.write_policy,
    }


def dump_runtime_materialized_heterogeneous_storage_report(
    report: RuntimeMaterializedHeterogeneousStorageReport,
) -> str:
    """Render stable JSON with no values, pointers, addresses, or handles."""

    text = json.dumps(
        runtime_materialized_heterogeneous_storage_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (
        MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_BYTES
    ):
        raise ValueError("materialized heterogeneous report exceeds byte limit")
    return text + "\n"


def _require_safe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe identifier")
    if len(value.encode("utf-8")) > (
        MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds metadata byte limit")


def _require_digest(value: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError("materialized heterogeneous metadata digest is invalid")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _digest(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_FIELD_BYTES",
    "MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_BYTES",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_ARTIFACT_STATUS",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_BUDGET_INTERPRETATION",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_KERNEL_TEMPORARY_POLICY",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_NATIVE_CLAIM",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_POLICY",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_SCHEMA_VERSION",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_SCOPE",
    "RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_STATUS",
    "RuntimeMaterializedHeterogeneousStorageReport",
    "build_runtime_materialized_heterogeneous_storage_report",
    "dump_runtime_materialized_heterogeneous_storage_report",
    "runtime_materialized_heterogeneous_storage_report_to_dict",
]
