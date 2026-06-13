"""Data-only policy for accepted backend-equivalence portfolio membership."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.backend_equivalence_portfolio import (
    RuntimeBackendEquivalencePortfolioReport,
    RuntimeBackendEquivalencePortfolioSlice,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_backend_equivalence_portfolio_policy_report.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT = (
    "runtime_backend_equivalence_portfolio_policy.data_only.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS = "review_evidence"
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS = "accepted"
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID = (
    "runtime_backend_equivalence_portfolio_policy"
)
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REQUIREMENTS = 16
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_FIELD_BYTES = 512

_POLICY_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_POLICY_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "command_line",
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
        "output_value",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "runtime_handle",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeBackendEquivalencePortfolioRequirement:
    """One required backend-equivalence slice in the accepted portfolio."""

    slice_id: str
    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    baseline_backend_sequence: tuple[str, ...]
    candidate_backend_sequence: tuple[str, ...]
    min_comparison_count: int = 1

    def __post_init__(self) -> None:
        _validate_policy_text(self.slice_id, "slice_id")
        _validate_policy_text(self.graph_name, "graph_name")
        _validate_policy_text(self.baseline_run_id, "baseline_run_id")
        _validate_policy_text(self.candidate_run_id, "candidate_run_id")
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError(
                "runtime backend equivalence portfolio policy run IDs must differ"
            )
        _validate_text_sequence(
            self.baseline_backend_sequence,
            "baseline_backend_sequence",
        )
        _validate_text_sequence(
            self.candidate_backend_sequence,
            "candidate_backend_sequence",
        )
        _validate_positive_count(self.min_comparison_count, "min_comparison_count")


@dataclass(frozen=True)
class RuntimeBackendEquivalencePortfolioPolicyReport:
    """Accepted membership policy for backend-equivalence portfolio evidence."""

    portfolio_id: str
    requirements: tuple[RuntimeBackendEquivalencePortfolioRequirement, ...]
    required_candidate_backend_families: tuple[str, ...]
    policy_id: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID
    policy_contract: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT
    policy_status: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS
    artifact_status: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_policy_text(self.portfolio_id, "portfolio_id")
        _validate_policy_text(self.policy_id, "policy_id")
        if self.policy_contract != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT:
            raise ValueError(
                "runtime backend equivalence portfolio policy contract mismatch"
            )
        if self.policy_status != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS:
            raise ValueError(
                "runtime backend equivalence portfolio policy status mismatch"
            )
        if (
            self.artifact_status
            != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS
        ):
            raise ValueError(
                "runtime backend equivalence portfolio policy artifact status mismatch"
            )
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError(
                "runtime backend equivalence portfolio policy must omit raw values"
            )
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError(
                "runtime backend equivalence portfolio policy trusted registry mismatch"
            )
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime backend equivalence portfolio policy blocked surfaces changed"
            )
        _validate_requirements(self.requirements)
        _validate_text_sequence(
            self.required_candidate_backend_families,
            "required_candidate_backend_families",
        )
        expected_families = _candidate_backend_families(self.requirements)
        if self.required_candidate_backend_families != expected_families:
            raise ValueError(
                "runtime backend equivalence portfolio policy families must be derived"
            )

    @property
    def requirement_count(self) -> int:
        """Return the number of required portfolio slices."""

        return len(self.requirements)

    @property
    def policy_metadata_digest(self) -> str:
        """Return a digest over policy metadata only."""

        payload = [
            {
                "baseline_backend_sequence": list(
                    requirement.baseline_backend_sequence
                ),
                "baseline_run_id": requirement.baseline_run_id,
                "candidate_backend_sequence": list(
                    requirement.candidate_backend_sequence
                ),
                "candidate_run_id": requirement.candidate_run_id,
                "graph_name": requirement.graph_name,
                "min_comparison_count": requirement.min_comparison_count,
                "slice_id": requirement.slice_id,
            }
            for requirement in self.requirements
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeBackendEquivalencePortfolioPolicyError(AssertionError):
    """Raised when backend-equivalence portfolio policy checks fail."""


def build_runtime_backend_equivalence_portfolio_policy_report(
    portfolio_id: str,
    requirements: Iterable[RuntimeBackendEquivalencePortfolioRequirement],
) -> RuntimeBackendEquivalencePortfolioPolicyReport:
    """Build an accepted data-only portfolio membership policy."""

    requirement_tuple = tuple(requirements)
    return RuntimeBackendEquivalencePortfolioPolicyReport(
        portfolio_id=portfolio_id,
        requirements=requirement_tuple,
        required_candidate_backend_families=_candidate_backend_families(
            requirement_tuple
        ),
    )


def build_default_runtime_backend_equivalence_portfolio_policy_report() -> (
    RuntimeBackendEquivalencePortfolioPolicyReport
):
    """Build the current accepted backend-diversity portfolio policy."""

    return build_runtime_backend_equivalence_portfolio_policy_report(
        "runtime_backend_equivalence_portfolio",
        (
            RuntimeBackendEquivalencePortfolioRequirement(
                slice_id="runtime_backend_equivalence",
                graph_name="runtime_backend_equivalence",
                baseline_run_id="reference_cpu",
                candidate_run_id="systolic_sim",
                baseline_backend_sequence=("reference-cpu", "reference-cpu"),
                candidate_backend_sequence=("systolic-sim", "reference-cpu"),
            ),
            RuntimeBackendEquivalencePortfolioRequirement(
                slice_id="runtime_vector_backend_equivalence",
                graph_name="runtime_vector_backend_equivalence",
                baseline_run_id="reference_cpu",
                candidate_run_id="vector_sim",
                baseline_backend_sequence=(
                    "reference-cpu",
                    "reference-cpu",
                    "reference-cpu",
                ),
                candidate_backend_sequence=(
                    "vector-sim",
                    "vector-sim",
                    "vector-sim",
                ),
            ),
            RuntimeBackendEquivalencePortfolioRequirement(
                slice_id="runtime_mixed_backend_equivalence",
                graph_name="runtime_mixed_backend_equivalence",
                baseline_run_id="reference_cpu",
                candidate_run_id="mixed_accelerators",
                baseline_backend_sequence=(
                    "reference-cpu",
                    "reference-cpu",
                    "reference-cpu",
                    "reference-cpu",
                ),
                candidate_backend_sequence=(
                    "systolic-sim",
                    "vector-sim",
                    "vector-sim",
                    "vector-sim",
                ),
            ),
        ),
    )


def assert_runtime_backend_equivalence_portfolio_matches_policy(
    policy: RuntimeBackendEquivalencePortfolioPolicyReport,
    portfolio: RuntimeBackendEquivalencePortfolioReport,
) -> RuntimeBackendEquivalencePortfolioReport:
    """Return the portfolio or raise when it does not match policy."""

    if not isinstance(policy, RuntimeBackendEquivalencePortfolioPolicyReport):
        raise TypeError(
            "runtime backend equivalence portfolio policy must be policy report"
        )
    if not isinstance(portfolio, RuntimeBackendEquivalencePortfolioReport):
        raise TypeError("runtime backend equivalence portfolio must be report")
    if portfolio.portfolio_id != policy.portfolio_id:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            "portfolio_id_mismatch"
        )
    if portfolio.raw_value_policy != policy.raw_value_policy:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            "raw_value_policy_mismatch"
        )
    if portfolio.candidate_backend_families != (
        policy.required_candidate_backend_families
    ):
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            "candidate_backend_families_mismatch"
        )
    if portfolio.slice_count != policy.requirement_count:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            "slice_count_mismatch"
        )
    requirement_by_slice_id = {
        requirement.slice_id: requirement for requirement in policy.requirements
    }
    for slice_ in portfolio.slices:
        requirement = requirement_by_slice_id.get(slice_.slice_id)
        if requirement is None:
            raise RuntimeBackendEquivalencePortfolioPolicyError(
                f"{slice_.slice_id}:unexpected_slice"
            )
        _assert_slice_matches_requirement(slice_, requirement)
    required_slice_ids = tuple(
        requirement.slice_id for requirement in policy.requirements
    )
    actual_slice_ids = tuple(slice_.slice_id for slice_ in portfolio.slices)
    if actual_slice_ids != required_slice_ids:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            "slice_order_mismatch"
        )
    return portfolio


def runtime_backend_equivalence_portfolio_policy_report_to_dict(
    report: RuntimeBackendEquivalencePortfolioPolicyReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible portfolio policy report."""

    if not isinstance(report, RuntimeBackendEquivalencePortfolioPolicyReport):
        raise TypeError(
            "runtime backend equivalence portfolio policy must be policy report"
        )
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "policy_contract": report.policy_contract,
        "policy_id": report.policy_id,
        "policy_metadata_digest": report.policy_metadata_digest,
        "policy_status": report.policy_status,
        "portfolio_id": report.portfolio_id,
        "raw_value_policy": report.raw_value_policy,
        "required_candidate_backend_families": list(
            report.required_candidate_backend_families
        ),
        "requirement_count": report.requirement_count,
        "requirements": [
            {
                "baseline_backend_sequence": list(
                    requirement.baseline_backend_sequence
                ),
                "baseline_run_id": requirement.baseline_run_id,
                "candidate_backend_sequence": list(
                    requirement.candidate_backend_sequence
                ),
                "candidate_run_id": requirement.candidate_run_id,
                "graph_name": requirement.graph_name,
                "min_comparison_count": requirement.min_comparison_count,
                "slice_id": requirement.slice_id,
            }
            for requirement in report.requirements
        ],
        "schema_version": (
            RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION
        ),
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_backend_equivalence_portfolio_policy_report(
    report: RuntimeBackendEquivalencePortfolioPolicyReport,
) -> str:
    """Render stable data-only backend-equivalence portfolio policy evidence."""

    text = json.dumps(
        runtime_backend_equivalence_portfolio_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_BYTES
    ):
        raise ValueError(
            "runtime backend equivalence portfolio policy report exceeds limit"
        )
    return text + "\n"


