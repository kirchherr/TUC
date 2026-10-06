"""Deterministic external-consumer report tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from integration.bounded_model_artifacts import consumer

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "bounded_model_artifacts" / "report.json"
SCHEMA = ROOT / "schemas" / "bounded_model_artifacts_integration.v0.schema.json"


def test_consumer_report_matches_golden() -> None:
    assert consumer._json(consumer.report()).decode("ascii") == GOLDEN.read_text(encoding="utf-8")


def test_report_is_source_free_and_schema_is_closed() -> None:
    report = cast(dict[str, Any], json.loads(GOLDEN.read_text(encoding="utf-8")))
    schema = cast(dict[str, Any], json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(report)
    assert [item["name"] for item in report["plans"]] == ["cpu", "cuda", "mixed"]
    assert [item["backend_sequence"] for item in report["plans"]] == [
        ["cpu", "cpu", "cpu"],
        ["cuda", "cuda", "cuda"],
        ["cuda", "cpu", "cpu"],
    ]
    assert report["model_digest"] != report["changed_model_digest"]
    text = GOLDEN.read_text(encoding="utf-8")
    for forbidden in ("#include", "__global__", "void tuc_", "C:\\\\", "/home/", "2.0", "-1.0"):
        assert forbidden not in text
