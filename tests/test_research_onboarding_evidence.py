from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.research_onboarding_evidence import build_report
from tuc import (
    RESEARCH_ONBOARDING_ARTIFACT_STATUS,
    RESEARCH_ONBOARDING_BLOCKED_CLAIMS,
    RESEARCH_ONBOARDING_CLAIM_STATUS,
    RESEARCH_ONBOARDING_CONTRACT,
    RESEARCH_ONBOARDING_DOCUMENTATION_PATHS,
    RESEARCH_ONBOARDING_PROOF_SHAPE,
    RESEARCH_ONBOARDING_REPORT_ID,
    RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION,
    RESEARCH_ONBOARDING_REQUIRED_COMMANDS,
    ResearchOnboardingEvidenceStep,
    ResearchOnboardingReport,
    build_research_onboarding_report,
    dump_research_onboarding_report,
    research_onboarding_report_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path("schemas/research_onboarding_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/research_onboarding_report.json")


def test_research_onboarding_report_binds_first_proof_path() -> None:
    report = build_research_onboarding_report()
    payload = research_onboarding_report_to_dict(report)

    assert payload["schema_version"] == RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION
    assert payload["report_id"] == RESEARCH_ONBOARDING_REPORT_ID
    assert payload["onboarding_contract"] == RESEARCH_ONBOARDING_CONTRACT
    assert payload["artifact_status"] == RESEARCH_ONBOARDING_ARTIFACT_STATUS
    assert payload["claim_status"] == RESEARCH_ONBOARDING_CLAIM_STATUS
    assert payload["proof_shape"] == list(RESEARCH_ONBOARDING_PROOF_SHAPE)
    assert payload["documentation_paths"] == list(RESEARCH_ONBOARDING_DOCUMENTATION_PATHS)
    assert payload["blocked_claims"] == list(RESEARCH_ONBOARDING_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["native_performance_claim"] is False
    assert payload["broad_source_parser_claim"] is False
    assert payload["vendor_replacement_claim"] is False
    assert [step["command"] for step in payload["evidence_steps"]] == list(
        RESEARCH_ONBOARDING_REQUIRED_COMMANDS
    )
    assert len(str(payload["evidence_metadata_digest"])) == 64


def test_research_onboarding_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n")

    assert dump_research_onboarding_report(build_research_onboarding_report()) == (
        expected + "\n"
    )
    assert build_report() == expected + "\n"


def test_research_onboarding_rejects_unsupported_command() -> None:
    with pytest.raises(ValueError, match="unsupported onboarding command"):
        ResearchOnboardingEvidenceStep(
            evidence_id="bad_command",
            command="python examples/unknown.py",
            purpose="attempt_unreviewed_path",
            artifact_kind="unknown_artifact",
            documentation_path="docs/RESEARCH_ONBOARDING_SLICE.md",
        )


def test_research_onboarding_rejects_claim_expansion() -> None:
    report = build_research_onboarding_report()

    with pytest.raises(ValueError, match="native performance"):
        ResearchOnboardingReport(
            report_id=report.report_id,
            evidence_steps=report.evidence_steps,
            native_performance_claim=True,
        )

    with pytest.raises(ValueError, match="broad source parsing"):
        ResearchOnboardingReport(
            report_id=report.report_id,
            evidence_steps=report.evidence_steps,
            broad_source_parser_claim=True,
        )

    with pytest.raises(ValueError, match="vendor replacement"):
        ResearchOnboardingReport(
            report_id=report.report_id,
            evidence_steps=report.evidence_steps,
            vendor_replacement_claim=True,
        )


def test_research_onboarding_rejects_duplicate_commands() -> None:
    report = build_research_onboarding_report()
    duplicate = replace(report.evidence_steps[0], evidence_id="duplicate_command")

    with pytest.raises(ValueError, match="duplicate onboarding command"):
        ResearchOnboardingReport(
            report_id=report.report_id,
            evidence_steps=(report.evidence_steps[0], duplicate),
        )


def test_research_onboarding_rejects_path_like_text() -> None:
    with pytest.raises(ValueError, match="forbidden fragment"):
        ResearchOnboardingEvidenceStep(
            evidence_id="bad_path",
            command="python examples/proof_of_execution.py",
            purpose="attempt_path_escape",
            artifact_kind="deterministic_proof_output",
            documentation_path="docs/../SECRET.md",
        )


def test_research_onboarding_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = research_onboarding_report_to_dict(build_research_onboarding_report())

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RESEARCH_ONBOARDING_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RESEARCH_ONBOARDING_ARTIFACT_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["broad_source_parser_claim"]["const"] is False
    assert schema["properties"]["vendor_replacement_claim"]["const"] is False
    assert schema["properties"]["evidence_steps"]["maxItems"] == 16


def test_research_onboarding_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "raw_benchmark_output",
        "raw_timing_samples",
        "raw_tensor_value",
        "host_path",
        "device_id",
        "plugin_entrypoint",
        "dynamic_library",
        "generated_code",
        "source_text",
        "subprocess",
    ):
        assert forbidden not in json.dumps(schema)


def test_research_onboarding_docs_are_linked() -> None:
    schema_path = "schemas/research_onboarding_report.v0.schema.json"
    golden_path = "tests/golden/proofs/research_onboarding_report.json"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RESEARCH_ONBOARDING_SLICE.md"),
        Path("docs/RESEARCH_ONBOARDING_EVIDENCE.md"),
        Path("rfcs/0199-research-onboarding-evidence.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "RESEARCH_ONBOARDING_EVIDENCE.md" in text or path.name == (
            "RESEARCH_ONBOARDING_EVIDENCE.md"
        )

    evidence_doc = Path("docs/RESEARCH_ONBOARDING_EVIDENCE.md").read_text(
        encoding="utf-8"
    )
    assert schema_path in evidence_doc
    assert golden_path in evidence_doc


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