def _assert_slice_matches_requirement(
    slice_: RuntimeBackendEquivalencePortfolioSlice,
    requirement: RuntimeBackendEquivalencePortfolioRequirement,
) -> None:
    fields = {
        "graph_name": slice_.graph_name,
        "baseline_run_id": slice_.baseline_run_id,
        "candidate_run_id": slice_.candidate_run_id,
        "baseline_backend_sequence": slice_.baseline_backend_sequence,
        "candidate_backend_sequence": slice_.candidate_backend_sequence,
        "raw_value_policy": slice_.raw_value_policy,
    }
    expected = {
        "graph_name": requirement.graph_name,
        "baseline_run_id": requirement.baseline_run_id,
        "candidate_run_id": requirement.candidate_run_id,
        "baseline_backend_sequence": requirement.baseline_backend_sequence,
        "candidate_backend_sequence": requirement.candidate_backend_sequence,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    }
    for field_name, expected_value in expected.items():
        if fields[field_name] != expected_value:
            raise RuntimeBackendEquivalencePortfolioPolicyError(
                f"{requirement.slice_id}:{field_name}_mismatch"
            )
    if slice_.comparison_count < requirement.min_comparison_count:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            f"{requirement.slice_id}:comparison_count_below_minimum"
        )
    if not slice_.passed:
        raise RuntimeBackendEquivalencePortfolioPolicyError(
            f"{requirement.slice_id}:slice_not_passed"
        )


