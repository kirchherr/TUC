"""Conformance checks for runtime candidate scoring semantics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.runtime.candidate_scoring_policy import (
    RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS,
    RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import CandidateScore, PartitionPlan, partition_graph
from tuc.runtime.plan import TransferCostProfile

RUNTIME_CANDIDATE_SCORING_CONFORMANCE_SCHEMA_VERSION = (
    "tuc.runtime_candidate_scoring_conformance_report.v0"
)
RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CONTRACT = (
    "runtime_candidate_scoring_conformance.data_only.v0"
)
RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REQUIRED_CASES = (
    "transfer_score_latency_prefers_lower",
    "layout_conversion_bytes_recorded",
    "transfer_bytes_tiebreaker",
    "preferred_memory_domain_match_tiebreaker",
    "backend_name_tiebreaker",
)
RUNTIME_CANDIDATE_SCORING_CONFORMANCE_STATUSES = frozenset({"passed", "failed"})
MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CASES = 32
MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_ISSUES = 64
MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_FIELD_BYTES = 512

_CONFORMANCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_CONFORMANCE_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeCandidateScoringConformanceCase:
    """Observed behavior for one candidate scoring component."""

    case_name: str
    component_name: str
    expected_backend: str
    observed_backend: str
    status: str
    detail: str

    def __post_init__(self) -> None:
        _validate_conformance_text(self.case_name, "case_name")
        _validate_conformance_text(self.component_name, "component_name")
        _validate_conformance_text(self.expected_backend, "expected_backend")
        _validate_conformance_text(self.observed_backend, "observed_backend")
        if self.status not in RUNTIME_CANDIDATE_SCORING_CONFORMANCE_STATUSES:
            raise ValueError(
                "runtime candidate scoring conformance status is unsupported"
            )
        _validate_conformance_text(self.detail, "detail")


@dataclass(frozen=True)
class RuntimeCandidateScoringConformanceIssue:
    """One derived conformance issue."""

    case_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_conformance_text(self.case_name, "issue case_name")
        _validate_conformance_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeCandidateScoringConformanceReport:
    """Deterministic report for runtime candidate scoring conformance."""

    cases: tuple[RuntimeCandidateScoringConformanceCase, ...]
    issues: tuple[RuntimeCandidateScoringConformanceIssue, ...]
    conformance_contract: str = RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CONTRACT
    policy_contract: str = RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.conformance_contract != RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CONTRACT:
            raise ValueError("runtime candidate scoring conformance contract mismatch")
        if self.policy_contract != RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT:
            raise ValueError("runtime candidate scoring policy contract mismatch")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError(
                "runtime candidate scoring conformance blocked surfaces changed"
            )
        if type(self.cases) is not tuple:
            raise TypeError(
                "runtime candidate scoring conformance cases must be a tuple"
            )
        if len(self.cases) > MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CASES:
            raise ValueError(
                "runtime candidate scoring conformance case count exceeds limit"
            )
        case_names: list[str] = []
        for case in self.cases:
            if not isinstance(case, RuntimeCandidateScoringConformanceCase):
                raise TypeError(
                    "runtime candidate scoring conformance cases must be case objects"
                )
            case_names.append(case.case_name)
        if tuple(case_names) != RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REQUIRED_CASES:
            raise ValueError(
                "runtime candidate scoring conformance cases must match required order"
            )
        if type(self.issues) is not tuple:
            raise TypeError(
                "runtime candidate scoring conformance issues must be a tuple"
            )
        if len(self.issues) > MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_ISSUES:
            raise ValueError(
                "runtime candidate scoring conformance issue count exceeds limit"
            )
        for issue in self.issues:
            if not isinstance(issue, RuntimeCandidateScoringConformanceIssue):
                raise TypeError(
                    "runtime candidate scoring conformance issues must be issue objects"
                )
        expected_issues = _derive_conformance_issues(self.cases)
        if self.issues != expected_issues:
            raise ValueError(
                "runtime candidate scoring conformance issues must be derived"
            )

    @property
    def passed(self) -> bool:
        """Return whether all candidate scoring cases passed."""

        return not self.issues

    @property
    def covered_components(self) -> tuple[str, ...]:
        """Return covered active components in policy order."""

        observed = {case.component_name for case in self.cases}
        return tuple(
            component
            for component in RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS
            if component in observed
        )


class RuntimeCandidateScoringConformanceError(AssertionError):
    """Raised when runtime candidate scoring conformance fails."""


def run_runtime_candidate_scoring_conformance() -> (
    RuntimeCandidateScoringConformanceReport
):
    """Run bounded, data-only candidate scoring conformance cases."""

    cases = (
        _transfer_score_latency_case(),
        _layout_conversion_bytes_case(),
        _transfer_bytes_tiebreaker_case(),
        _preferred_memory_domain_match_case(),
        _backend_name_tiebreaker_case(),
    )
    return RuntimeCandidateScoringConformanceReport(
        cases=cases,
        issues=_derive_conformance_issues(cases),
    )


def assert_runtime_candidate_scoring_conformance(
    report: RuntimeCandidateScoringConformanceReport,
) -> RuntimeCandidateScoringConformanceReport:
    """Return the report or raise when candidate scoring conformance fails."""

    if not isinstance(report, RuntimeCandidateScoringConformanceReport):
        raise TypeError(
            "runtime candidate scoring conformance report must be report object"
        )
    if report.issues:
        lines = ["runtime candidate scoring conformance failed:"]
        lines.extend(
            f"- {issue.case_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeCandidateScoringConformanceError("\n".join(lines))
    return report


def runtime_candidate_scoring_conformance_report_to_dict(
    report: RuntimeCandidateScoringConformanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible conformance report."""

    if not isinstance(report, RuntimeCandidateScoringConformanceReport):
        raise TypeError(
            "runtime candidate scoring conformance report must be report object"
        )
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": len(report.cases),
        "cases": [
            {
                "case_name": case.case_name,
                "component_name": case.component_name,
                "detail": case.detail,
                "expected_backend": case.expected_backend,
                "observed_backend": case.observed_backend,
                "status": case.status,
            }
            for case in report.cases
        ],
        "conformance_contract": report.conformance_contract,
        "covered_components": list(report.covered_components),
        "issues": [
            {
                "case_name": issue.case_name,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "policy_active_component_order": list(
            RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS
        ),
        "policy_contract": report.policy_contract,
        "schema_version": RUNTIME_CANDIDATE_SCORING_CONFORMANCE_SCHEMA_VERSION,
    }


def dump_runtime_candidate_scoring_conformance_report(
    report: RuntimeCandidateScoringConformanceReport,
) -> str:
    """Render a stable runtime candidate scoring conformance report."""

    text = json.dumps(
        runtime_candidate_scoring_conformance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REPORT_BYTES
    ):
        raise ValueError(
            "runtime candidate scoring conformance report exceeds byte limit"
        )
    return text + "\n"


def _transfer_score_latency_case() -> RuntimeCandidateScoringConformanceCase:
    produced = TensorRef("produced", (4, 4))
    output = TensorRef("output", (4, 4))
    graph = ComputeGraph(
        name="candidate_scoring_transfer_score",
        operations=(
            ComputeOperation(
                name="source",
                kind=OperationKind.MATMUL,
                inputs=(TensorRef("lhs", (4, 4)), TensorRef("rhs", (4, 4))),
                outputs=(produced,),
            ),
            ComputeOperation(
                name="consume",
                kind=OperationKind.ELEMENTWISE,
                inputs=(produced,),
                outputs=(output,),
            ),
        ),
    )
    plan = partition_graph(
        graph,
        (
            _capability(
                "analog-source",
                OperationKind.MATMUL,
                MemoryDomainKind.ANALOG_WEIGHT_BANK,
            ),
            _capability(
                "analog-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.ANALOG_WEIGHT_BANK,
            ),
            _capability(
                "gpu-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.GPU_HBM,
            ),
        ),
        include_candidate_scores=True,
        transfer_cost_profile=_balanced_transfer_profile(),
    )
    selected = _selected_score(plan, "consume")
    passed = (
        selected.backend_name == "analog-target"
        and selected.transfer_score == 0
        and _score_for(plan, "consume", "gpu-target").transfer_score > 0
    )
    return _case(
        case_name="transfer_score_latency_prefers_lower",
        component_name="transfer_score",
        expected_backend="analog-target",
        observed_backend=selected.backend_name,
        passed=passed,
        detail="lower_latency_score_selected",
    )


def _layout_conversion_bytes_case() -> RuntimeCandidateScoringConformanceCase:
    produced = TensorRef("blocked_tensor", (4, 4))
    output = TensorRef("output", (4, 4))
    graph = ComputeGraph(
        name="candidate_scoring_layout_conversion",
        operations=(
            ComputeOperation(
                name="source",
                kind=OperationKind.MATMUL,
                inputs=(TensorRef("lhs", (4, 4)), TensorRef("rhs", (4, 4))),
                outputs=(produced,),
            ),
            ComputeOperation(
                name="consume",
                kind=OperationKind.ELEMENTWISE,
                inputs=(produced,),
                outputs=(output,),
            ),
        ),
    )
    plan = partition_graph(
        graph,
        (
            BackendCapability(
                name="blocked-source",
                supported_ops=frozenset({OperationKind.MATMUL}),
                memory_domain=MemoryDomainKind.HOST_RAM,
                produced_layouts=frozenset({LayoutKind.BLOCKED}),
            ),
            _capability(
                "a-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.HOST_RAM,
            ),
            _capability(
                "b-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.HOST_RAM,
            ),
        ),
        include_candidate_scores=True,
    )
    selected = _selected_score(plan, "consume")
    passed = (
        selected.backend_name == "a-target"
        and selected.layout_conversion_bytes == 64
        and plan.total_layout_conversion_bytes() == 64
    )
    return _case(
        case_name="layout_conversion_bytes_recorded",
        component_name="layout_conversion_bytes",
        expected_backend="a-target",
        observed_backend=selected.backend_name,
        passed=passed,
        detail="layout_conversion_component_recorded",
    )


def _transfer_bytes_tiebreaker_case() -> RuntimeCandidateScoringConformanceCase:
    big = TensorRef("big", (4, 4))
    small = TensorRef("small", (2, 2))
    output = TensorRef("output", (4, 4))
    graph = ComputeGraph(
        name="candidate_scoring_transfer_bytes",
        operations=(
            ComputeOperation(
                name="big_source",
                kind=OperationKind.MATMUL,
                inputs=(TensorRef("lhs", (4, 4)), TensorRef("rhs", (4, 4))),
                outputs=(big,),
            ),
            ComputeOperation(
                name="small_source",
                kind=OperationKind.REDUCTION,
                inputs=(TensorRef("source", (2, 2)),),
                outputs=(small,),
            ),
            ComputeOperation(
                name="merge",
                kind=OperationKind.ELEMENTWISE,
                inputs=(big, small),
                outputs=(output,),
            ),
        ),
    )
    plan = partition_graph(
        graph,
        (
            _capability(
                "analog-producer",
                OperationKind.MATMUL,
                MemoryDomainKind.ANALOG_WEIGHT_BANK,
            ),
            _capability(
                "gpu-producer",
                OperationKind.REDUCTION,
                MemoryDomainKind.GPU_HBM,
            ),
            _capability(
                "z-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.ANALOG_WEIGHT_BANK,
            ),
            _capability(
                "a-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.GPU_HBM,
            ),
        ),
        include_candidate_scores=True,
        transfer_cost_profile=_balanced_transfer_profile(),
    )
    selected = _selected_score(plan, "merge")
    rejected = _score_for(plan, "merge", "a-target")
    passed = (
        selected.backend_name == "z-target"
        and selected.transfer_score == rejected.transfer_score
        and selected.transfer_bytes < rejected.transfer_bytes
    )
    return _case(
        case_name="transfer_bytes_tiebreaker",
        component_name="transfer_bytes",
        expected_backend="z-target",
        observed_backend=selected.backend_name,
        passed=passed,
        detail="lower_transfer_bytes_selected_after_score_tie",
    )


def _preferred_memory_domain_match_case() -> RuntimeCandidateScoringConformanceCase:
    graph = ComputeGraph(
        name="candidate_scoring_preferred_domain",
        operations=(
            ComputeOperation(
                name="prefer_gpu",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("input", (4, 4)),),
                outputs=(TensorRef("output", (4, 4)),),
                attributes={
                    "tuc.preferred_memory_domain": MemoryDomainKind.GPU_HBM.value
                },
            ),
        ),
    )
    plan = partition_graph(
        graph,
        (
            _capability(
                "a-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.ANALOG_WEIGHT_BANK,
            ),
            _capability(
                "z-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.GPU_HBM,
            ),
        ),
        include_candidate_scores=True,
    )
    selected = _selected_score(plan, "prefer_gpu")
    passed = (
        selected.backend_name == "z-target"
        and selected.preferred_memory_domain_match
    )
    return _case(
        case_name="preferred_memory_domain_match_tiebreaker",
        component_name="preferred_memory_domain_match",
        expected_backend="z-target",
        observed_backend=selected.backend_name,
        passed=passed,
        detail="preferred_memory_domain_selected_after_equal_scores",
    )


