from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_ingestion_maintainer_security_review_packet import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
    SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION,
    SourceIngestionMaintainerSecurityReviewPacketError,
    assert_source_ingestion_maintainer_security_review_packet_contract,
    build_report,
    build_source_ingestion_maintainer_security_review_packet,
)
from tuc.frontend.source_ingestion_maintainer_review import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE,
    SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE,
)

SCHEMA_PATH = Path(
    "schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json"
)
DOC_PATH = Path("docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md")

EXPECTED_REVIEW_EVIDENCE_IDS = (
    "admitting_source_ingestion_rfc",
    "bounded_source_buffer_api",
    "source_ingestion_sandbox_implementation",
    "parser_fuzz_negative_corpus_for_admitting_slice",
    "source_free_diagnostics_admission_tests",
    "source_to_intent_plain_data_output_golden_for_admitted_slice",
    "ci_replay_for_admitted_slice",
    "real_triton_first_admissible_slice_plan",
)


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_ingestion_maintainer_security_review_packet()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_source_ingestion_maintainer_review_packet_passes() -> None:
    report = _cached_report()

    assert_source_ingestion_maintainer_security_review_packet_contract(report)
    assert report["schema_version"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert report["evidence_id"] == SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID
    assert report["contract"] == SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT
    assert report["status"] == SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS
    assert report["approval_status"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS
    )
    assert report["approval_required"] is True
    assert report["target_surface"] == SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE
    assert report["target_slice"] == SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE
    assert report["direct_source_ingestion"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["remaining_external_evidence"] == list(
        SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE
    )
    assert report["required_checks"] == list(
        SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS
    )
    assert report["blocked_execution_surfaces"] == list(
        SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES
    )
    assert [item["evidence_id"] for item in report["review_evidence"]] == list(
        EXPECTED_REVIEW_EVIDENCE_IDS
    )
    assert report["issues"] == []


def test_source_ingestion_maintainer_review_packet_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_ingestion_maintainer_review_packet_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_ingestion_maintainer_security_review_packet.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"approval_status": "not_approved"' in completed.stdout
    assert '"source_ingestion_admission_ready": false' in completed.stdout
    assert "maintainer_security_review_approval" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("status", "approved", "status"),
        ("approval_status", "approved", "approval_status"),
        ("approval_required", False, "approval_required"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_ingestion_admission_ready", True, "source_ingestion_admission_ready"),
        ("remaining_external_evidence_count", 0, "remaining_external_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_ingestion_maintainer_review_packet_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(
        SourceIngestionMaintainerSecurityReviewPacketError,
        match=match,
    ):
        assert_source_ingestion_maintainer_security_review_packet_contract(report)


def test_source_ingestion_maintainer_review_packet_rejects_evidence_order_drift() -> None:
    report = dict(_cached_report())
    evidence = list(report["review_evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["review_evidence"] = evidence

    with pytest.raises(
        SourceIngestionMaintainerSecurityReviewPacketError,
        match="evidence order",
    ):
        assert_source_ingestion_maintainer_security_review_packet_contract(report)


def test_source_ingestion_maintainer_review_packet_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(
        SourceIngestionMaintainerSecurityReviewPacketError,
        match="digest drift",
    ):
        assert_source_ingestion_maintainer_security_review_packet_contract(report)


def test_source_ingestion_maintainer_review_packet_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(
        SourceIngestionMaintainerSecurityReviewPacketError,
        match="top-level keys",
    ):
        assert_source_ingestion_maintainer_security_review_packet_contract(report)


def test_source_ingestion_maintainer_review_packet_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_id"]["const"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID
    )
    assert schema["properties"]["contract"]["const"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT
    )
    assert schema["properties"]["approval_status"]["const"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS
    )
    assert schema["properties"]["review_evidence_count"]["const"] == len(
        EXPECTED_REVIEW_EVIDENCE_IDS
    )
    assert [
        item["const"]
        for item in schema["properties"]["remaining_external_evidence"]["prefixItems"]
    ] == list(SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE)


def test_source_ingestion_maintainer_review_packet_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command_line",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)


def test_source_ingestion_maintainer_review_packet_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert golden["approval_status"] == "not_approved"
    assert golden["source_ingestion_admission_ready"] is False
    assert golden["review_evidence_count"] == len(EXPECTED_REVIEW_EVIDENCE_IDS)


def test_source_ingestion_maintainer_review_packet_is_documented() -> None:
    schema_path = (
        "schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json"
    )
    example_path = "examples/source_ingestion_maintainer_security_review_packet.py"
    golden_path = (
        "tests/golden/frontend/"
        "source_ingestion_maintainer_security_review_packet_report.json"
    )
    module_path = "src/tuc/frontend/source_ingestion_maintainer_review.py"
    doc_path = "docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md"
    rfc_path = "rfcs/0265-source-ingestion-maintainer-security-review-packet.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert (
            rfc_path in text
            or path == Path(rfc_path)
            or path.name in {"README.md", "ROADMAP.md"}
        )


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
