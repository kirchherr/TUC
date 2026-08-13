from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_capability_coverage import (
    build_current_backend_capability_coverage_report,
)
from tuc import (
    BACKEND_CAPABILITY_COVERAGE_CONTRACT,
    BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION,
    MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendCapabilityCoverageError,
    BackendCapabilityCoverageReport,
    BackendCapabilityCoverageRow,
    LinearAlgebraSimulatorBackend,
    OperationKind,
    assert_backend_capability_coverage,
    backend_capability_coverage_report_to_dict,
    build_backend_capability_coverage_report,
    dump_backend_capability_coverage_report,
)
from tuc.backends import BackendCapability

SCHEMA_PATH = Path("schemas/backend_capability_coverage_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/backend_capability_coverage/current_report.json")


def test_current_backend_capability_coverage_is_complete() -> None:
    report = build_current_backend_capability_coverage_report()
    payload = backend_capability_coverage_report_to_dict(report)

    assert report.complete
    assert payload["coverage_status"] == "complete"
    assert payload["backend_names"] == ["linear-sim", "systolic-sim", "vector-sim"]
    assert payload["required_operation_kinds"] == [
        "matmul",
        "elementwise",
        "reduction",
        "softmax",
    ]

    rows = {row["operation_kind"]: row for row in payload["rows"]}  # type: ignore[index]
    assert rows["matmul"]["accepting_backends"] == [
        "linear-sim",
        "systolic-sim",
    ]
    assert rows["softmax"]["accepting_backends"] == ["vector-sim"]
    assert rows["elementwise"]["preferred_backends"] == ["vector-sim"]
    assert rows["reduction"]["accepting_backends"] == ["linear-sim", "vector-sim"]
    assert payload["issues"] == []


def test_backend_capability_coverage_detects_missing_operation_family() -> None:
    report = build_backend_capability_coverage_report(
        (LinearAlgebraSimulatorBackend().capability,),
    )
    payload = backend_capability_coverage_report_to_dict(report)

    assert not report.complete
    assert payload["coverage_status"] == "partial"
    assert payload["issues"] == [
        {
            "issue_code": "operation_kind_not_covered",
            "operation_kind": "elementwise",
        },
        {
            "issue_code": "operation_kind_not_covered",
            "operation_kind": "softmax",
        },
    ]


def test_assert_backend_capability_coverage_raises_on_missing_coverage() -> None:
    report = build_backend_capability_coverage_report(
        (LinearAlgebraSimulatorBackend().capability,),
    )

    with pytest.raises(BackendCapabilityCoverageError, match="softmax"):
        assert_backend_capability_coverage(report)


def test_backend_capability_coverage_rejects_duplicate_backend_names() -> None:
    capability = LinearAlgebraSimulatorBackend().capability

    with pytest.raises(ValueError, match="backend names must be unique"):
        build_backend_capability_coverage_report((capability, capability))


def test_backend_capability_coverage_rejects_hand_written_issues() -> None:
    report = build_backend_capability_coverage_report(
        (LinearAlgebraSimulatorBackend().capability,),
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendCapabilityCoverageReport(
            backend_names=report.backend_names,
            required_operation_kinds=report.required_operation_kinds,
            rows=report.rows,
            issues=(),
        )


def test_backend_capability_coverage_row_validates_missing_rows() -> None:
    with pytest.raises(ValueError, match="missing operation"):
        BackendCapabilityCoverageRow(
            operation_kind=OperationKind.MATMUL,
            accepting_backends=("linear-sim",),
            preferred_backends=(),
            memory_domains=(),
            produced_layouts=(),
            status="missing",
        )


def test_backend_capability_coverage_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        build_backend_capability_coverage_report(
            (
                BackendCapability(
                    name="plugin_entrypoint",
                    supported_ops=frozenset({OperationKind.MATMUL}),
                ),
            )
        )


def test_backend_capability_coverage_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_capability_coverage.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["complete"] is True
    assert loaded["backend_count"] == 3


def test_backend_capability_coverage_dump_matches_golden() -> None:
    report = build_current_backend_capability_coverage_report()

    assert dump_backend_capability_coverage_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_backend_capability_coverage_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_capability_coverage_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["coverage_contract"]["const"] == (
        BACKEND_CAPABILITY_COVERAGE_CONTRACT
    )
    assert schema["properties"]["backend_count"]["maximum"] == (
        MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_backend_capability_coverage_schema_fails_closed() -> None:
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
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["coverage_row"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_capability_coverage_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION
    assert golden["coverage_contract"] == BACKEND_CAPABILITY_COVERAGE_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["backend_count"] == len(golden["backend_names"]) == 3
    assert golden["operation_count"] == len(golden["rows"]) == 4
    assert golden["complete"] is True
    assert golden["issues"] == []


def test_backend_capability_coverage_schema_is_referenced() -> None:
    schema_path = "schemas/backend_capability_coverage_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_CAPABILITY_COVERAGE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0202-backend-capability-coverage-matrix.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def test_backend_capability_coverage_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_capability_coverage_report_to_dict(object())  # type: ignore[arg-type]


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
