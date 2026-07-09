"""CI replay evidence primitives for the future admitted source slice."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT = "ci_replay_for_admitted_slice.ci.v0"
CI_REPLAY_FOR_ADMITTED_SLICE_STATUS = "PASS"
CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE = "deterministic_digest_replay_only"
CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY = "digest_only_source_free"
CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY = "github_actions_read_only_replay"
CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS = (
    "github_actions_permissions_contents_read",
    "checkout_persist_credentials_false",
    "ruff_required",
    "mypy_required",
    "pytest_required",
    "admitted_slice_replay_step_required",
    "deterministic_report_goldens_bound",
    "source_intent_plain_data_golden_bound",
    "digest_only_report",
    "source_free_report",
    "direct_source_ingestion_remains_blocked",
    "no_source_to_compute_graph",
    "no_source_to_hac_ir",
    "no_source_to_runtime_plan",
    "no_triton_jit",
    "no_device_access",
    "no_generated_artifacts",
)
CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS = (
    "bounded_source_buffer_api",
    "source_ingestion_sandbox_implementation",
    "parser_fuzz_negative_corpus_for_admitting_slice",
    "source_free_diagnostics_admission_tests",
    "source_to_intent_plain_data_output_golden_for_admitted_slice",
)
CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES = (
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
    "python_import",
    "network_access",
    "subprocess_execution",
    "dynamic_library_loading",
)

MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_ITEMS = 16
MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_BYTES = 128 * 1024
MAX_CI_REPLAY_FOR_ADMITTED_SLICE_FIELD_BYTES = 512

_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
        "url",
    }
)


class AdmittedSliceCIReplayError(ValueError):
    """Raised when admitted-slice CI replay evidence drifts."""


@dataclass(frozen=True)
class AdmittedSliceCIReplayItem:
    """One replayed evidence report summarized by digest only."""

    evidence_id: str
    contract: str
    status: str
    digest: str
    source_free: bool
    replayed: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        _validate_report_text(self.contract, "contract")
        _validate_report_text(self.status, "status")
        _validate_digest(self.digest, "digest")
        if self.source_free is not True:
            raise AdmittedSliceCIReplayError("CI replay item must be source-free")
        if self.replayed is not True:
            raise AdmittedSliceCIReplayError("CI replay item must be replayed")


@dataclass(frozen=True)
class AdmittedSliceCIReplayReport:
    """Digest-only CI replay evidence for the future admitted source slice."""

    replayed_evidence: tuple[AdmittedSliceCIReplayItem, ...]
    ci_workflow_digest: str
    ci_workflow_permissions: str
    ci_checkout_credentials: str
    ci_replay_step_bound: bool
    contract: str = CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT
    status: str = CI_REPLAY_FOR_ADMITTED_SLICE_STATUS
    target_slice: str = CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE
    replay_mode: str = CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE
    artifact_policy: str = CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY
    ci_binding_policy: str = CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY
    admission_effect: str = CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT
    required_controls: tuple[str, ...] = CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS
    blocked_execution_surfaces: tuple[str, ...] = (
        CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.contract != CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT:
            raise AdmittedSliceCIReplayError("CI replay contract drift")
        if self.status != CI_REPLAY_FOR_ADMITTED_SLICE_STATUS:
            raise AdmittedSliceCIReplayError("CI replay status drift")
        if self.target_slice != CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE:
            raise AdmittedSliceCIReplayError("CI replay target slice drift")
        if self.replay_mode != CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE:
            raise AdmittedSliceCIReplayError("CI replay mode drift")
        if self.artifact_policy != CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY:
            raise AdmittedSliceCIReplayError("CI replay artifact policy drift")
        if self.ci_binding_policy != CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY:
            raise AdmittedSliceCIReplayError("CI replay binding policy drift")
        if self.admission_effect != CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT:
            raise AdmittedSliceCIReplayError("CI replay admission effect drift")
        _validate_digest(self.ci_workflow_digest, "ci_workflow_digest")
        if self.ci_workflow_permissions != "contents_read":
            raise AdmittedSliceCIReplayError("CI replay workflow permissions drift")
        if self.ci_checkout_credentials != "persist_credentials_false":
            raise AdmittedSliceCIReplayError("CI replay checkout credentials drift")
        if self.ci_replay_step_bound is not True:
            raise AdmittedSliceCIReplayError("CI replay step binding drift")
        _validate_exact_tuple(
            self.required_controls,
            CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_replayed_evidence(self.replayed_evidence)

    @property
    def replayed_evidence_count(self) -> int:
        """Return replayed evidence count."""

        return len(self.replayed_evidence)

    @property
    def all_replayed(self) -> bool:
        """Return whether every replay item passed."""

        return all(item.replayed for item in self.replayed_evidence)


def build_admitted_slice_ci_replay_report(
    replayed_evidence: Iterable[AdmittedSliceCIReplayItem],
    *,
    ci_workflow_digest: str,
    ci_workflow_permissions: str,
    ci_checkout_credentials: str,
    ci_replay_step_bound: bool,
) -> AdmittedSliceCIReplayReport:
    """Build admitted-slice CI replay evidence."""

    return AdmittedSliceCIReplayReport(
        replayed_evidence=tuple(replayed_evidence),
        ci_workflow_digest=ci_workflow_digest,
        ci_workflow_permissions=ci_workflow_permissions,
        ci_checkout_credentials=ci_checkout_credentials,
        ci_replay_step_bound=ci_replay_step_bound,
    )


def admitted_slice_ci_replay_report_to_dict(
    report: AdmittedSliceCIReplayReport,
) -> dict[str, object]:
    """Return stable JSON-ready admitted-slice CI replay evidence."""

    if not isinstance(report, AdmittedSliceCIReplayReport):
        raise TypeError("admitted-slice CI replay report must be report object")
    return {
        "admission_effect": report.admission_effect,
        "all_replayed": report.all_replayed,
        "artifact_policy": report.artifact_policy,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "ci_binding_policy": report.ci_binding_policy,
        "ci_checkout_credentials": report.ci_checkout_credentials,
        "ci_replay_step_bound": report.ci_replay_step_bound,
        "ci_workflow_digest": report.ci_workflow_digest,
        "ci_workflow_permissions": report.ci_workflow_permissions,
        "contract": report.contract,
        "direct_source_ingestion": False,
        "replay_mode": report.replay_mode,
        "replayed_evidence": [
            {
                "contract": item.contract,
                "digest": item.digest,
                "evidence_id": item.evidence_id,
                "replayed": item.replayed,
                "source_free": item.source_free,
                "status": item.status,
            }
            for item in report.replayed_evidence
        ],
        "replayed_evidence_count": report.replayed_evidence_count,
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": report.status,
        "target_slice": report.target_slice,
    }


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return canonical digest for JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def digest_text(text: str) -> str:
    """Return canonical digest for text inputs."""

    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def dump_admitted_slice_ci_replay_report(
    report: AdmittedSliceCIReplayReport,
) -> str:
    """Render stable admitted-slice CI replay evidence."""

    payload = admitted_slice_ci_replay_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_BYTES:
        raise AdmittedSliceCIReplayError("CI replay report exceeds byte limit")
    return text + "\n"


def _validate_replayed_evidence(
    replayed_evidence: tuple[AdmittedSliceCIReplayItem, ...],
) -> None:
    if type(replayed_evidence) is not tuple:
        raise TypeError("CI replay evidence must be tuple")
    if len(replayed_evidence) > MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_ITEMS:
        raise AdmittedSliceCIReplayError("CI replay evidence count exceeds limit")
    observed_ids = tuple(item.evidence_id for item in replayed_evidence)
    if observed_ids != CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS:
        raise AdmittedSliceCIReplayError("CI replay evidence IDs drift")
    if len(observed_ids) != len(set(observed_ids)):
        raise AdmittedSliceCIReplayError("CI replay evidence IDs must be unique")
    digests = [item.digest for item in replayed_evidence]
    if len(digests) != len(set(digests)):
        raise AdmittedSliceCIReplayError("CI replay evidence digests must be unique")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"CI replay {label} must be tuple")
    if values != expected:
        raise AdmittedSliceCIReplayError(f"CI replay {label} drift")
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise AdmittedSliceCIReplayError(f"CI replay {label} must be report-safe")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise AdmittedSliceCIReplayError(f"CI replay {label} must be report-safe")
    if len(value.encode("utf-8")) > MAX_CI_REPLAY_FOR_ADMITTED_SLICE_FIELD_BYTES:
        raise AdmittedSliceCIReplayError(f"CI replay {label} exceeds limit")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AdmittedSliceCIReplayError(f"CI replay {label} must be sha256")


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in (
        "@triton.jit",
        "import os",
        "import triton",
        "tl.dot",
        "tl.store",
        '"backend_artifact":',
        '"command_line":',
        '"device_id":',
        '"file_path":',
        '"generated_code":',
        '"host_path":',
        '"plugin_entrypoint":',
        '"python_source":',
        '"raw_source":',
        '"raw_source_text":',
        '"raw_tensor_value":',
        '"runtime_handle":',
        '"source_intent_payload":',
        '"source_text":',
    ):
        if fragment in lowered:
            raise AdmittedSliceCIReplayError(
                f"CI replay contains forbidden fragment: {fragment}"
            )


__all__ = [
    "CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT",
    "CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY",
    "CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES",
    "CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY",
    "CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT",
    "CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS",
    "CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE",
    "CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS",
    "CI_REPLAY_FOR_ADMITTED_SLICE_STATUS",
    "CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE",
    "MAX_CI_REPLAY_FOR_ADMITTED_SLICE_FIELD_BYTES",
    "MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_ITEMS",
    "MAX_CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_BYTES",
    "AdmittedSliceCIReplayError",
    "AdmittedSliceCIReplayItem",
    "AdmittedSliceCIReplayReport",
    "admitted_slice_ci_replay_report_to_dict",
    "build_admitted_slice_ci_replay_report",
    "digest_json_payload",
    "digest_text",
    "dump_admitted_slice_ci_replay_report",
]
