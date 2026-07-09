"""Project-level research-scope claim gate for TUC.

This module binds the current high-level proof artifacts while explicitly
blocking production compiler, native performance, and vendor replacement
claims.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.research_scope_claim_gate_report.v0"
)
RESEARCH_SCOPE_CLAIM_GATE_CONTRACT = "research_scope.claim_gate.data_only.v0"
RESEARCH_SCOPE_CLAIM_GATE_ID = "research_scope_claim_gate"
RESEARCH_SCOPE_CLAIM_GATE_STATUS = "PASS"
RESEARCH_SCOPE_CLAIM_ID = "the_universal_compute_research_scope"
RESEARCH_SCOPE_CLAIM_STATEMENT = "hardware_independent_compute_intent_research_proof"
RESEARCH_SCOPE_CLAIM_STATUS = "supported_for_current_research_scope"
RESEARCH_SCOPE_BOUNDARY = "research_proof_not_compiler_replacement"
RESEARCH_SCOPE_ADOPTION_STATUS = "pre_alpha_research"
RESEARCH_SCOPE_TIME_HORIZON_CLAIM = "no_timeline_claim"
RESEARCH_SCOPE_ARTIFACT_POLICY = "digest_only_source_free"
RESEARCH_SCOPE_EVIDENCE_POLICY = "top_level_gate_digest_only_source_free"

RESEARCH_SCOPE_SUPPORTED_CLAIMS = (
    "hardware_independent_compute_intent_current_research_scope",
    "capability_driven_runtime_planning_current_slice",
    "trusted_prototype_backend_execution_current_slice",
    "backend_equivalence_metadata_checked",
    "source_intent_to_runtime_research_path_bounded",
    "secure_by_design_admission_boundaries",
)
RESEARCH_SCOPE_BLOCKED_CLAIMS = (
    "cuda_replacement",
    "rocm_replacement",
    "xla_replacement",
    "tvm_replacement",
    "iree_replacement",
    "production_compiler",
    "arbitrary_triton_source_ingestion",
    "arbitrary_pytorch_model_support",
    "native_performance_parity",
    "real_hardware_backend_execution",
    "external_plugin_execution",
    "generated_artifact_execution",
)
RESEARCH_SCOPE_REQUIRED_INVARIANTS = (
    "objective_alpha_research_claim_gate_passed",
    "source_to_intent_research_capability_claim_gate_passed",
    "performance_interpretation_blocks_native_claims",
    "source_ingestion_maintainer_approval_artifact_absent",
    "source_ingestion_admission_gate_blocks_direct_source_ingestion",
    "top_level_evidence_digest_bound",
    "metadata_only_source_free_artifacts",
    "production_compiler_claim_false",
    "vendor_replacement_claims_false",
    "native_performance_claim_false",
)

MAX_RESEARCH_SCOPE_EVIDENCE = 8
MAX_RESEARCH_SCOPE_FIELD_BYTES = 256
MAX_RESEARCH_SCOPE_REPORT_BYTES = 64 * 1024

_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "backend_artifact",
    "command_line",
    "device_id",
    "dynamic_library_path",
    "file_path",
    "generated_code",
    "host_path",
    "import os",
    "native_source",
    "plugin_entrypoint",
    "python_source",
    "raw_benchmark_output",
    "raw_source",
    "raw_source_text",
    "raw_tensor_value",
    "raw_timing_samples",
    "runtime_handle",
    "source_intent_payload",
    "source_text",
    "tl.dot",
    "tl.store",
)


class ResearchScopeClaimGateError(AssertionError):
    """Raised when the research-scope claim gate contract drifts."""


@dataclass(frozen=True)
class ResearchScopeEvidenceRequirement:
    """One required top-level evidence artifact for the scope gate."""

    evidence_id: str
    contract: str
    status: str


RESEARCH_SCOPE_REQUIRED_EVIDENCE = (
    ResearchScopeEvidenceRequirement(
        evidence_id="objective_alpha_research_claim_gate",
        contract="objective_alpha.research_claim_gate.ci.v0",
        status="PASS",
    ),
    ResearchScopeEvidenceRequirement(
        evidence_id="source_to_intent_research_capability_claim_gate",
        contract="source_to_intent_research_capability_claim_gate.ci.v0",
        status="PASS",
    ),
    ResearchScopeEvidenceRequirement(
        evidence_id="performance_proof_interpretation",
        contract="performance_proof_boundary.blocking.v0",
        status="blocked",
    ),
    ResearchScopeEvidenceRequirement(
        evidence_id="source_ingestion_maintainer_approval_artifact",
        contract="source_ingestion_maintainer_approval_artifact.absent.v0",
        status="external_approval_not_supplied",
    ),
    ResearchScopeEvidenceRequirement(
        evidence_id="source_ingestion_admission_gate",
        contract="source_ingestion_admission_gate.fail_closed.v0",
        status="blocked_missing_maintainer_security_review_approval",
    ),
)


@dataclass(frozen=True)
class ResearchScopeEvidenceBinding:
    """Digest binding for one required top-level evidence artifact."""

    evidence_id: str
    contract: str
    status: str
    digest: str
    source_free: bool = True
    supports_scope: bool = True

    def __post_init__(self) -> None:
        _validate_token(self.evidence_id, "research scope binding evidence_id")
        _validate_token(self.contract, "research scope binding contract")
        _validate_token(self.status, "research scope binding status")
        if not _SHA256_RE.fullmatch(self.digest):
            raise ResearchScopeClaimGateError("research scope evidence digest invalid")
        if self.source_free is not True:
            raise ResearchScopeClaimGateError("research scope evidence must be source-free")
        if self.supports_scope is not True:
            raise ResearchScopeClaimGateError("research scope evidence must support scope")


@dataclass(frozen=True)
class ResearchScopeClaimGateReport:
    """Data-only gate binding TUC's current research-scope claim."""

    evidence: tuple[ResearchScopeEvidenceBinding, ...]
    schema_version: str = RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION
    gate_contract: str = RESEARCH_SCOPE_CLAIM_GATE_CONTRACT
    gate_id: str = RESEARCH_SCOPE_CLAIM_GATE_ID
    gate_status: str = RESEARCH_SCOPE_CLAIM_GATE_STATUS
    claim_id: str = RESEARCH_SCOPE_CLAIM_ID
    claim_statement: str = RESEARCH_SCOPE_CLAIM_STATEMENT
    claim_status: str = RESEARCH_SCOPE_CLAIM_STATUS
    scope_boundary: str = RESEARCH_SCOPE_BOUNDARY
    adoption_status: str = RESEARCH_SCOPE_ADOPTION_STATUS
    time_horizon_claim: str = RESEARCH_SCOPE_TIME_HORIZON_CLAIM
    artifact_policy: str = RESEARCH_SCOPE_ARTIFACT_POLICY
    evidence_policy: str = RESEARCH_SCOPE_EVIDENCE_POLICY
    supported_claims: tuple[str, ...] = RESEARCH_SCOPE_SUPPORTED_CLAIMS
    blocked_claims: tuple[str, ...] = RESEARCH_SCOPE_BLOCKED_CLAIMS
    required_invariants: tuple[str, ...] = RESEARCH_SCOPE_REQUIRED_INVARIANTS
    research_scope_claim: bool = True
    production_compiler_claim: bool = False
    cuda_replacement_claim: bool = False
    rocm_replacement_claim: bool = False
    xla_replacement_claim: bool = False
    tvm_replacement_claim: bool = False
    iree_replacement_claim: bool = False
    native_performance_claim: bool = False
    real_hardware_backend_execution_claim: bool = False
    arbitrary_source_ingestion_claim: bool = False
    arbitrary_third_party_backend_execution_claim: bool = False
    generated_artifact_execution_claim: bool = False
    external_plugin_execution_claim: bool = False
    source_ingestion_admitted: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION:
            raise ResearchScopeClaimGateError("research scope schema version mismatch")
        if self.gate_contract != RESEARCH_SCOPE_CLAIM_GATE_CONTRACT:
            raise ResearchScopeClaimGateError("research scope gate contract mismatch")
        if self.gate_id != RESEARCH_SCOPE_CLAIM_GATE_ID:
            raise ResearchScopeClaimGateError("research scope gate id mismatch")
        if self.gate_status != RESEARCH_SCOPE_CLAIM_GATE_STATUS:
            raise ResearchScopeClaimGateError("research scope gate status mismatch")
        if self.claim_id != RESEARCH_SCOPE_CLAIM_ID:
            raise ResearchScopeClaimGateError("research scope claim id mismatch")
        if self.claim_statement != RESEARCH_SCOPE_CLAIM_STATEMENT:
            raise ResearchScopeClaimGateError("research scope claim statement mismatch")
        if self.claim_status != RESEARCH_SCOPE_CLAIM_STATUS:
            raise ResearchScopeClaimGateError("research scope claim status mismatch")
        if self.scope_boundary != RESEARCH_SCOPE_BOUNDARY:
            raise ResearchScopeClaimGateError("research scope boundary mismatch")
        if self.adoption_status != RESEARCH_SCOPE_ADOPTION_STATUS:
            raise ResearchScopeClaimGateError("research scope adoption status mismatch")
        if self.time_horizon_claim != RESEARCH_SCOPE_TIME_HORIZON_CLAIM:
            raise ResearchScopeClaimGateError("research scope time horizon mismatch")
        if self.artifact_policy != RESEARCH_SCOPE_ARTIFACT_POLICY:
            raise ResearchScopeClaimGateError("research scope artifact policy mismatch")
        if self.evidence_policy != RESEARCH_SCOPE_EVIDENCE_POLICY:
            raise ResearchScopeClaimGateError("research scope evidence policy mismatch")
        if self.supported_claims != RESEARCH_SCOPE_SUPPORTED_CLAIMS:
            raise ResearchScopeClaimGateError("research scope supported claims changed")
        if self.blocked_claims != RESEARCH_SCOPE_BLOCKED_CLAIMS:
            raise ResearchScopeClaimGateError("research scope blocked claims changed")
        if self.required_invariants != RESEARCH_SCOPE_REQUIRED_INVARIANTS:
            raise ResearchScopeClaimGateError("research scope required invariants changed")
        if self.research_scope_claim is not True:
            raise ResearchScopeClaimGateError("research scope claim must be true")
        _assert_blocked_claim_flags(self)
        _validate_evidence_bindings(self.evidence)


