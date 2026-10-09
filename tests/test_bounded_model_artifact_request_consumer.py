"""Closed source-free invocation integration report."""

from __future__ import annotations

import json
from pathlib import Path

from integration.bounded_model_artifact_request import consumer

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/golden/bounded_model_artifact_request/report.json"
SCHEMA = ROOT / "schemas/bounded_model_artifact_request_integration.v0.schema.json"


def test_report_matches_golden_and_closed_schema() -> None:
    report = consumer.report()
    assert consumer._json(report).decode("ascii") == GOLDEN.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"]) == set(report)
    plans = report["plans"]
    assert isinstance(plans, list)
    assert [plan["name"] for plan in plans] == ["cpu", "cuda", "mixed"]
    plan_schema = schema["properties"]["plans"]["items"]
    assert plan_schema["additionalProperties"] is False
    for plan in plans:
        assert set(plan_schema["required"]) == set(plan_schema["properties"]) == set(plan)
        assert len(set(plan["request_digests"])) == 2
        assert plan["changed_request_digest"] not in plan["request_digests"]
        assert plan["changed_bundle_digest"] != plan["bundle_digest"]
    assert len({plan["bundle_digest"] for plan in plans}) == 3
    text = GOLDEN.read_text(encoding="utf-8")
    for forbidden in ("#include", "__global__", "void tuc_", "value_bits", "2.0", "-1.0"):
        assert forbidden not in text
