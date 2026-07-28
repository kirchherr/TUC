from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_first_slice_maintainer_approval_request import (
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_APPROVAL_STATUS,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_CLAIMS,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_EXECUTION_SURFACES,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_DECISION,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_POLICY,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REQUIRED_INVARIANTS,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCOPE,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SLICE,
    REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SURFACE,
    RealTritonFirstSliceMaintainerApprovalRequestError,
    assert_real_triton_first_slice_maintainer_approval_request_report_contract,
    build_real_triton_first_slice_maintainer_approval_request_report,
    build_report,
)

SCHEMA_PATH = Path(
    "schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json"
)
DOC_PATH = Path("docs/REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST.md")
RFC_PATH = Path("rfcs/0278-real-triton-first-slice-maintainer-approval-request.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_real_triton_first_slice_maintainer_approval_request_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_real_triton_first_slice_maintainer_approval_request_shape() -> None:
    report = _cached_report()

    assert_real_triton_first_slice_maintainer_approval_request_report_contract(report)
    assert report["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION
    )
    assert report["request_id"] == REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID
    assert report["request_contract"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT
    )
    assert report["request_status"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS
    )
    assert report["approval_status"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_APPROVAL_STATUS
    )
    assert report["admission_decision"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_DECISION
    )
    assert report["approval_request_scope"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCOPE
    )
    assert report["target_surface"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SURFACE
    )
    assert report["target_slice"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SLICE
    )
    assert report["evidence_policy"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_POLICY
    )
    assert report["approval_request_is_approval"] is False
    assert report["external_approval_required"] is True
    assert report["approval_artifact_present"] is False
    assert report["admission_ready"] is False
    assert report["admitted"] is False
    assert report["direct_source_ingestion"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["surface_opened"] is False
    assert report["external_approval_evidence"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE
    )
    assert report["review_checklist"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST
    )
    assert report["blocked_claims"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_CLAIMS
    )
    assert report["blocked_execution_surfaces"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_EXECUTION_SURFACES
    )
    assert report["required_invariants"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REQUIRED_INVARIANTS
    )
    assert [item["artifact_id"] for item in report["review_packets"]] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS
    )
    assert report["issues"] == []
    assert report["source_free"] is True


def test_real_triton_first_slice_maintainer_approval_request_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_first_slice_maintainer_approval_request_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/real_triton_first_slice_maintainer_approval_request.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert (
        "real_triton_first_slice_maintainer_approval_request.data_only.v0"
        in completed.stdout
    )
    assert '"request_status": "ready_for_external_review"' in completed.stdout
    assert '"approval_request_is_approval": false' in completed.stdout
    assert '"approval_status": "not_approved"' in completed.stdout
    assert '"admitted": false' in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout
    assert '"host_path":' not in completed.stdout
    assert '"device_id":' not in completed.stdout


def test_real_triton_first_slice_maintainer_approval_request_rejects_fake_approval() -> None:
    with pytest.raises(
        RealTritonFirstSliceMaintainerApprovalRequestError,
        match="status drift",
    ):
        build_real_triton_first_slice_maintainer_approval_request_report(
            artifact_text_overrides={
                "source_ingestion_maintainer_approval_artifact": json.dumps(
                    {
                        "contract": "source_ingestion_maintainer_approval_artifact.absent.v0",
                        "status": "approved",
                    }
                )
            }
        )


def test_real_triton_first_slice_maintainer_approval_request_rejects_source_leakage() -> None:
    with pytest.raises(
        RealTritonFirstSliceMaintainerApprovalRequestError,
        match="forbidden fragment",
    ):
        build_real_triton_first_slice_maintainer_approval_request_report(
            artifact_text_overrides={
                "real_triton_first_slice_admission_readiness_gate": '{"source_text":"x"}'
            }
        )


def test_real_triton_first_slice_maintainer_approval_request_rejects_contract_drift() -> None:
    report = dict(_cached_report())
    report["admitted"] = True

    with pytest.raises(
        RealTritonFirstSliceMaintainerApprovalRequestError,
        match="admitted",
    ):
        assert_real_triton_first_slice_maintainer_approval_request_report_contract(report)


def test_real_triton_first_slice_maintainer_approval_request_rejects_order_drift() -> None:
    report = dict(_cached_report())
    packets = list(report["review_packets"])
    packets[0], packets[1] = packets[1], packets[0]
    report["review_packets"] = packets

    with pytest.raises(
        RealTritonFirstSliceMaintainerApprovalRequestError,
        match="evidence order",
    ):
        assert_real_triton_first_slice_maintainer_approval_request_report_contract(report)


def test_real_triton_first_slice_maintainer_approval_request_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION
    )
    assert schema["properties"]["request_id"]["const"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID
    )
    assert schema["properties"]["request_contract"]["const"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT
    )
    assert schema["properties"]["request_status"]["const"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS
    )
    assert schema["properties"]["approval_status"]["const"] == "not_approved"
    assert schema["properties"]["approval_request_is_approval"]["const"] is False
    assert schema["properties"]["admitted"]["const"] is False
    assert schema["properties"]["review_packet_count"]["const"] == len(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS
    )
    assert schema["properties"]["review_checklist"]["const"] == list(
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST
    )


def test_real_triton_first_slice_maintainer_approval_request_schema_fails_closed() -> None:
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
    for object_schema in _iter_object_schemas(schema):
        assert not (set(object_schema.get("properties", {})) & forbidden_properties)


def test_real_triton_first_slice_maintainer_approval_request_golden_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION
    )
    assert golden["approval_status"] == "not_approved"
    assert golden["approval_request_is_approval"] is False
    assert golden["admission_ready"] is False
    assert golden["admitted"] is False
    assert golden["surface_opened"] is False


def test_real_triton_first_slice_maintainer_approval_request_is_documented() -> None:
    schema_path = (
        "schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json"
    )
    example_path = "examples/real_triton_first_slice_maintainer_approval_request.py"
    golden_path = (
        "tests/golden/frontend/"
        "real_triton_first_slice_maintainer_approval_request_report.json"
    )
    doc_path = "docs/REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST.md"
    rfc_path = "rfcs/0278-real-triton-first-slice-maintainer-approval-request.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md"),
        Path("docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md"),
        Path("docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md"),
        Path("docs/SOURCE_INGESTION_ADMISSION_GATE.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        assert schema_path in text
        assert golden_path in text
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path == RFC_PATH


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))


def _assert_objects_fail_closed(schema: Any) -> None:
    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False


def _iter_object_schemas(schema: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append(schema)
        for value in schema.values():
            found.extend(_iter_object_schemas(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_iter_object_schemas(item))
    return found
