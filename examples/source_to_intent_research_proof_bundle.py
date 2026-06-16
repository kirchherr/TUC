"""Emit a digest-only review bundle for the Source-to-Intent research proof."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_diagnostics import (
        build_report as build_diagnostics_report,
    )
    from examples.source_to_intent_research_evidence_gate import (
        build_gate_report as build_evidence_gate_report,
    )
    from examples.source_to_intent_research_execution_bridge import (
        assert_execution_bridge_report_contract,
    )
    from examples.source_to_intent_research_execution_bridge import (
        build_report as build_execution_bridge_report,
    )
    from examples.source_to_intent_research_idiom_alignment import (
        assert_research_idiom_alignment_report_contract,
    )
    from examples.source_to_intent_research_idiom_alignment import (
        build_report as build_idiom_alignment_report,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        REQUIRED_PARSER_SOURCE_NAMES,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        build_gate_report as build_conformance_gate_report,
    )
    from examples.source_to_intent_research_preflight_bridge import (
        assert_preflight_bridge_report_contract,
    )
    from examples.source_to_intent_research_preflight_bridge import (
        build_report as build_preflight_bridge_report,
    )
    from examples.source_to_intent_research_readiness import (
        build_report as build_readiness_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_diagnostics import (  # type: ignore[no-redef]
        build_report as build_diagnostics_report,
    )
    from source_to_intent_research_evidence_gate import (  # type: ignore[no-redef]
        build_gate_report as build_evidence_gate_report,
    )
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        assert_execution_bridge_report_contract,
    )
    from source_to_intent_research_execution_bridge import (
        build_report as build_execution_bridge_report,
    )
    from source_to_intent_research_idiom_alignment import (  # type: ignore[no-redef]
        assert_research_idiom_alignment_report_contract,
    )
    from source_to_intent_research_idiom_alignment import (
        build_report as build_idiom_alignment_report,
    )
    from source_to_intent_research_parser_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_PARSER_SOURCE_NAMES,
    )
    from source_to_intent_research_parser_conformance_gate import (
        build_gate_report as build_conformance_gate_report,
    )
    from source_to_intent_research_preflight_bridge import (  # type: ignore[no-redef]
        assert_preflight_bridge_report_contract,
    )
    from source_to_intent_research_preflight_bridge import (
        build_report as build_preflight_bridge_report,
    )
    from source_to_intent_research_readiness import (  # type: ignore[no-redef]
        build_report as build_readiness_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_proof_bundle_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT = (
    "source_to_intent_research_proof_bundle.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_ARTIFACT_POLICY = (
    "digest_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CLAIM = (
    "safe_source_to_runtime_research_slice"
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_SOURCE_BOUNDARY = (
    "preflight_to_source_intent_plain_data_to_runtime"
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_BLOCKED_CLAIMS = (
    "general_triton_source_ingestion",
    "native_performance_claim",
    "production_parser",
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REVIEW_CLAIMS = (
    "default_parser_blocked",
    "idiom_scope_bound",
    "preflight_gated",
    "runtime_execution_controlled",
    "source_intent_plain_data_only",
)
SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "python_source",
    "raw_source_text",
    "raw_tensor_value",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_parser_sources",
        "artifact_count",
        "artifact_policy",
        "artifacts",
        "blocked_claims",
        "bundle_contract",
        "claim",
        "default_parser_status",
        "parser_output_policy",
        "parser_status",
        "required_artifacts",
        "review_claims",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_ARTIFACT_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_ARTIFACTS = (
    (
        "source_to_intent_research_readiness",
        "json_report",
        "source_to_intent_parser_gate.blocking.v0",
    ),
    (
        "source_to_intent_research_parser_conformance_gate",
        "text_gate",
        "source_to_intent_research_parser_conformance_gate.ci.v0",
    ),
    (
        "source_to_intent_research_diagnostics",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
    ),
    (
        "source_to_intent_research_preflight_bridge",
        "json_report",
        "source_to_intent_research_preflight_bridge.execution_free.v0",
    ),
    (
        "source_to_intent_research_execution_bridge",
        "json_report",
        "source_to_intent_research_execution_bridge.explicit.v0",
    ),
    (
        "source_to_intent_research_idiom_alignment",
        "json_report",
        "source_to_intent_research_idiom_alignment.scope.v0",
    ),
    (
        "source_to_intent_research_evidence_gate",
        "text_gate",
        "source_to_intent_research_evidence_gate.ci.v0",
    ),
)


def build_proof_bundle_report() -> dict[str, object]:
    """Return a source-free digest bundle for reviewing the research proof."""

    artifact_texts = {
        "source_to_intent_research_readiness": build_readiness_report(),
        "source_to_intent_research_parser_conformance_gate": (
            build_conformance_gate_report()
        ),
        "source_to_intent_research_diagnostics": build_diagnostics_report(),
        "source_to_intent_research_preflight_bridge": build_preflight_bridge_report(),
        "source_to_intent_research_execution_bridge": build_execution_bridge_report(),
        "source_to_intent_research_idiom_alignment": build_idiom_alignment_report(),
        "source_to_intent_research_evidence_gate": build_evidence_gate_report(),
    }
    _assert_artifact_payloads(artifact_texts)
    artifacts = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "contract": contract,
            "digest": _digest(artifact_texts[artifact_id]),
            "status": "accepted",
        }
        for artifact_id, artifact_kind, contract in _REQUIRED_ARTIFACTS
    ]
    report: dict[str, object] = {
        "accepted_parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "artifact_count": len(artifacts),
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_ARTIFACT_POLICY,
        "artifacts": artifacts,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_BLOCKED_CLAIMS),
        "bundle_contract": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
        "claim": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CLAIM,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "required_artifacts": [artifact[0] for artifact in _REQUIRED_ARTIFACTS],
        "review_claims": list(SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REVIEW_CLAIMS),
        "schema_version": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    assert_proof_bundle_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the research proof bundle."""

    return json.dumps(build_proof_bundle_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_proof_bundle_report_contract(report: object) -> None:
    """Fail closed unless the proof bundle report matches the v0 contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research proof bundle report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "accepted_parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "artifact_count": len(_REQUIRED_ARTIFACTS),
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_BLOCKED_CLAIMS),
        "bundle_contract": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
        "claim": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CLAIM,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "required_artifacts": [artifact[0] for artifact in _REQUIRED_ARTIFACTS],
        "review_claims": list(SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REVIEW_CLAIMS),
        "schema_version": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                "source-to-intent research proof bundle "
                f"{key} contract drift"
            )
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("source-to-intent research proof bundle artifacts drift")
    observed_ids = []
    for index, artifact in enumerate(artifacts):
        observed_ids.append(_assert_artifact_contract(index, artifact))
    if tuple(observed_ids) != tuple(artifact[0] for artifact in _REQUIRED_ARTIFACTS):
        raise ValueError("source-to-intent research proof bundle artifact order drift")
    _assert_report_is_source_free(report)


def _assert_artifact_payloads(artifact_texts: Mapping[str, str]) -> None:
    readiness = json.loads(artifact_texts["source_to_intent_research_readiness"])
    if readiness["ready"] is not True:
        raise ValueError("source-to-intent research proof bundle readiness drift")
    preflight = json.loads(artifact_texts["source_to_intent_research_preflight_bridge"])
    assert_preflight_bridge_report_contract(preflight)
    execution = json.loads(artifact_texts["source_to_intent_research_execution_bridge"])
    assert_execution_bridge_report_contract(execution)
    alignment = json.loads(artifact_texts["source_to_intent_research_idiom_alignment"])
    assert_research_idiom_alignment_report_contract(alignment)
    evidence_gate = artifact_texts["source_to_intent_research_evidence_gate"]
    for artifact_id in (
        "source_to_intent_research_readiness",
        "source_to_intent_research_parser_conformance_gate",
        "source_to_intent_research_diagnostics",
        "source_to_intent_research_preflight_bridge",
        "source_to_intent_research_execution_bridge",
        "source_to_intent_research_idiom_alignment",
    ):
        if _digest(artifact_texts[artifact_id]) not in evidence_gate:
            raise ValueError(
                "source-to-intent research proof bundle evidence gate digest drift"
            )
    if 'status = "PASS"' not in evidence_gate:
        raise ValueError("source-to-intent research proof bundle gate status drift")


def _assert_artifact_contract(index: int, artifact: object) -> str:
    if not isinstance(artifact, Mapping):
        raise ValueError("source-to-intent research proof bundle artifact must be object")
    _assert_exact_keys("artifact", artifact, _ARTIFACT_KEYS)
    expected_id, expected_kind, expected_contract = _REQUIRED_ARTIFACTS[index]
    expected_values = {
        "artifact_id": expected_id,
        "artifact_kind": expected_kind,
        "contract": expected_contract,
        "status": "accepted",
    }
    for key, expected in expected_values.items():
        if artifact[key] != expected:
            raise ValueError(
                "source-to-intent research proof bundle "
                f"{key} contract drift"
            )
    digest = artifact["digest"]
    if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("source-to-intent research proof bundle digest drift")
    return expected_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research proof bundle {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research proof bundle report is not JSON data"
        ) from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research proof bundle report contains "
                "forbidden source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
