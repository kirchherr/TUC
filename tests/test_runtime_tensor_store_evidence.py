from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TENSOR_STORE_CONTRACT,
    RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT,
    RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_VALUE_EXTERNAL_INPUT_BACKEND,
    RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT,
    RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN,
    RUNTIME_VALUE_RECORD_CONTRACT,
    LayoutKind,
    MemoryDomainKind,
    RuntimeTensorStoreEvidenceIssue,
    RuntimeTensorStoreEvidenceReport,
    RuntimeTensorValueEvidence,
    assert_runtime_tensor_store_evidence,
    dump_runtime_tensor_store_evidence_report,
    runtime_tensor_store_evidence_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_TENSOR_STORE_EVIDENCE_RECORDS

GOLDEN_PATH = Path(
    "tests/golden/runtime_tensor_store_evidence/proof_of_execution.json"
)
SCHEMA_PATH = Path("schemas/runtime_tensor_store_evidence_report.v0.schema.json")


def test_runtime_tensor_store_evidence_passes_for_execution_proof() -> None:
    report = build_tensor_store_evidence_report()

    assert report.evidence_contract == RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT
    assert report.passed
    assert report.issues == ()
    assert len(report.expected_records) == 5
    assert len(report.records) == 5
    assert tuple(record.tensor_name for record in report.records) == (
        "lhs",
        "rhs",
        "projection",
        "row_sum",
        "activated",
    )
    assert all(record.readonly for record in report.records)
    assert {record.raw_value_status for record in report.records} == {
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    }
    assert tuple(runtime_tensor_store_evidence_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "evidence_contract",
        "expected_record_count",
        "expected_records",
        "graph_name",
        "issues",
        "passed",
        "raw_value_policy",
        "record_count",
        "record_metadata_digest",
        "records",
        "schema_version",
        "store_contract",
        "value_record_contract",
    )
    assert report.records[0].producer_kind == "external_input"
    assert report.records[0].producer_id == "lhs"
    assert report.records[0].planned_backend == RUNTIME_VALUE_EXTERNAL_INPUT_BACKEND
    assert report.records[0].planned_memory_domain is MemoryDomainKind.HOST_RAM
    assert report.records[0].planned_layout is LayoutKind.ROW_MAJOR
    assert report.records[0].placement_source == (
        RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT
    )
    assert report.records[2].planned_backend == "linear-sim"
    assert report.records[2].placement_source == (
        RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN
    )
    assert report.records[-1].producer_kind == "operation"
    assert report.records[-1].producer_id == "activation"