def _backend_name_tiebreaker_case() -> RuntimeCandidateScoringConformanceCase:
    graph = ComputeGraph(
        name="candidate_scoring_backend_name",
        operations=(
            ComputeOperation(
                name="tie",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("input", (4, 4)),),
                outputs=(TensorRef("output", (4, 4)),),
            ),
        ),
    )
    plan = partition_graph(
        graph,
        (
            _capability(
                "z-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.HOST_RAM,
            ),
            _capability(
                "a-target",
                OperationKind.ELEMENTWISE,
                MemoryDomainKind.HOST_RAM,
            ),
        ),
        include_candidate_scores=True,
    )
    selected = _selected_score(plan, "tie")
    passed = selected.backend_name == "a-target"
    return _case(
        case_name="backend_name_tiebreaker",
        component_name="backend_name_tiebreaker",
        expected_backend="a-target",
        observed_backend=selected.backend_name,
        passed=passed,
        detail="lexical_backend_name_selected_after_equal_scores",
    )


def _capability(
    name: str,
    operation_kind: OperationKind,
    memory_domain: MemoryDomainKind,
) -> BackendCapability:
    return BackendCapability(
        name=name,
        supported_ops=frozenset({operation_kind}),
        memory_domain=memory_domain,
    )


def _balanced_transfer_profile() -> TransferCostProfile:
    return TransferCostProfile.from_manifest(
        {
            "name": "candidate_scoring_conformance_profile",
            "fallback": {
                "bandwidth_gb_s": 16.0,
                "base_latency_ns": 20_000.0,
                "energy_pj_per_byte": 100.0,
            },
            "edges": (
                {
                    "source_domain": "analog_weight_bank",
                    "target_domain": "gpu_hbm",
                    "bandwidth_gb_s": 64.0,
                    "base_latency_ns": 0.0,
                    "energy_pj_per_byte": 1.0,
                },
                {
                    "source_domain": "gpu_hbm",
                    "target_domain": "analog_weight_bank",
                    "bandwidth_gb_s": 16.0,
                    "base_latency_ns": 0.0,
                    "energy_pj_per_byte": 1.0,
                },
            ),
        }
    )


