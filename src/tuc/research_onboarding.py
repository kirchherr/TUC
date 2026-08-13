"""Data-only onboarding evidence for the first TUC research proof path."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION = "tuc.research_onboarding_report.v0"
RESEARCH_ONBOARDING_CONTRACT = "research_onboarding.first_proof_path.v0"
RESEARCH_ONBOARDING_ARTIFACT_STATUS = "review_evidence"
RESEARCH_ONBOARDING_CLAIM_STATUS = "bounded_research_claim"
RESEARCH_ONBOARDING_REPORT_ID = "objective_alpha_research_onboarding"
RESEARCH_ONBOARDING_REQUIRED_COMMANDS = (
    "python examples/proof_of_execution.py",
    "python examples/runtime_evidence_matrix.py",
    "python examples/runtime_evidence_gate.py",
)
RESEARCH_ONBOARDING_PROOF_SHAPE = (
    "Graph",
    "HAC-IR",
    "Runtime Plan",
    "Trusted Prototype Backends",
    "Reference-Checked Result",
    "Metadata-Only Evidence",
)
RESEARCH_ONBOARDING_DOCUMENTATION_PATHS = (
    "docs/RESEARCH_ONBOARDING_SLICE.md",
    "docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md",
    "docs/RUNTIME_EXECUTOR.md",
    "docs/RUNTIME_EVIDENCE_FLOW.md",
    "docs/PERFORMANCE_PROOF_BOUNDARY.md",
)
RESEARCH_ONBOARDING_BLOCKED_CLAIMS = (
    "native_performance_parity",
    "vendor_compiler_replacement",
    "broad_source_code_parsing",
    "arbitrary_third_party_backend_execution",
    "device_access",
    "generated_artifact_execution",
)
RESEARCH_ONBOARDING_MAX_FIELD_BYTES = 256
RESEARCH_ONBOARDING_MAX_STEPS = 16
RESEARCH_ONBOARDING_MAX_DOCS = 32
RESEARCH_ONBOARDING_MAX_REPORT_BYTES = 64 * 1024

_ONBOARDING_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")
_FORBIDDEN_TEXT_FRAGMENTS = (
    "..",
    "\\",
    "://",
    "backend_artifact",
    "device_id",
    "dynamic_library",
    "generated_code",
    "host_path",
    "import_module",
    "plugin_entrypoint",
    "python_source",
    "raw_benchmark_output",
    "raw_tensor_value",
    "raw_timing_samples",
    "source_text",
    "subprocess",
)


@dataclass(frozen=True)
class ResearchOnboardingEvidenceStep:
    """One fixed command-to-evidence link in the first onboarding path."""

    evidence_id: str
    command: str
    purpose: str
    artifact_kind: str
    documentation_path: str

    def __post_init__(self) -> None:
        _validate_onboarding_text(self.evidence_id, "onboarding evidence_id")
        _validate_onboarding_text(self.command, "onboarding command")
        _validate_onboarding_text(self.purpose, "onboarding purpose")
        _validate_onboarding_text(self.artifact_kind, "onboarding artifact_kind")
        _validate_onboarding_text(
            self.documentation_path,
            "onboarding documentation_path",
        )
        if self.command not in RESEARCH_ONBOARDING_REQUIRED_COMMANDS:
            raise ValueError(f"unsupported onboarding command: {self.command!r}")
        if self.documentation_path not in RESEARCH_ONBOARDING_DOCUMENTATION_PATHS:
            raise ValueError(
                f"unsupported onboarding documentation path: {self.documentation_path!r}"
            )


@dataclass(frozen=True)
class ResearchOnboardingReport:
    """Deterministic data-only report for the first research proof path."""

    report_id: str
    evidence_steps: tuple[ResearchOnboardingEvidenceStep, ...]
    proof_shape: tuple[str, ...] = RESEARCH_ONBOARDING_PROOF_SHAPE
    documentation_paths: tuple[str, ...] = RESEARCH_ONBOARDING_DOCUMENTATION_PATHS
    blocked_claims: tuple[str, ...] = RESEARCH_ONBOARDING_BLOCKED_CLAIMS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    onboarding_contract: str = RESEARCH_ONBOARDING_CONTRACT
    artifact_status: str = RESEARCH_ONBOARDING_ARTIFACT_STATUS
    claim_status: str = RESEARCH_ONBOARDING_CLAIM_STATUS
    native_performance_claim: bool = False
    broad_source_parser_claim: bool = False
    vendor_replacement_claim: bool = False

    def __post_init__(self) -> None:
        _validate_onboarding_text(self.report_id, "onboarding report_id")
        if self.proof_shape != RESEARCH_ONBOARDING_PROOF_SHAPE:
            raise ValueError("research onboarding proof shape changed")
        if self.documentation_paths != RESEARCH_ONBOARDING_DOCUMENTATION_PATHS:
            raise ValueError("research onboarding documentation paths changed")
        if self.blocked_claims != RESEARCH_ONBOARDING_BLOCKED_CLAIMS:
            raise ValueError("research onboarding blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("research onboarding blocked execution surfaces changed")
        if self.onboarding_contract != RESEARCH_ONBOARDING_CONTRACT:
            raise ValueError("research onboarding contract mismatch")
        if self.artifact_status != RESEARCH_ONBOARDING_ARTIFACT_STATUS:
            raise ValueError("research onboarding artifact status mismatch")
        if self.claim_status != RESEARCH_ONBOARDING_CLAIM_STATUS:
            raise ValueError("research onboarding claim status mismatch")
        if self.native_performance_claim:
            raise ValueError("research onboarding must not claim native performance")
        if self.broad_source_parser_claim:
            raise ValueError("research onboarding must not claim broad source parsing")
        if self.vendor_replacement_claim:
            raise ValueError("research onboarding must not claim vendor replacement")
        _validate_evidence_steps(self.evidence_steps)
        _validate_text_sequence(
            self.proof_shape,
            "research onboarding proof shape",
            max_items=16,
        )
        _validate_text_sequence(
            self.documentation_paths,
            "research onboarding documentation paths",
            max_items=RESEARCH_ONBOARDING_MAX_DOCS,
        )
        _validate_text_sequence(
            self.blocked_claims,
            "research onboarding blocked claims",
            max_items=16,
        )

    @property
    def evidence_metadata_digest(self) -> str:
        """Return a stable digest over the onboarding evidence contract."""

        return _metadata_digest(
            {
                "blocked_claims": self.blocked_claims,
                "blocked_execution_surfaces": self.blocked_execution_surfaces,
                "documentation_paths": self.documentation_paths,
                "evidence_steps": tuple(
                    _evidence_step_to_dict(step) for step in self.evidence_steps
                ),
                "proof_shape": self.proof_shape,
                "report_id": self.report_id,
            }
        )


def build_research_onboarding_report() -> ResearchOnboardingReport:
    """Build the current first-proof onboarding evidence report."""

    return ResearchOnboardingReport(
        report_id=RESEARCH_ONBOARDING_REPORT_ID,
        evidence_steps=(
            ResearchOnboardingEvidenceStep(
                evidence_id="proof_of_execution",
                command="python examples/proof_of_execution.py",
                purpose="execute_trusted_objective_alpha_slice",
                artifact_kind="deterministic_proof_output",
                documentation_path="docs/RESEARCH_ONBOARDING_SLICE.md",
            ),
            ResearchOnboardingEvidenceStep(
                evidence_id="runtime_evidence_matrix",
                command="python examples/runtime_evidence_matrix.py",
                purpose="inventory_required_runtime_evidence",
                artifact_kind="schema_versioned_matrix_report",
                documentation_path="docs/RUNTIME_EVIDENCE_FLOW.md",
            ),
            ResearchOnboardingEvidenceStep(
                evidence_id="runtime_evidence_gate",
                command="python examples/runtime_evidence_gate.py",
                purpose="verify_merge_facing_evidence_requirements",
                artifact_kind="deterministic_gate_output",
                documentation_path="docs/RUNTIME_EVIDENCE_FLOW.md",
            ),
        ),
    )


def research_onboarding_report_to_dict(
    report: ResearchOnboardingReport,
) -> dict[str, object]:
    """Return the stable JSON-compatible mapping for an onboarding report."""

    assert_research_onboarding_report(report)
    return {
        "artifact_status": report.artifact_status,
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "broad_source_parser_claim": report.broad_source_parser_claim,
        "claim_status": report.claim_status,
        "documentation_paths": list(report.documentation_paths),
        "evidence_metadata_digest": report.evidence_metadata_digest,
        "evidence_steps": [
            _evidence_step_to_dict(step) for step in report.evidence_steps
        ],
        "native_performance_claim": report.native_performance_claim,
        "onboarding_contract": report.onboarding_contract,
        "proof_shape": list(report.proof_shape),
        "report_id": report.report_id,
        "schema_version": RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION,
        "vendor_replacement_claim": report.vendor_replacement_claim,
    }


def dump_research_onboarding_report(report: ResearchOnboardingReport) -> str:
    """Serialize a research onboarding report deterministically."""

    text = json.dumps(
        research_onboarding_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > RESEARCH_ONBOARDING_MAX_REPORT_BYTES:
        raise ValueError("research onboarding report exceeds size limit")
    return f"{text}\n"


def assert_research_onboarding_report(report: ResearchOnboardingReport) -> None:
    """Fail closed when the onboarding report drifts beyond its contract."""

    if not isinstance(report, ResearchOnboardingReport):
        raise TypeError("expected ResearchOnboardingReport")
    if report.report_id != RESEARCH_ONBOARDING_REPORT_ID:
        raise ValueError("unexpected research onboarding report id")
    commands = tuple(step.command for step in report.evidence_steps)
    if commands != RESEARCH_ONBOARDING_REQUIRED_COMMANDS:
        raise ValueError("research onboarding commands changed")
    if report.native_performance_claim:
        raise ValueError("native performance claim is not allowed")
    if report.broad_source_parser_claim:
        raise ValueError("broad source parser claim is not allowed")
    if report.vendor_replacement_claim:
        raise ValueError("vendor replacement claim is not allowed")


def _evidence_step_to_dict(
    step: ResearchOnboardingEvidenceStep,
) -> dict[str, str]:
    return {
        "artifact_kind": step.artifact_kind,
        "command": step.command,
        "documentation_path": step.documentation_path,
        "evidence_id": step.evidence_id,
        "purpose": step.purpose,
    }


def _validate_evidence_steps(
    steps: tuple[ResearchOnboardingEvidenceStep, ...],
) -> None:
    if len(steps) > RESEARCH_ONBOARDING_MAX_STEPS:
        raise ValueError("too many research onboarding evidence steps")
    if not steps:
        raise ValueError("research onboarding evidence steps are required")
    seen_ids: set[str] = set()
    seen_commands: set[str] = set()
    for step in steps:
        if step.evidence_id in seen_ids:
            raise ValueError(f"duplicate onboarding evidence id: {step.evidence_id!r}")
        if step.command in seen_commands:
            raise ValueError(f"duplicate onboarding command: {step.command!r}")
        seen_ids.add(step.evidence_id)
        seen_commands.add(step.command)


def _validate_text_sequence(
    values: tuple[str, ...],
    field_name: str,
    *,
    max_items: int,
) -> None:
    if len(values) > max_items:
        raise ValueError(f"too many values for {field_name}")
    if not values:
        raise ValueError(f"{field_name} must not be empty")
    for value in values:
        _validate_onboarding_text(value, field_name)


def _validate_onboarding_text(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value.encode("utf-8")) > RESEARCH_ONBOARDING_MAX_FIELD_BYTES:
        raise ValueError(f"{field_name} exceeds size limit")
    if not _ONBOARDING_TEXT_RE.fullmatch(value):
        raise ValueError(f"{field_name} contains unsupported characters")
    lowered = value.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise ValueError(f"{field_name} contains forbidden fragment: {fragment}")


def _metadata_digest(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


__all__ = [
    "RESEARCH_ONBOARDING_ARTIFACT_STATUS",
    "RESEARCH_ONBOARDING_BLOCKED_CLAIMS",
    "RESEARCH_ONBOARDING_CLAIM_STATUS",
    "RESEARCH_ONBOARDING_CONTRACT",
    "RESEARCH_ONBOARDING_DOCUMENTATION_PATHS",
    "RESEARCH_ONBOARDING_PROOF_SHAPE",
    "RESEARCH_ONBOARDING_REPORT_ID",
    "RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION",
    "RESEARCH_ONBOARDING_REQUIRED_COMMANDS",
    "ResearchOnboardingEvidenceStep",
    "ResearchOnboardingReport",
    "assert_research_onboarding_report",
    "build_research_onboarding_report",
    "dump_research_onboarding_report",
    "research_onboarding_report_to_dict",
]
