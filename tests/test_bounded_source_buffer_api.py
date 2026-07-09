from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.bounded_source_buffer_api import (
    BOUNDED_SOURCE_BUFFER_API_ARTIFACT_POLICY,
    BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
    BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION,
    BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS,
    BoundedSourceBufferAPIReportError,
    assert_bounded_source_buffer_api_report_contract,
    build_bounded_source_buffer_api_report,
    build_report,
)
from tuc.frontend import (
    BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT,
    BOUNDED_SOURCE_BUFFER_API_CONTRACT,
    BOUNDED_SOURCE_BUFFER_API_STATUS,
    BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES,
    BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS,
    BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY,
    BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY,
    BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY,
    BoundedSourceBufferError,
    bound_source_buffer,
    bounded_source_buffer_record_to_dict,
)

SCHEMA_PATH = Path("schemas/bounded_source_buffer_api_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/bounded_source_buffer_api_report.json")
DOC_PATH = Path("docs/BOUNDED_SOURCE_BUFFER_API.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_bounded_source_buffer_api_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_bounded_source_buffer_api_accepts_metadata_only_record() -> None:
    record = bound_source_buffer(
        "def kernel(x):\n    y = x + 1\n    return y\n",
        source_name="unit_kernel",
        declared_shape_profile={"x": (4, 8), "y": (4, 8)},
    )
    payload = bounded_source_buffer_record_to_dict(record)

    assert payload["source_name"] == "unit_kernel"
    assert payload["api_contract"] == BOUNDED_SOURCE_BUFFER_API_CONTRACT
    assert payload["api_status"] == BOUNDED_SOURCE_BUFFER_API_STATUS
    assert payload["output_policy"] == BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY
    assert payload["raw_source_policy"] == BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY
    assert payload["diagnostic_policy"] == BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY
    assert payload["admission_effect"] == BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT
    assert payload["blocked_outputs"] == list(BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS)
    assert payload["blocked_execution_surfaces"] == list(
        BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES
    )
    assert "kernel(x)" not in json.dumps(payload, sort_keys=True)
    assert "raw_source" not in set(payload)
    assert "source_text" not in set(payload)


@pytest.mark.parametrize(
    ("source", "source_name", "shape_profile", "match"),
    (
        ("", "empty_case", {"x": (1,)}, "must not be empty"),
        (
            "\n".join("x = 1" for _ in range(2049)),
            "line_budget_case",
            {"x": (1,)},
            "line budget",
        ),
        ("def broken(:\n    pass\n", "syntax_case", {"x": (1,)}, "syntax"),
        ("x = 1\n", "../path", {"x": (1,)}, "report-safe"),
        ("x = 1\n", "bad_shape_case", {"x": (True,)}, "dimensions"),
    ),
)
def test_bounded_source_buffer_api_rejects_unsafe_inputs(
    source: str,
    source_name: str,
    shape_profile: dict[str, tuple[object, ...]],
    match: str,
) -> None:
    with pytest.raises((BoundedSourceBufferError, TypeError), match=match):
        bound_source_buffer(
            source,
            source_name=source_name,
            declared_shape_profile=shape_profile,  # type: ignore[arg-type]
        )


def test_bounded_source_buffer_api_report_passes() -> None:
    report = _cached_report()

    assert_bounded_source_buffer_api_report_contract(report)
    assert report["schema_version"] == BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION
    assert report["api_contract"] == BOUNDED_SOURCE_BUFFER_API_CONTRACT
    assert report["evidence_id"] == BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID
    assert report["api_status"] == BOUNDED_SOURCE_BUFFER_API_STATUS
    assert report["artifact_policy"] == BOUNDED_SOURCE_BUFFER_API_ARTIFACT_POLICY
    assert report["admission_effect"] == BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT
    assert report["accepted_case_count"] == 2
    assert report["rejection_case_count"] == 4
    assert report["required_controls"] == list(
        BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS
    )
    assert report["blocked_outputs"] == list(BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS)
    assert report["blocked_execution_surfaces"] == list(
        BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES
    )
    assert report["direct_source_ingestion"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["issues"] == []


def test_bounded_source_buffer_api_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_bounded_source_buffer_api_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/bounded_source_buffer_api.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"api_status": "implemented_non_admitting"' in completed.stdout
    assert '"direct_source_ingestion": false' in completed.stdout
    assert '"source_to_hac_ir": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_source":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("api_status", "admitting", "api_status"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("rejection_case_count", 0, "rejection_case_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_bounded_source_buffer_api_report_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(BoundedSourceBufferAPIReportError, match=match):
        assert_bounded_source_buffer_api_report_contract(report)


def test_bounded_source_buffer_api_report_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(BoundedSourceBufferAPIReportError, match="digest drift"):
        assert_bounded_source_buffer_api_report_contract(report)


def test_bounded_source_buffer_api_report_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    records = [dict(item) for item in report["accepted_records"]]  # type: ignore[union-attr]
    records[0]["source_text"] = "@triton.jit\ndef kernel():\n    pass\n"
    report["accepted_records"] = records

    with pytest.raises(BoundedSourceBufferAPIReportError, match="record keys"):
        assert_bounded_source_buffer_api_report_contract(report)


def test_bounded_source_buffer_api_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["api_contract"]["const"] == (
        BOUNDED_SOURCE_BUFFER_API_CONTRACT
    )
    assert schema["properties"]["api_status"]["const"] == (
        BOUNDED_SOURCE_BUFFER_API_STATUS
    )
    assert schema["properties"]["direct_source_ingestion"]["const"] is False
    assert schema["properties"]["source_to_compute_graph"]["const"] is False
    assert schema["properties"]["source_to_hac_ir"]["const"] is False
    assert schema["properties"]["source_to_runtime_plan"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS)
    assert [
        item["const"] for item in schema["properties"]["blocked_outputs"]["prefixItems"]
    ] == list(BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS)


def test_bounded_source_buffer_api_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "command_line",
        "device_id",
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
    }
    assert not (set(schema["properties"]) & forbidden_properties)
    assert not (
        set(schema["$defs"]["bounded_source_record"]["properties"])
        & forbidden_properties
    )


def test_bounded_source_buffer_api_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION
    assert golden["api_status"] == BOUNDED_SOURCE_BUFFER_API_STATUS
    assert golden["direct_source_ingestion"] is False
    assert golden["source_to_runtime_plan"] is False


def test_bounded_source_buffer_api_is_documented() -> None:
    schema_path = "schemas/bounded_source_buffer_api_report.v0.schema.json"
    example_path = "examples/bounded_source_buffer_api.py"
    golden_path = "tests/golden/frontend/bounded_source_buffer_api_report.json"
    doc_path = "docs/BOUNDED_SOURCE_BUFFER_API.md"
    rfc_path = "rfcs/0259-bounded-source-buffer-api.md"
    module_path = "src/tuc/frontend/bounded_source_buffer.py"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert doc_path in text or path == DOC_PATH
        assert module_path in text or path.name in {
            "README.md",
            "ROADMAP.md",
            "ROADMAP_STATUS.md",
        }
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert rfc_path in text or path.name in {"README.md", "ROADMAP.md"}


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
