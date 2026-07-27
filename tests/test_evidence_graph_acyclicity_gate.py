from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.evidence_graph_acyclicity_gate import (
    SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_EDGE_COUNT,
    SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_NODE_IDS,
    assert_evidence_graph_acyclicity_gate_report_contract,
    build_current_evidence_graph_acyclicity_gate_report,
    build_report,
)
from tuc.evidence_graph_acyclicity import (
    EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION,
    EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY,
    EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT,
    EVIDENCE_GRAPH_ACYCLICITY_GATE_ID,
    EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS,
    EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE,
    EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION,
    EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS,
    EvidenceGraphAcyclicityError,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    build_evidence_graph_acyclicity_report,
    evidence_graph_acyclicity_report_to_dict,
)

SCHEMA_PATH = Path("schemas/evidence_graph_acyclicity_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/evidence_graph_acyclicity_gate_report.json")
DOC_PATH = Path("docs/EVIDENCE_GRAPH_ACYCLICITY_GATE.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_current_evidence_graph_acyclicity_gate_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_evidence_graph_acyclicity_gate_passes() -> None:
    report = _cached_report()

    assert_evidence_graph_acyclicity_gate_report_contract(report)
    assert report["schema_version"] == EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION
    assert report["gate_contract"] == EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT
    assert report["gate_id"] == EVIDENCE_GRAPH_ACYCLICITY_GATE_ID
    assert report["gate_status"] == EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS
    assert report["graph_scope"] == EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE
    assert report["edge_direction"] == EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION
    assert report["evidence_policy"] == EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY
    assert report["node_count"] == len(SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_NODE_IDS)
    assert report["edge_count"] == SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_EDGE_COUNT
    assert report["cycle_count"] == 0
    assert report["detected_cycles"] == []
    assert report["source_free"] is True
    assert report["required_invariants"] == list(
        EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS
    )


def test_evidence_graph_acyclicity_gate_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_evidence_graph_acyclicity_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/evidence_graph_acyclicity_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"cycle_count": 0' in completed.stdout
    assert "real_triton_first_admissible_slice_plan" in completed.stdout
    assert "source_ingestion_maintainer_security_review_packet" in completed.stdout
    assert "source_ingestion_admission_gate" in completed.stdout
    assert "source_ingestion_preclaim_evidence_graph_acyclicity_gate" in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


def test_evidence_graph_acyclicity_gate_edges_are_dependency_ordered() -> None:
    report = _cached_report()
    order = report["topological_order"]
    assert isinstance(order, list)

    assert order.index("real_triton_first_admissible_slice_plan") < order.index(
        "source_ingestion_maintainer_security_review_packet"
    )
    assert order.index("source_ingestion_maintainer_security_review_packet") < (
        order.index("source_ingestion_maintainer_approval_artifact")
    )
    assert order.index("source_ingestion_maintainer_approval_artifact") < order.index(
        "source_ingestion_admission_gate"
    )
    assert order.index("source_ingestion_admission_gate") < order.index(
        "source_ingestion_preclaim_evidence_graph_acyclicity_gate"
    )
    assert order.index("source_ingestion_preclaim_evidence_graph_acyclicity_gate") < order.index(
        "research_scope_claim_gate"
    )


def test_evidence_graph_acyclicity_gate_rejects_cycle() -> None:
    digest = "sha256:" + "1" * 64
    nodes = (
        EvidenceGraphNode("Alpha", "alpha.contract.v0", "PASS"),
        EvidenceGraphNode("Beta", "beta.contract.v0", "PASS"),
    )
    edges = (
        EvidenceGraphEdge("Alpha", "Beta", digest),
        EvidenceGraphEdge("Beta", "Alpha", digest),
    )

    with pytest.raises(EvidenceGraphAcyclicityError, match="cycle"):
        build_evidence_graph_acyclicity_report(nodes, edges)


def test_evidence_graph_acyclicity_gate_rejects_missing_endpoint() -> None:
    digest = "sha256:" + "2" * 64
    nodes = (EvidenceGraphNode("Alpha", "alpha.contract.v0", "PASS"),)
    edges = (EvidenceGraphEdge("Alpha", "Beta", digest),)

    with pytest.raises(EvidenceGraphAcyclicityError, match="endpoint"):
        build_evidence_graph_acyclicity_report(nodes, edges)


def test_evidence_graph_acyclicity_gate_rejects_duplicate_node() -> None:
    nodes = (
        EvidenceGraphNode("Alpha", "alpha.contract.v0", "PASS"),
        EvidenceGraphNode("Alpha", "alpha.contract.v0", "PASS"),
    )

    with pytest.raises(EvidenceGraphAcyclicityError, match="duplicate node"):
        build_evidence_graph_acyclicity_report(nodes, ())


def test_evidence_graph_acyclicity_gate_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(EvidenceGraphAcyclicityError, match="top-level"):
        assert_evidence_graph_acyclicity_gate_report_contract(report)


def test_evidence_graph_acyclicity_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == EVIDENCE_GRAPH_ACYCLICITY_GATE_ID
    assert schema["properties"]["gate_status"]["const"] == (
        EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS
    )
    assert schema["properties"]["node_count"]["const"] == len(
        SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_NODE_IDS
    )
    assert schema["properties"]["edge_count"]["const"] == (
        SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_EDGE_COUNT
    )


def test_evidence_graph_acyclicity_gate_schema_fails_closed() -> None:
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


def test_evidence_graph_acyclicity_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION
    assert golden["gate_status"] == EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS
    assert golden["cycle_count"] == 0
    assert golden["detected_cycles"] == []
    assert golden["node_count"] == len(SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_NODE_IDS)
    assert golden["edge_count"] == SOURCE_INGESTION_EVIDENCE_GRAPH_ACYCLICITY_EDGE_COUNT


def test_evidence_graph_acyclicity_report_to_dict_rejects_unbuilt_graph() -> None:
    report = build_evidence_graph_acyclicity_report(
        (EvidenceGraphNode("Alpha", "alpha.contract.v0", "PASS"),),
        (),
    )
    payload = evidence_graph_acyclicity_report_to_dict(report)

    assert payload["cycle_count"] == 0
    assert payload["topological_order"] == ["Alpha"]


def test_evidence_graph_acyclicity_gate_is_documented_and_ci_bound() -> None:
    schema_path = "schemas/evidence_graph_acyclicity_gate_report.v0.schema.json"
    example_path = "examples/evidence_graph_acyclicity_gate.py"
    golden_path = "tests/golden/frontend/evidence_graph_acyclicity_gate_report.json"
    module_path = "src/tuc/evidence_graph_acyclicity.py"
    doc_path = "docs/EVIDENCE_GRAPH_ACYCLICITY_GATE.md"
    rfc_path = "rfcs/0270-evidence-graph-acyclicity-gate.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path(".github/PULL_REQUEST_TEMPLATE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        if path not in {
            Path(".github/workflows/ci.yml"),
            Path(".github/PULL_REQUEST_TEMPLATE.md"),
        }:
            assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert doc_path in text or path == DOC_PATH
            assert rfc_path in text or path == Path(rfc_path) or path.name in {
                "README.md",
                "ROADMAP.md",
            }


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