def _selected_score(plan: PartitionPlan, operation_name: str) -> CandidateScore:
    selected = tuple(
        score
        for score in plan.candidate_scores
        if score.operation_name == operation_name and score.selected
    )
    if len(selected) != 1:
        raise ValueError("expected exactly one selected candidate score")
    return selected[0]


def _score_for(
    plan: PartitionPlan,
    operation_name: str,
    backend_name: str,
) -> CandidateScore:
    for score in plan.candidate_scores:
        if (
            score.operation_name == operation_name
            and score.backend_name == backend_name
        ):
            return score
    raise ValueError("candidate score not found")


def _case(
    *,
    case_name: str,
    component_name: str,
    expected_backend: str,
    observed_backend: str,
    passed: bool,
    detail: str,
) -> RuntimeCandidateScoringConformanceCase:
    return RuntimeCandidateScoringConformanceCase(
        case_name=case_name,
        component_name=component_name,
        expected_backend=expected_backend,
        observed_backend=observed_backend,
        status="passed" if passed else "failed",
        detail=detail,
    )


def _derive_conformance_issues(
    cases: tuple[RuntimeCandidateScoringConformanceCase, ...],
) -> tuple[RuntimeCandidateScoringConformanceIssue, ...]:
    issues: list[RuntimeCandidateScoringConformanceIssue] = []
    components = tuple(case.component_name for case in cases)
    if components != RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS:
        issues.append(
            RuntimeCandidateScoringConformanceIssue(
                case_name="policy",
                issue_code="active_component_coverage_mismatch",
            )
        )
    for case in cases:
        if case.status != "passed":
            issues.append(
                RuntimeCandidateScoringConformanceIssue(
                    case_name=case.case_name,
                    issue_code=f"{case.case_name}_not_passed",
                )
            )
    return tuple(issues)


def _validate_conformance_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _CONFORMANCE_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe runtime scoring conformance identifier"
        )
    if (
        len(value.encode("utf-8"))
        > MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds runtime scoring conformance field limit")
    if value in _FORBIDDEN_CONFORMANCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CASES",
    "MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_FIELD_BYTES",
    "MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_ISSUES",
    "MAX_RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REPORT_BYTES",
    "RUNTIME_CANDIDATE_SCORING_CONFORMANCE_CONTRACT",
    "RUNTIME_CANDIDATE_SCORING_CONFORMANCE_REQUIRED_CASES",
    "RUNTIME_CANDIDATE_SCORING_CONFORMANCE_SCHEMA_VERSION",
    "RUNTIME_CANDIDATE_SCORING_CONFORMANCE_STATUSES",
    "RuntimeCandidateScoringConformanceCase",
    "RuntimeCandidateScoringConformanceError",
    "RuntimeCandidateScoringConformanceIssue",
    "RuntimeCandidateScoringConformanceReport",
    "assert_runtime_candidate_scoring_conformance",
    "dump_runtime_candidate_scoring_conformance_report",
    "run_runtime_candidate_scoring_conformance",
    "runtime_candidate_scoring_conformance_report_to_dict",
]
