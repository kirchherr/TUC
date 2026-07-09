from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_to_intent_plain_data_output_golden_for_admitted_slice import (
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION,
    SourceToIntentAdmittedSliceGoldenReportError,
    assert_source_to_intent_admitted_slice_golden_report_contract,
    build_admitted_slice_parse_results,
    build_report,
    build_source_intent_plain_data_output_golden,
    build_source_to_intent_plain_data_output_golden_report,
)
from tuc.frontend.source_intent import SOURCE_INTENT_IR_CONTRACT
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)
from tuc.frontend.source_to_intent_admitted_slice_golden import (
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS,
    SourceToIntentAdmittedSliceGoldenError,
    build_source_to_intent_admitted_slice_golden_report,
    source_intent_plain_data_digest,
    source_to_intent_plain_data_golden_case_from_parse_result,
)

SCHEMA_PATH = Path(
    "schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json"
)
REPORT_GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json"
)
SOURCE_INTENT_GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json"
)
DOC_PATH = Path("docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_to_intent_plain_data_output_golden_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


@lru_cache(maxsize=1)
def _cached_source_intent_text() -> str:
    return build_source_intent_plain_data_output_golden()


def test_source_to_intent_plain_data_output_golden_report_passes() -> None:
    report = _cached_report()

    assert_source_to_intent_admitted_slice_golden_report_contract(report)
    assert report["schema_version"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION
    )
    assert report["evidence_id"] == SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID
    assert report["golden_contract"] == SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT
    assert report["golden_status"] == SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS
    assert report["source_intent_schema_version"] == SOURCE_INTENT_SCHEMA_VERSION
    assert report["source_intent_contract"] == SOURCE_INTENT_IR_CONTRACT
    assert report["case_count"] == 2
    assert report["source_to_intent_plain_data_output_golden"] is True
    assert report["operation_family_coverage_complete"] is True
    assert report["operation_family_coverage"] == list(
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES
    )
    assert report["direct_source_ingestion"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["issues"] == []


def test_source_intent_plain_data_golden_validates_and_matches_digests() -> None:
    report = _cached_report()
    golden = json.loads(_cached_source_intent_text())

    assert golden["plain_data_schema_version"] == report["plain_data_schema_version"]
    assert golden["case_count"] == report["case_count"]
    report_digests = {
        str(case["case_id"]): str(case["plain_data_digest"])
        for case in report["cases"]
    }
    for case in golden["cases"]:
        plain_data = case["source_intent_plain_data"]
        module = source_intent_from_mapping(plain_data)
        assert module.contract == SOURCE_INTENT_IR_CONTRACT
        assert case["plain_data_digest"] == source_intent_plain_data_digest(plain_data)
        assert report_digests[str(case["case_id"])] == case["plain_data_digest"]


def test_source_to_intent_plain_data_output_golden_dump_matches_golden() -> None:
    assert _cached_text() == REPORT_GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_plain_data_output_golden_payload_matches_golden() -> None:
    assert _cached_source_intent_text() == SOURCE_INTENT_GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_source_to_intent_plain_data_output_golden_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == REPORT_GOLDEN_PATH.read_text(encoding="utf-8")
    assert "source_to_intent_plain_data_output_golden" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_source_to_intent_plain_data_output_golden_source_intent_mode_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py",
            "--source-intent",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == SOURCE_INTENT_GOLDEN_PATH.read_text(encoding="utf-8")
    assert "source_intent_plain_data" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_text" not in completed.stdout


def test_source_to_intent_plain_data_output_golden_rejects_incomplete_coverage() -> None:
    result = build_admitted_slice_parse_results()[0]
    case = source_to_intent_plain_data_golden_case_from_parse_result(
        result,
        case_id="admitted_slice_matmul_elementwise_plain_data_golden",
    )

    with pytest.raises(
        SourceToIntentAdmittedSliceGoldenError,
        match="operation family coverage incomplete",
    ):
        build_source_to_intent_admitted_slice_golden_report((case,))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("golden_status", "draft", "golden_status"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_to_compute_graph", True, "source_to_compute_graph"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("source_to_runtime_plan", True, "source_to_runtime_plan"),
        ("source_to_intent_plain_data_output_golden", False, "plain_data_output"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_to_intent_plain_data_output_golden_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(SourceToIntentAdmittedSliceGoldenReportError, match=match):
        assert_source_to_intent_admitted_slice_golden_report_contract(report)


def test_source_to_intent_plain_data_output_golden_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(
        SourceToIntentAdmittedSliceGoldenReportError,
        match="digest drift",
    ):
        assert_source_to_intent_admitted_slice_golden_report_contract(report)


def test_source_to_intent_plain_data_output_golden_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(
        SourceToIntentAdmittedSliceGoldenReportError,
        match="top-level keys drift",
    ):
        assert_source_to_intent_admitted_slice_golden_report_contract(report)


def test_source_to_intent_plain_data_output_golden_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_id"]["const"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID
    )
    assert schema["properties"]["golden_contract"]["const"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT
    )
    assert schema["properties"]["golden_status"]["const"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS
    )
    assert schema["properties"]["source_intent_schema_version"]["const"] == (
        SOURCE_INTENT_SCHEMA_VERSION
    )
    assert schema["properties"]["source_intent_contract"]["const"] == (
        SOURCE_INTENT_IR_CONTRACT
    )
    assert [
        item["const"]
        for item in schema["properties"]["operation_family_coverage"]["prefixItems"]
    ] == list(SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES)


def test_source_to_intent_plain_data_output_golden_schema_fails_closed() -> None:
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


def test_source_to_intent_plain_data_output_golden_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(REPORT_GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION
    )
    assert golden["evidence_id"] == SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID
    assert golden["case_count"] == 2
    assert golden["operation_family_coverage_complete"] is True


def test_source_to_intent_plain_data_output_golden_is_documented() -> None:
    schema_path = (
        "schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json"
    )
    example_path = (
        "examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py"
    )
    report_golden_path = (
        "tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json"
    )
    source_intent_golden_path = (
        "tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json"
    )
    module_path = "src/tuc/frontend/source_to_intent_admitted_slice_golden.py"
    doc_path = "docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md"
    rfc_path = (
        "rfcs/0263-source-to-intent-plain-data-output-golden-for-admitted-slice.md"
    )

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
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert report_golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert source_intent_golden_path in text or path.name in {
            "README.md",
            "ROADMAP.md",
        }
        assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
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