def _candidate_backend_families(
    requirements: tuple[RuntimeBackendEquivalencePortfolioRequirement, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                backend
                for requirement in requirements
                for backend in requirement.candidate_backend_sequence
                if backend != "reference-cpu"
            }
        )
    )


def _validate_requirements(
    requirements: tuple[RuntimeBackendEquivalencePortfolioRequirement, ...],
) -> None:
    if type(requirements) is not tuple or not requirements:
        raise ValueError(
            "runtime backend equivalence portfolio policy requirements must be non-empty tuple"
        )
    if len(requirements) > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REQUIREMENTS:
        raise ValueError(
            "runtime backend equivalence portfolio policy requirement count exceeds limit"
        )
    seen: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, RuntimeBackendEquivalencePortfolioRequirement):
            raise TypeError(
                "runtime backend equivalence portfolio policy requirements must be requirements"
            )
        if requirement.slice_id in seen:
            raise ValueError(
                "runtime backend equivalence portfolio policy slice IDs must be unique"
            )
        seen.add(requirement.slice_id)


def _validate_text_sequence(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(
            f"runtime backend equivalence portfolio policy {label} must be non-empty tuple"
        )
    for item in value:
        _validate_policy_text(item, label)


def _validate_positive_count(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(
            f"runtime backend equivalence portfolio policy {label} must be positive"
        )


def _validate_policy_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _POLICY_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe runtime backend equivalence portfolio policy identifier"
        )
    if (
        len(value.encode("utf-8"))
        > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_FIELD_BYTES
    ):
        raise ValueError(
            f"{label} exceeds runtime backend equivalence portfolio policy field limit"
        )
    if value in _FORBIDDEN_POLICY_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_FIELD_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REQUIREMENTS",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS",
    "RuntimeBackendEquivalencePortfolioPolicyError",
    "RuntimeBackendEquivalencePortfolioPolicyReport",
    "RuntimeBackendEquivalencePortfolioRequirement",
    "assert_runtime_backend_equivalence_portfolio_matches_policy",
    "build_default_runtime_backend_equivalence_portfolio_policy_report",
    "build_runtime_backend_equivalence_portfolio_policy_report",
    "dump_runtime_backend_equivalence_portfolio_policy_report",
    "runtime_backend_equivalence_portfolio_policy_report_to_dict",
]
