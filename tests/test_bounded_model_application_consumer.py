"""Deterministic, closed protocol integration evidence."""

import json
from pathlib import Path

from integration.bounded_model_application import consumer

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/golden/bounded_model_application/report.json"
SCHEMA = ROOT / "schemas/bounded_model_application_integration.v0.schema.json"


def test_golden_report_and_closed_schema():
    report = consumer.report()
    assert consumer._json(report).decode("ascii") == GOLDEN.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(schema["required"]) == set(report)
    calls = report["calls"]
    inner = schema["properties"]["calls"]["items"]
    assert inner["additionalProperties"] is False
    assert all(set(inner["required"]) == set(inner["properties"]) == set(call) for call in calls)
    assert [call["name"] for call in calls] == ["base", "variable", "parameter"]
    assert len({call["program_digest"] for call in calls}) == 1
    assert len({call["bundle_digest"] for call in calls}) == 2
    assert len({call["request_digest"] for call in calls}) == 3
    assert len({call["protocol_request_digest"] for call in calls}) == 3
    assert len({call["result_digest"] for call in calls}) == 3
    assert report["synthetic_responses"] is True
    assert report["native_execution_observed"] is False
    assert report["rejected_targets"] == ["cuda", "mixed"]
    for forbidden in ("#include", "__global__", "void tuc_", "value_bits"):
        assert forbidden not in GOLDEN.read_text(encoding="utf-8")
