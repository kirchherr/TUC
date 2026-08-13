"""Emit the pre-claim source-ingestion evidence graph acyclicity gate."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping

from examples.real_triton_first_slice_plan import (
    assert_real_triton_first_slice_plan_report_contract,
)
from examples.real_triton_first_slice_plan import (
    build_report as build_real_triton_first_slice_plan_report,
)
from examples.source_ingestion_admission_gate import (
    assert_source_ingestion_admission_gate_report_contract,
)
from examples.source_ingestion_admission_gate import (
    build_report as build_source_ingestion_admission_gate_report,
)
from examples.source_ingestion_maintainer_approval_artifact import (
    assert_source_ingestion_maintainer_approval_artifact_report_contract,
)
from examples.source_ingestion_maintainer_approval_artifact import (
    build_report as build_source_ingestion_maintainer_approval_report,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    assert_source_ingestion_maintainer_security_review_packet_contract,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    build_report as build_source_ingestion_maintainer_review_report,
)
from tuc.evidence_graph_acyclicity import (
    EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION,
    EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY,
    EvidenceGraphAcyclicityError,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    build_evidence_graph_acyclicity_report,
    evidence_graph_acyclicity_report_to_dict,
)

SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_preclaim_acyclicity_gate_report.v0"
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT = (
    "source_ingestion_preclaim_acyclicity_gate.data_only.v0"
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID = (
    "source_ingestion_preclaim_evidence_graph_acyclicity_gate"
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_STATUS = "PASS"
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GRAPH_SCOPE = (
    "source_ingestion_first_slice_to_admission_gate"
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REQUIRED_INVARIANTS = (
    "edge_endpoints_declared",
    "graph_is_acyclic",
    "dependency_first_topological_order_emitted",
    "digest_only_source_free_edges",
    "research_scope_claim_not_in_preclaim_graph",
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS = (
    "real_triton_integration_admission_gate",
    "real_triton_surface_gate_completion",
    "source_ingestion_quarantine_gate",
    "admitting_source_ingestion_rfc",
    "bounded_source_buffer_api",
    "source_ingestion_sandbox_implementation",
    "parser_fuzz_negative_corpus_for_admitting_slice",
    "source_free_diagnostics_admission_tests",
    "source_to_intent_plain_data_output_golden_for_admitted_slice",
    "ci_replay_for_admitted_slice",
    "source_ingestion_approval_criteria",
    "source_to_intent_research_source_runtime_smoke",
    "source_to_intent_research_kernel_ingress_proof_bundle",
    "real_triton_first_admissible_slice_plan",
    "source_ingestion_maintainer_security_review_packet",
    "source_ingestion_maintainer_approval_artifact",
    "source_ingestion_admission_gate",
)
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_EDGE_COUNT = 25
SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REPORT_PATH = (
    "tests/golden/frontend/source_ingestion_preclaim_acyclicity_gate_report.json"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "cycle_count",
        "detected_cycles",
        "edge_count",
        "edge_direction",
        "edges",
        "evidence_policy",
        "gate_contract",
        "gate_id",
        "gate_status",
        "graph_scope",
        "node_count",
        "nodes",
        "required_invariants",
        "schema_version",
        "source_free",
        "topological_order",
    }
)
_NODE_KEYS = frozenset(
    {"contract", "evidence_id", "node_kind", "source_free", "status"}
)
_EDGE_KEYS = frozenset(
    {
        "bound_digest",
        "edge_kind",
        "from_evidence_id",
        "source_free",
        "to_evidence_id",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    "import os",
    "import triton",
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"research_scope_claim_gate"',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    "tl.dot",
    "tl.store",
)


def build_current_source_ingestion_preclaim_acyclicity_gate_report() -> (
    dict[str, object]
):
    """Build the source-ingestion DAG proof before research-scope binding."""

    nodes, edges = _build_graph(_build_payloads())
    report = build_evidence_graph_acyclicity_report(nodes, edges)
    payload = evidence_graph_acyclicity_report_to_dict(report)
    payload.update(
        {
            "gate_contract": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
            "gate_id": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID,
            "gate_status": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_STATUS,
            "graph_scope": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GRAPH_SCOPE,
            "required_invariants": list(
                SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REQUIRED_INVARIANTS
            ),
            "schema_version": (
                SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REPORT_SCHEMA_VERSION
            ),
        }
    )
    assert_source_ingestion_preclaim_acyclicity_gate_report_contract(payload)
    return payload


def build_report() -> str:
    """Return stable JSON evidence for the pre-claim acyclicity gate."""

    payload = build_current_source_ingestion_preclaim_acyclicity_gate_report()
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    return f"{text}\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_preclaim_acyclicity_gate_report_contract(
    report: object,
) -> None:
    """Fail closed unless the pre-claim acyclicity report matches v0."""

    if not isinstance(report, Mapping):
        raise EvidenceGraphAcyclicityError("preclaim acyclicity report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise EvidenceGraphAcyclicityError("preclaim acyclicity top-level keys drift")

    expected = {
        "cycle_count": 0,
        "edge_count": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_EDGE_COUNT,
        "edge_direction": EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION,
        "evidence_policy": EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY,
        "gate_contract": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
        "gate_id": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID,
        "gate_status": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_STATUS,
        "graph_scope": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GRAPH_SCOPE,
        "node_count": len(SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS),
        "schema_version": SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REPORT_SCHEMA_VERSION,
        "source_free": True,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise EvidenceGraphAcyclicityError(f"preclaim acyclicity {key} drift")

    if report.get("detected_cycles") != []:
        raise EvidenceGraphAcyclicityError("preclaim acyclicity cycles must be empty")
    _assert_string_sequence(
        report.get("required_invariants"),
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_nodes(report.get("nodes"))
    _assert_edges(report.get("edges"))
    _assert_topological_order(report.get("topological_order"))
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_payloads() -> dict[str, Mapping[str, object]]:
    texts = {
        "first_slice": build_real_triton_first_slice_plan_report(),
        "review_packet": build_source_ingestion_maintainer_review_report(),
        "approval_artifact": build_source_ingestion_maintainer_approval_report(),
        "admission_gate": build_source_ingestion_admission_gate_report(),
    }
    payloads = {key: _json_payload(text, key) for key, text in texts.items()}
    assert_real_triton_first_slice_plan_report_contract(payloads["first_slice"])
    assert_source_ingestion_maintainer_security_review_packet_contract(
        payloads["review_packet"]
    )
    assert_source_ingestion_maintainer_approval_artifact_report_contract(
        payloads["approval_artifact"]
    )
    assert_source_ingestion_admission_gate_report_contract(payloads["admission_gate"])
    return payloads


def _build_graph(
    payloads: Mapping[str, Mapping[str, object]],
) -> tuple[tuple[EvidenceGraphNode, ...], tuple[EvidenceGraphEdge, ...]]:
    nodes: dict[str, EvidenceGraphNode] = {}
    edges: list[EvidenceGraphEdge] = []

    first_slice = payloads["first_slice"]
    review_packet = payloads["review_packet"]
    approval_artifact = payloads["approval_artifact"]
    admission_gate = payloads["admission_gate"]

    first_slice_id = _add_report_node(
        nodes,
        first_slice,
        "plan_id",
        "plan_contract",
        "plan_status",
    )
    review_packet_id = _add_report_node(
        nodes,
        review_packet,
        "evidence_id",
        "contract",
        "status",
    )
    approval_artifact_id = _add_report_node(
        nodes,
        approval_artifact,
        "evidence_id",
        "contract",
        "status",
    )
    admission_gate_id = _add_report_node(
        nodes,
        admission_gate,
        "gate_id",
        "gate_contract",
        "gate_status",
    )

    _extend_edges_from_items(nodes, edges, first_slice_id, first_slice["evidence"])
    _extend_edges_from_items(nodes, edges, review_packet_id, review_packet["review_evidence"])
    _append_edge_from_item(
        nodes,
        edges,
        approval_artifact_id,
        approval_artifact["maintainer_review_packet"],
    )
    _append_edge_from_item(
        nodes,
        edges,
        admission_gate_id,
        admission_gate["maintainer_review_packet"],
    )
    _append_edge_from_item(
        nodes,
        edges,
        admission_gate_id,
        admission_gate["maintainer_approval_artifact"],
    )

    ordered_nodes = tuple(
        nodes[evidence_id]
        for evidence_id in SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS
    )
    return ordered_nodes, tuple(edges)


def _add_report_node(
    nodes: dict[str, EvidenceGraphNode],
    payload: Mapping[str, object],
    evidence_id_key: str,
    contract_key: str,
    status_key: str,
) -> str:
    evidence_id = _required_text(payload, evidence_id_key)
    contract = _required_text(payload, contract_key)
    status = _required_text(payload, status_key)
    _add_or_confirm_node(nodes, evidence_id, contract, status, "evidence_report")
    return evidence_id


def _append_edge_from_item(
    nodes: dict[str, EvidenceGraphNode],
    edges: list[EvidenceGraphEdge],
    from_evidence_id: str,
    item: object,
) -> None:
    if not isinstance(item, Mapping):
        raise EvidenceGraphAcyclicityError("preclaim edge item must be object")
    evidence_id = _required_text(item, "evidence_id")
    contract = _required_text(item, "contract")
    status = _required_text(item, "status")
    digest = _required_text(item, "digest")
    if item.get("source_free") is not True:
        raise EvidenceGraphAcyclicityError("preclaim edge item must be source-free")
    _add_or_confirm_node(nodes, evidence_id, contract, status, "leaf_evidence")
    edges.append(
        EvidenceGraphEdge(
            from_evidence_id=from_evidence_id,
            to_evidence_id=evidence_id,
            bound_digest=digest,
        )
    )


def _extend_edges_from_items(
    nodes: dict[str, EvidenceGraphNode],
    edges: list[EvidenceGraphEdge],
    from_evidence_id: str,
    items: object,
) -> None:
    if not isinstance(items, Iterable) or isinstance(items, (str, bytes)):
        raise EvidenceGraphAcyclicityError("preclaim edge items must be iterable")
    for item in items:
        _append_edge_from_item(nodes, edges, from_evidence_id, item)


def _add_or_confirm_node(
    nodes: dict[str, EvidenceGraphNode],
    evidence_id: str,
    contract: str,
    status: str,
    node_kind: str,
) -> None:
    existing = nodes.get(evidence_id)
    if existing is not None:
        if existing.contract != contract or existing.status != status:
            raise EvidenceGraphAcyclicityError("preclaim node contract drift")
        return
    nodes[evidence_id] = EvidenceGraphNode(
        evidence_id=evidence_id,
        contract=contract,
        status=status,
        node_kind=node_kind,
    )


def _assert_nodes(value: object) -> None:
    if not isinstance(value, list):
        raise EvidenceGraphAcyclicityError("preclaim nodes must be list")
    if [item.get("evidence_id") for item in value if isinstance(item, Mapping)] != list(
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS
    ):
        raise EvidenceGraphAcyclicityError("preclaim node IDs drift")
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _NODE_KEYS:
            raise EvidenceGraphAcyclicityError("preclaim node keys drift")
        if item.get("evidence_id") == "research_scope_claim_gate":
            raise EvidenceGraphAcyclicityError("research scope cannot be preclaim node")
        for key in ("contract", "evidence_id", "node_kind", "status"):
            _validate_text(item.get(key), f"node {key}")
        if item.get("source_free") is not True:
            raise EvidenceGraphAcyclicityError("preclaim node source flag drift")


def _assert_edges(value: object) -> None:
    if not isinstance(value, list):
        raise EvidenceGraphAcyclicityError("preclaim edges must be list")
    if len(value) != SOURCE_INGESTION_PRECLAIM_ACYCLICITY_EDGE_COUNT:
        raise EvidenceGraphAcyclicityError("preclaim edge count drift")
    node_ids = set(SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS)
    edge_pairs = set()
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _EDGE_KEYS:
            raise EvidenceGraphAcyclicityError("preclaim edge keys drift")
        from_id = _required_text(item, "from_evidence_id")
        to_id = _required_text(item, "to_evidence_id")
        _validate_text(item.get("edge_kind"), "edge kind")
        digest = item.get("bound_digest")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise EvidenceGraphAcyclicityError("preclaim edge digest invalid")
        if item.get("source_free") is not True:
            raise EvidenceGraphAcyclicityError("preclaim edge source flag drift")
        if from_id not in node_ids or to_id not in node_ids:
            raise EvidenceGraphAcyclicityError("preclaim edge endpoint drift")
        if (from_id, to_id) in edge_pairs:
            raise EvidenceGraphAcyclicityError("preclaim duplicate edge")
        edge_pairs.add((from_id, to_id))


def _assert_topological_order(value: object) -> None:
    if not isinstance(value, list):
        raise EvidenceGraphAcyclicityError("preclaim topological order invalid")
    if set(value) != set(SOURCE_INGESTION_PRECLAIM_ACYCLICITY_NODE_IDS):
        raise EvidenceGraphAcyclicityError("preclaim topological nodes drift")
    if "research_scope_claim_gate" in value:
        raise EvidenceGraphAcyclicityError("research scope cannot appear preclaim")
    if value.index("real_triton_first_admissible_slice_plan") > value.index(
        "source_ingestion_maintainer_security_review_packet"
    ):
        raise EvidenceGraphAcyclicityError("preclaim first-slice order drift")
    if value.index("source_ingestion_maintainer_approval_artifact") > value.index(
        "source_ingestion_admission_gate"
    ):
        raise EvidenceGraphAcyclicityError("preclaim admission order drift")


def _assert_string_sequence(value: object, expected: tuple[str, ...], label: str) -> None:
    if not isinstance(value, list) or tuple(value) != expected:
        raise EvidenceGraphAcyclicityError(f"preclaim {label} drift")
    for item in value:
        _validate_text(item, label)


def _json_payload(text: str, label: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise EvidenceGraphAcyclicityError(f"{label} must emit a JSON object")
    return payload


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    _validate_text(value, key)
    return str(value)


def _validate_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise EvidenceGraphAcyclicityError(f"preclaim {label} invalid")


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise EvidenceGraphAcyclicityError(
                f"preclaim report contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