def test_runtime_tensor_store_evidence_dump_matches_golden() -> None:
    assert dump_runtime_tensor_store_evidence_report(
        build_tensor_store_evidence_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_tensor_store_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_tensor_store_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_tensor_store_evidence.data_only.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout


def test_runtime_tensor_store_evidence_assertion_returns_report() -> None:
    assert assert_runtime_tensor_store_evidence(
        build_tensor_store_evidence_report()
    ).passed


def test_runtime_tensor_store_evidence_issues_must_be_derived() -> None:
    report = build_tensor_store_evidence_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeTensorStoreEvidenceReport(
            graph_name=report.graph_name,
            expected_records=report.expected_records,
            records=report.records[:-1],
            issues=(),
        )


def test_runtime_tensor_store_evidence_records_mutable_values_as_issue() -> None:
    report = build_tensor_store_evidence_report()
    record = report.records[0]
    mutable_record = RuntimeTensorValueEvidence(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        producer_kind=record.producer_kind,
        producer_id=record.producer_id,
        planned_backend=record.planned_backend,
        planned_memory_domain=record.planned_memory_domain,
        planned_layout=record.planned_layout,
        placement_source=record.placement_source,
        readonly=False,
    )
    failing = RuntimeTensorStoreEvidenceReport(
        graph_name=report.graph_name,
        expected_records=report.expected_records[:1],
        records=(mutable_record,),
        issues=(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name=mutable_record.tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "record_value_mutable"


def test_runtime_tensor_store_evidence_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimeTensorValueEvidence(
            tensor_name="value",
            shape=(2,),
            dtype="float64",
            value_role="input",
            producer_kind="external_input",
            producer_id="value",
            planned_backend=RUNTIME_VALUE_EXTERNAL_INPUT_BACKEND,
            planned_memory_domain=MemoryDomainKind.HOST_RAM,
            planned_layout=LayoutKind.ROW_MAJOR,
            placement_source=RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT,
            readonly=True,
            raw_value_status="included",
        )


def test_runtime_tensor_store_evidence_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeTensorValueEvidence(
            tensor_name="python_source",
            shape=(2,),
            dtype="float64",
            value_role="input",
            producer_kind="external_input",
            producer_id="python_source",
            planned_backend=RUNTIME_VALUE_EXTERNAL_INPUT_BACKEND,
            planned_memory_domain=MemoryDomainKind.HOST_RAM,
            planned_layout=LayoutKind.ROW_MAJOR,
            placement_source=RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT,
            readonly=True,
        )


def test_runtime_tensor_store_evidence_records_provenance_mismatch_as_issue() -> None:
    report = build_tensor_store_evidence_report()
    record = report.records[-1]
    bad_record = RuntimeTensorValueEvidence(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        producer_kind=record.producer_kind,
        producer_id="other_operation",
        planned_backend=record.planned_backend,
        planned_memory_domain=record.planned_memory_domain,
        planned_layout=record.planned_layout,
        placement_source=record.placement_source,
        readonly=True,
    )
    failing = RuntimeTensorStoreEvidenceReport(
        graph_name=report.graph_name,
        expected_records=report.expected_records[-1:],
        records=(bad_record,),
        issues=(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name=bad_record.tensor_name,
                issue_code="producer_id_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "producer_id_mismatch"


def test_runtime_tensor_store_evidence_records_placement_mismatch_as_issue() -> None:
    report = build_tensor_store_evidence_report()
    record = report.records[2]
    bad_record = RuntimeTensorValueEvidence(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        producer_kind=record.producer_kind,
        producer_id=record.producer_id,
        planned_backend="reference-cpu",
        planned_memory_domain=record.planned_memory_domain,
        planned_layout=record.planned_layout,
        placement_source=record.placement_source,
        readonly=True,
    )
    failing = RuntimeTensorStoreEvidenceReport(
        graph_name=report.graph_name,
        expected_records=report.expected_records[2:3],
        records=(bad_record,),
        issues=(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name=bad_record.tensor_name,
                issue_code="planned_backend_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "planned_backend_mismatch"


def test_runtime_tensor_store_evidence_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_tensor_store_evidence_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT
    )
    assert schema["properties"]["store_contract"]["const"] == (
        RUNTIME_TENSOR_STORE_CONTRACT
    )
    assert schema["properties"]["value_record_contract"]["const"] == (
        RUNTIME_VALUE_RECORD_CONTRACT
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["records"]["maxItems"] == (
        MAX_RUNTIME_TENSOR_STORE_EVIDENCE_RECORDS
    )
    assert schema["$defs"]["producer_kind"]["enum"] == [
        "external_input",
        "operation",
    ]
    assert schema["$defs"]["placement_source"]["enum"] == [
        RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT,
        RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN,
    ]
    assert schema["$defs"]["layout"]["enum"] == ["blocked", "row_major"]
    assert schema["$defs"]["memory_domain"]["enum"] == [
        "analog_weight_bank",
        "device_sram",
        "gpu_hbm",
        "host_ram",
    ]
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_tensor_store_evidence_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["expected_record"]["properties"]
        assert forbidden not in schema["$defs"]["value_record"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_tensor_store_evidence_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS
    assert golden["evidence_contract"] == RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT
    assert golden["store_contract"] == RUNTIME_TENSOR_STORE_CONTRACT
    assert golden["value_record_contract"] == RUNTIME_VALUE_RECORD_CONTRACT
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["expected_record_count"] == len(golden["expected_records"]) == 5
    assert golden["record_count"] == len(golden["records"]) == 5
    assert all(record["readonly"] is True for record in golden["records"])
    assert golden["records"][0]["producer_kind"] == "external_input"
    assert golden["records"][0]["producer_id"] == "lhs"
    assert golden["records"][0]["planned_backend"] == RUNTIME_VALUE_EXTERNAL_INPUT_BACKEND
    assert golden["records"][0]["planned_memory_domain"] == "host_ram"
    assert golden["records"][0]["planned_layout"] == "row_major"
    assert golden["records"][0]["placement_source"] == (
        RUNTIME_VALUE_PLACEMENT_SOURCE_EXTERNAL_INPUT
    )
    assert golden["records"][2]["planned_backend"] == "linear-sim"
    assert golden["records"][2]["placement_source"] == (
        RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN
    )
    assert golden["records"][-1]["producer_kind"] == "operation"
    assert golden["records"][-1]["producer_id"] == "activation"


def test_runtime_tensor_store_evidence_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_tensor_store_evidence_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_TENSOR_STORE_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0106-runtime-tensor-store-evidence.md"),
        Path("rfcs/0108-runtime-value-provenance.md"),
        Path("rfcs/0134-runtime-value-placement-metadata.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


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
