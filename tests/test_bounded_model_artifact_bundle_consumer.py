"""Deterministic external-consumer bundle report tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from integration.bounded_model_artifact_bundle import consumer

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "bounded_model_artifact_bundle" / "report.json"
SCHEMA = ROOT / "schemas" / "bounded_model_artifact_bundle_integration.v0.schema.json"


def test_consumer_report_matches_golden() -> None:
    assert consumer._json(consumer.report()).decode("ascii") == GOLDEN.read_text(encoding="utf-8")


def test_report_is_source_free_and_schema_is_closed() -> None:
    report = cast(dict[str, Any], json.loads(GOLDEN.read_text(encoding="utf-8")))
    schema = cast(dict[str, Any], json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)
    assert [item["name"] for item in report["plans"]] == ["cpu", "cuda", "mixed"]
    plan_schema = schema["properties"]["plans"]["items"]
    assert plan_schema["additionalProperties"] is False
    assert all(set(plan_schema["required"]) == set(item) for item in report["plans"])
    assert all(set(plan_schema["properties"]) == set(item) for item in report["plans"])
    assert all(item["bundle_digest"] != item["changed_bundle_digest"] for item in report["plans"])
    assert all(
        item["model_compilation_digest"] != item["changed_model_compilation_digest"]
        for item in report["plans"]
    )
    text = GOLDEN.read_text(encoding="utf-8")
    for forbidden in ("#include", "__global__", "void tuc_", "C:\\\\", "/home/", "2.0", "-1.0"):
        assert forbidden not in text