def build_research_scope_claim_gate_report(
    evidence: Iterable[ResearchScopeEvidenceBinding],
) -> ResearchScopeClaimGateReport:
    """Build a project-level research-scope claim gate from top-level evidence."""

    return ResearchScopeClaimGateReport(evidence=tuple(evidence))


def research_scope_claim_gate_report_to_dict(
    report: ResearchScopeClaimGateReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible research-scope gate report."""

    assert_research_scope_claim_gate_report(report)
    payload: dict[str, object] = {
        "adoption_status": report.adoption_status,
        "arbitrary_source_ingestion_claim": report.arbitrary_source_ingestion_claim,
        "arbitrary_third_party_backend_execution_claim": (
            report.arbitrary_third_party_backend_execution_claim
        ),
        "artifact_policy": report.artifact_policy,
        "blocked_claims": list(report.blocked_claims),
        "claim_id": report.claim_id,
        "claim_statement": report.claim_statement,
        "claim_status": report.claim_status,
        "cuda_replacement_claim": report.cuda_replacement_claim,
        "evidence": [_evidence_binding_to_dict(item) for item in report.evidence],
        "evidence_count": len(report.evidence),
        "evidence_policy": report.evidence_policy,
        "external_plugin_execution_claim": report.external_plugin_execution_claim,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_passed": True,
        "gate_status": report.gate_status,
        "generated_artifact_execution_claim": report.generated_artifact_execution_claim,
        "iree_replacement_claim": report.iree_replacement_claim,
        "issues": [],
        "native_performance_claim": report.native_performance_claim,
        "production_compiler_claim": report.production_compiler_claim,
        "real_hardware_backend_execution_claim": (
            report.real_hardware_backend_execution_claim
        ),
        "research_scope_claim": report.research_scope_claim,
        "required_invariants": list(report.required_invariants),
        "rocm_replacement_claim": report.rocm_replacement_claim,
        "schema_version": report.schema_version,
        "scope_boundary": report.scope_boundary,
        "source_ingestion_admitted": report.source_ingestion_admitted,
        "supported_claims": list(report.supported_claims),
        "time_horizon_claim": report.time_horizon_claim,
        "tvm_replacement_claim": report.tvm_replacement_claim,
        "xla_replacement_claim": report.xla_replacement_claim,
    }
    payload["scope_report_digest"] = _digest_payload(payload)
    assert_research_scope_claim_gate_report_contract(payload)
    return payload


def dump_research_scope_claim_gate_report(
    report: ResearchScopeClaimGateReport,
) -> str:
    """Serialize a research-scope claim gate deterministically."""

    text = json.dumps(
        research_scope_claim_gate_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RESEARCH_SCOPE_REPORT_BYTES:
        raise ResearchScopeClaimGateError("research scope report exceeds size limit")
    return f"{text}\n"


def assert_research_scope_claim_gate_report(
    report: ResearchScopeClaimGateReport,
) -> None:
    """Fail closed unless the report object matches the current scope contract."""

    if not isinstance(report, ResearchScopeClaimGateReport):
        raise ResearchScopeClaimGateError("expected ResearchScopeClaimGateReport")
    _validate_evidence_bindings(report.evidence)
    _assert_blocked_claim_flags(report)


def assert_research_scope_claim_gate_report_contract(report: object) -> None:
    """Fail closed unless a JSON-compatible report matches v0 exactly."""

    if not isinstance(report, Mapping):
        raise ResearchScopeClaimGateError("research scope report must be an object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise ResearchScopeClaimGateError("research scope top-level keys drift")

    expected: dict[str, object] = {
        "adoption_status": RESEARCH_SCOPE_ADOPTION_STATUS,
        "arbitrary_source_ingestion_claim": False,
        "arbitrary_third_party_backend_execution_claim": False,
        "artifact_policy": RESEARCH_SCOPE_ARTIFACT_POLICY,
        "claim_id": RESEARCH_SCOPE_CLAIM_ID,
        "claim_statement": RESEARCH_SCOPE_CLAIM_STATEMENT,
        "claim_status": RESEARCH_SCOPE_CLAIM_STATUS,
        "cuda_replacement_claim": False,
        "evidence_count": len(RESEARCH_SCOPE_REQUIRED_EVIDENCE),
        "evidence_policy": RESEARCH_SCOPE_EVIDENCE_POLICY,
        "external_plugin_execution_claim": False,
        "gate_contract": RESEARCH_SCOPE_CLAIM_GATE_CONTRACT,
        "gate_id": RESEARCH_SCOPE_CLAIM_GATE_ID,
        "gate_passed": True,
        "gate_status": RESEARCH_SCOPE_CLAIM_GATE_STATUS,
        "generated_artifact_execution_claim": False,
        "iree_replacement_claim": False,
        "issues": [],
        "native_performance_claim": False,
        "production_compiler_claim": False,
        "real_hardware_backend_execution_claim": False,
        "research_scope_claim": True,
        "rocm_replacement_claim": False,
        "schema_version": RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION,
        "scope_boundary": RESEARCH_SCOPE_BOUNDARY,
        "source_ingestion_admitted": False,
        "time_horizon_claim": RESEARCH_SCOPE_TIME_HORIZON_CLAIM,
        "tvm_replacement_claim": False,
        "xla_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ResearchScopeClaimGateError(f"research scope {key} drift")

    _assert_string_sequence(
        report.get("supported_claims"),
        RESEARCH_SCOPE_SUPPORTED_CLAIMS,
        "supported_claims",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        RESEARCH_SCOPE_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        RESEARCH_SCOPE_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_evidence_list(report.get("evidence"))
    report_digest = report.get("scope_report_digest")
    if not isinstance(report_digest, str) or not _SHA256_RE.fullmatch(report_digest):
        raise ResearchScopeClaimGateError("research scope report digest invalid")
    if report_digest != _digest_payload(report):
        raise ResearchScopeClaimGateError("research scope report digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


_TOP_LEVEL_KEYS = frozenset(
    {
        "adoption_status",
        "arbitrary_source_ingestion_claim",
        "arbitrary_third_party_backend_execution_claim",
        "artifact_policy",
        "blocked_claims",
        "claim_id",
        "claim_statement",
        "claim_status",
        "cuda_replacement_claim",
        "evidence",
        "evidence_count",
        "evidence_policy",
        "external_plugin_execution_claim",
        "gate_contract",
        "gate_id",
        "gate_passed",
        "gate_status",
        "generated_artifact_execution_claim",
        "iree_replacement_claim",
        "issues",
        "native_performance_claim",
        "production_compiler_claim",
        "real_hardware_backend_execution_claim",
        "research_scope_claim",
        "required_invariants",
        "rocm_replacement_claim",
        "schema_version",
        "scope_boundary",
        "scope_report_digest",
        "source_ingestion_admitted",
        "supported_claims",
        "time_horizon_claim",
        "tvm_replacement_claim",
        "xla_replacement_claim",
    }
)
_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_scope"}
)


def _evidence_binding_to_dict(
    binding: ResearchScopeEvidenceBinding,
) -> dict[str, object]:
    return {
        "contract": binding.contract,
        "digest": binding.digest,
        "evidence_id": binding.evidence_id,
        "source_free": binding.source_free,
        "status": binding.status,
        "supports_scope": binding.supports_scope,
    }


def _assert_blocked_claim_flags(report: ResearchScopeClaimGateReport) -> None:
    if report.production_compiler_claim:
        raise ResearchScopeClaimGateError("production compiler claim is not allowed")
    if report.cuda_replacement_claim:
        raise ResearchScopeClaimGateError("CUDA replacement claim is not allowed")
    if report.rocm_replacement_claim:
        raise ResearchScopeClaimGateError("ROCm replacement claim is not allowed")
    if report.xla_replacement_claim:
        raise ResearchScopeClaimGateError("XLA replacement claim is not allowed")
    if report.tvm_replacement_claim:
        raise ResearchScopeClaimGateError("TVM replacement claim is not allowed")
    if report.iree_replacement_claim:
        raise ResearchScopeClaimGateError("IREE replacement claim is not allowed")
    if report.native_performance_claim:
        raise ResearchScopeClaimGateError("native performance claim is not allowed")
    if report.real_hardware_backend_execution_claim:
        raise ResearchScopeClaimGateError("real hardware backend claim is not allowed")
    if report.arbitrary_source_ingestion_claim:
        raise ResearchScopeClaimGateError("arbitrary source ingestion claim is not allowed")
    if report.arbitrary_third_party_backend_execution_claim:
        raise ResearchScopeClaimGateError("third-party backend claim is not allowed")
    if report.generated_artifact_execution_claim:
        raise ResearchScopeClaimGateError("generated artifact execution is not allowed")
    if report.external_plugin_execution_claim:
        raise ResearchScopeClaimGateError("external plugin execution is not allowed")
    if report.source_ingestion_admitted:
        raise ResearchScopeClaimGateError("source ingestion must remain blocked")


def _validate_evidence_bindings(
    evidence: tuple[ResearchScopeEvidenceBinding, ...],
) -> None:
    if len(evidence) > MAX_RESEARCH_SCOPE_EVIDENCE:
        raise ResearchScopeClaimGateError("too many research scope evidence bindings")
    if len(evidence) != len(RESEARCH_SCOPE_REQUIRED_EVIDENCE):
        raise ResearchScopeClaimGateError("research scope evidence count drift")
    seen: set[str] = set()
    for binding, requirement in zip(
        evidence,
        RESEARCH_SCOPE_REQUIRED_EVIDENCE,
        strict=True,
    ):
        if not isinstance(binding, ResearchScopeEvidenceBinding):
            raise ResearchScopeClaimGateError("research scope evidence binding invalid")
        if binding.evidence_id in seen:
            raise ResearchScopeClaimGateError("research scope duplicate evidence id")
        seen.add(binding.evidence_id)
        if binding.evidence_id != requirement.evidence_id:
            raise ResearchScopeClaimGateError("research scope evidence id drift")
        if binding.contract != requirement.contract:
            raise ResearchScopeClaimGateError("research scope evidence contract drift")
        if binding.status != requirement.status:
            raise ResearchScopeClaimGateError("research scope evidence status drift")
        if binding.source_free is not True:
            raise ResearchScopeClaimGateError("research scope evidence source_free drift")
        if binding.supports_scope is not True:
            raise ResearchScopeClaimGateError("research scope evidence supports_scope drift")


def _assert_evidence_list(value: object) -> None:
    if not isinstance(value, list):
        raise ResearchScopeClaimGateError("research scope evidence must be list")
    if len(value) != len(RESEARCH_SCOPE_REQUIRED_EVIDENCE):
        raise ResearchScopeClaimGateError("research scope evidence count drift")
    for item, requirement in zip(value, RESEARCH_SCOPE_REQUIRED_EVIDENCE, strict=True):
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise ResearchScopeClaimGateError("research scope evidence keys drift")
        expected = {
            "evidence_id": requirement.evidence_id,
            "contract": requirement.contract,
            "source_free": True,
            "status": requirement.status,
            "supports_scope": True,
        }
        for key, expected_value in expected.items():
            if item.get(key) != expected_value:
                raise ResearchScopeClaimGateError(f"research scope evidence {key} drift")
        digest = item.get("digest")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ResearchScopeClaimGateError("research scope evidence digest invalid")


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value, field)) != expected:
        raise ResearchScopeClaimGateError(f"research scope {field} drift")


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ResearchScopeClaimGateError(f"research scope {field} must be list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ResearchScopeClaimGateError(f"research scope {field} item invalid")
        _validate_token(item, f"research scope {field}")
        result.append(item)
    return result


def _validate_token(value: str, field: str) -> None:
    if not isinstance(value, str):
        raise ResearchScopeClaimGateError(f"{field} must be text")
    if not value:
        raise ResearchScopeClaimGateError(f"{field} must not be empty")
    if len(value.encode("utf-8")) > MAX_RESEARCH_SCOPE_FIELD_BYTES:
        raise ResearchScopeClaimGateError(f"{field} exceeds size limit")
    if not _TOKEN_RE.fullmatch(value):
        raise ResearchScopeClaimGateError(f"{field} contains unsupported characters")
    _assert_text_is_source_free(value)


def _digest_payload(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("scope_report_digest", None)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ResearchScopeClaimGateError(
                f"research scope report contains forbidden fragment: {fragment}"
            )


__all__ = [
    "RESEARCH_SCOPE_ADOPTION_STATUS",
    "RESEARCH_SCOPE_ARTIFACT_POLICY",
    "RESEARCH_SCOPE_BLOCKED_CLAIMS",
    "RESEARCH_SCOPE_BOUNDARY",
    "RESEARCH_SCOPE_CLAIM_GATE_CONTRACT",
    "RESEARCH_SCOPE_CLAIM_GATE_ID",
    "RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION",
    "RESEARCH_SCOPE_CLAIM_GATE_STATUS",
    "RESEARCH_SCOPE_CLAIM_ID",
    "RESEARCH_SCOPE_CLAIM_STATEMENT",
    "RESEARCH_SCOPE_CLAIM_STATUS",
    "RESEARCH_SCOPE_EVIDENCE_POLICY",
    "RESEARCH_SCOPE_REQUIRED_EVIDENCE",
    "RESEARCH_SCOPE_REQUIRED_INVARIANTS",
    "RESEARCH_SCOPE_SUPPORTED_CLAIMS",
    "RESEARCH_SCOPE_TIME_HORIZON_CLAIM",
    "ResearchScopeClaimGateError",
    "ResearchScopeClaimGateReport",
    "ResearchScopeEvidenceBinding",
    "ResearchScopeEvidenceRequirement",
    "assert_research_scope_claim_gate_report",
    "assert_research_scope_claim_gate_report_contract",
    "build_research_scope_claim_gate_report",
    "dump_research_scope_claim_gate_report",
    "research_scope_claim_gate_report_to_dict",
]
