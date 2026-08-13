from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_ingestion_sandbox_implementation import (
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_ARTIFACT_POLICY,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION,
    SourceIngestionSandboxImplementationReportError,
    assert_source_ingestion_sandbox_implementation_report_contract,
    build_report,
    build_source_ingestion_sandbox_implementation_report,
)
from tuc.frontend import (
    SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT,
    SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS,
    SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
    SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY,
    SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY,
    SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS,
    run_source_ingestion_sandbox,
    source_ingestion_sandbox_result_to_dict,
)

SCHEMA_PATH = Path("schemas/source_ingestion_sandbox_implementation_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_ingestion_sandbox_implementation_report.json"
)
DOC_PATH = Path("docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_ingestion_sandbox_implementation_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_source_ingestion_sandbox_accepts_metadata_only_result() -> None:
    result = run_source_ingestion_sandbox(
        "def kernel(x):\n    y = x + 1\n    return y\n",
        source_name="unit_sandbox_kernel",
        declared_shape_profile={"x": (4, 8), "y": (4, 8)},
    )
    payload = source_ingestion_sandbox_result_to_dict(result)

    assert payload["source_name"] == "unit_sandbox_kernel"
    assert payload["outcome"] == "accepted_metadata_only"
    assert payload["sandbox_contract"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT
    assert payload["sandbox_status"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS
    assert payload["output_policy"] == SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY
    assert payload["raw_source_policy"] == SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY
    assert payload["diagnostic_policy"] == SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY
    assert payload["admission_effect"] == SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT
    assert payload["blocked_outputs"] == list(SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS)
    assert payload["blocked_execution_surfaces"] == list(
        SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["direct_source_ingestion"] is False
    assert payload["source_to_intent_plain_data"] is False
    assert payload["source_to_compute_graph"] is False
    assert payload["source_to_hac_ir"] is False
    assert payload["source_to_runtime_plan"] is False
    assert "bounded_source_buffer_record_digest" in payload
    assert "kernel(x)" not in json.dumps(payload, sort_keys=True)
    assert "raw_source" not in set(payload)
    assert "source_text" not in set(payload)


@pytest.mark.parametrize(
    ("source", "source_name", "shape_profile", "reason_code", "safe_name"),
    (
        ("", "empty_case", {"x": (1,)}, "empty_source", "empty_case"),
        ("def broken(:\n    pass\n", "syntax_case", {"x": (1,)}, "syntax_error", "syntax_case"),
        ("x = 1\n", "shape_case", {"x": (True,)}, "shape_profile", "shape_case"),
        ("x = 1\n", "../path", {"x": (1,)}, "report_safe", "rejected_source_name"),
    ),
)
def test_source_ingestion_sandbox_rejects_source_free(
    source: str,
    source_name: str,
    shape_profile: dict[str, tuple[object, ...]],
    reason_code: str,
    safe_name: str,
) -> None:
    result = run_source_ingestion_sandbox(
        source,
        source_name=source_name,
        declared_shape_profile=shape_profile,  # type: ignore[arg-type]
    )
    payload = source_ingestion_sandbox_result_to_dict(result)

    assert payload["outcome"] == "rejected"
    assert payload["reason_code"] == reason_code
    assert payload["source_name"] == safe_name
    assert payload["source_free"] is True
    assert payload["direct_source_ingestion"] is False
    assert payload["source_to_intent_plain_data"] is False
    assert "source_text" not in set(payload)
    assert "raw_source" not in set(payload)


def test_source_ingestion_sandbox_implementation_report_passes() -> None:
    report = _cached_report()

    assert_source_ingestion_sandbox_implementation_report_contract(report)
    assert report["schema_version"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION
    )
    assert report["sandbox_contract"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT
    assert report["evidence_id"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID
    assert report["sandbox_status"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS
    assert report["artifact_policy"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_ARTIFACT_POLICY
    )
    assert report["accepted_case_count"] == 2
    assert report["rejection_case_count"] == 4
    assert report["required_controls"] == list(SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS)
    assert report["blocked_outputs"] == list(SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS)
    assert report["direct_source_ingestion"] is False
    assert report["source_to_intent_plain_data"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["issues"] == []


def test_source_ingestion_sandbox_implementation_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_ingestion_sandbox_implementation_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_ingestion_sandbox_implementation.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"sandbox_status": "implemented_non_admitting"' in completed.stdout
    assert '"direct_source_ingestion": false' in completed.stdout
    assert '"source_to_intent_plain_data": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_source":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("sandbox_status", "admitting", "sandbox_status"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_to_intent_plain_data", True, "source_to_intent_plain_data"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("rejection_case_count", 0, "rejection_case_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_ingestion_sandbox_implementation_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(SourceIngestionSandboxImplementationReportError, match=match):
        assert_source_ingestion_sandbox_implementation_report_contract(report)


def test_source_ingestion_sandbox_implementation_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(
        SourceIngestionSandboxImplementationReportError,
        match="digest drift",
    ):
        assert_source_ingestion_sandbox_implementation_report_contract(report)


def test_source_ingestion_sandbox_implementation_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    accepted = [dict(item) for item in report["accepted_results"]]  # type: ignore[union-attr]
    accepted[0]["source_text"] = "@triton.jit\ndef kernel():\n    pass\n"
    report["accepted_results"] = accepted

    with pytest.raises(
        SourceIngestionSandboxImplementationReportError,
        match="accepted result keys",
    ):
        assert_source_ingestion_sandbox_implementation_report_contract(report)


def test_source_ingestion_sandbox_implementation_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["sandbox_contract"]["const"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT
    )
    assert schema["properties"]["sandbox_status"]["const"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS
    )
    assert schema["properties"]["direct_source_ingestion"]["const"] is False
    assert schema["properties"]["source_to_intent_plain_data"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS)
    assert [
        item["const"] for item in schema["properties"]["blocked_outputs"]["prefixItems"]
    ] == list(SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS)


def test_source_ingestion_sandbox_implementation_schema_fails_closed() -> None:
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
    assert not (set(schema["$defs"]["accepted_result"]["properties"]) & forbidden_properties)
    assert not (set(schema["$defs"]["rejection_result"]["properties"]) & forbidden_properties)


def test_source_ingestion_sandbox_implementation_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION
    )
    assert golden["sandbox_status"] == SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS
    assert golden["direct_source_ingestion"] is False
    assert golden["source_to_intent_plain_data"] is False


def test_source_ingestion_sandbox_implementation_is_documented() -> None:
    schema_path = "schemas/source_ingestion_sandbox_implementation_report.v0.schema.json"
    example_path = "examples/source_ingestion_sandbox_implementation.py"
    golden_path = "tests/golden/frontend/source_ingestion_sandbox_implementation_report.json"
    doc_path = "docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md"
    rfc_path = "rfcs/0260-source-ingestion-sandbox-implementation.md"
    module_path = "src/tuc/frontend/source_ingestion_sandbox.py"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/BOUNDED_SOURCE_BUFFER_API.md"),
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