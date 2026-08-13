"""Data-only evidence graph acyclicity checks."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION = (
    "tuc.evidence_graph_acyclicity_gate_report.v0"
)
EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT = (
    "evidence_graph_acyclicity_gate.data_only.v0"
)
EVIDENCE_GRAPH_ACYCLICITY_GATE_ID = (
    "source_ingestion_evidence_graph_acyclicity_gate"
)
EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS = "PASS"
EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE = (
    "source_ingestion_first_slice_to_research_scope"
)
EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION = "dependent_report_to_bound_evidence"
EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY = "edge_digest_only_source_free"
EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS = (
    "edge_endpoints_declared",
    "graph_is_acyclic",
    "dependency_first_topological_order_emitted",
    "digest_only_source_free_edges",
    "source_ingestion_downstream_gates_do_not_cycle_into_first_slice",
)

MAX_EVIDENCE_GRAPH_NODES = 64
MAX_EVIDENCE_GRAPH_EDGES = 128
MAX_EVIDENCE_GRAPH_FIELD_BYTES = 256
MAX_EVIDENCE_GRAPH_REPORT_BYTES = 128 * 1024

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
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    "tl.dot",
    "tl.store",
)


class EvidenceGraphAcyclicityError(AssertionError):
    """Raised when an evidence graph is not a safe acyclic data graph."""


@dataclass(frozen=True)
class EvidenceGraphNode:
    """One source-free evidence node in the digest-binding graph."""

    evidence_id: str
    contract: str
    status: str
    node_kind: str = "evidence_report"
    source_free: bool = True

    def __post_init__(self) -> None:
        _validate_token(self.evidence_id, "node evidence_id")
        _validate_token(self.contract, "node contract")
        _validate_token(self.status, "node status")
        _validate_token(self.node_kind, "node kind")
        if self.source_free is not True:
            raise EvidenceGraphAcyclicityError("evidence graph node must be source-free")


@dataclass(frozen=True)
class EvidenceGraphEdge:
    """One digest binding from a dependent report to a bound evidence report."""

    from_evidence_id: str
    to_evidence_id: str
    bound_digest: str
    edge_kind: str = "digest_binding"
    source_free: bool = True

    def __post_init__(self) -> None:
        _validate_token(self.from_evidence_id, "edge from")
        _validate_token(self.to_evidence_id, "edge to")
        _validate_token(self.edge_kind, "edge kind")
        _validate_digest(self.bound_digest, "edge digest")
        if self.source_free is not True:
            raise EvidenceGraphAcyclicityError("evidence graph edge must be source-free")
        if self.from_evidence_id == self.to_evidence_id:
            raise EvidenceGraphAcyclicityError("evidence graph self-edge rejected")


@dataclass(frozen=True)
class EvidenceGraphAcyclicityReport:
    """Fail-closed data-only report proving the current evidence graph is acyclic."""

    nodes: tuple[EvidenceGraphNode, ...]
    edges: tuple[EvidenceGraphEdge, ...]
    schema_version: str = EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION
    gate_contract: str = EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT
    gate_id: str = EVIDENCE_GRAPH_ACYCLICITY_GATE_ID
    gate_status: str = EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS
    graph_scope: str = EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE
    edge_direction: str = EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION
    evidence_policy: str = EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY
    required_invariants: tuple[str, ...] = (
        EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS
    )

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION:
            raise EvidenceGraphAcyclicityError("evidence graph schema version drift")
        if self.gate_contract != EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT:
            raise EvidenceGraphAcyclicityError("evidence graph contract drift")
        if self.gate_id != EVIDENCE_GRAPH_ACYCLICITY_GATE_ID:
            raise EvidenceGraphAcyclicityError("evidence graph gate id drift")
        if self.gate_status != EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS:
            raise EvidenceGraphAcyclicityError("evidence graph gate status drift")
        if self.graph_scope != EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE:
            raise EvidenceGraphAcyclicityError("evidence graph scope drift")
        if self.edge_direction != EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION:
            raise EvidenceGraphAcyclicityError("evidence graph edge direction drift")
        if self.evidence_policy != EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY:
            raise EvidenceGraphAcyclicityError("evidence graph policy drift")
        if self.required_invariants != EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS:
            raise EvidenceGraphAcyclicityError("evidence graph invariants drift")
        _validate_graph(self.nodes, self.edges)


def build_evidence_graph_acyclicity_report(
    nodes: Iterable[EvidenceGraphNode],
    edges: Iterable[EvidenceGraphEdge],
) -> EvidenceGraphAcyclicityReport:
    """Build a fail-closed acyclicity report from evidence graph records."""

    return EvidenceGraphAcyclicityReport(nodes=tuple(nodes), edges=tuple(edges))


def assert_evidence_graph_acyclicity_report(
    report: EvidenceGraphAcyclicityReport,
) -> None:
    """Fail closed unless the report is the current acyclic evidence graph."""

    if not isinstance(report, EvidenceGraphAcyclicityReport):
        raise TypeError("evidence graph report must be report")
    _validate_graph(report.nodes, report.edges)


def evidence_graph_acyclicity_report_to_dict(
    report: EvidenceGraphAcyclicityReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible acyclicity gate report."""

    assert_evidence_graph_acyclicity_report(report)
    topological_order = _dependency_first_topological_order(report.nodes, report.edges)
    return {
        "cycle_count": 0,
        "detected_cycles": [],
        "edge_count": len(report.edges),
        "edge_direction": report.edge_direction,
        "edges": [_edge_to_dict(edge) for edge in report.edges],
        "evidence_policy": report.evidence_policy,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "graph_scope": report.graph_scope,
        "node_count": len(report.nodes),
        "nodes": [_node_to_dict(node) for node in report.nodes],
        "required_invariants": list(report.required_invariants),
        "schema_version": report.schema_version,
        "source_free": True,
        "topological_order": list(topological_order),
    }


def dump_evidence_graph_acyclicity_report(
    report: EvidenceGraphAcyclicityReport,
) -> str:
    """Render stable JSON evidence for the acyclicity gate."""

    payload = evidence_graph_acyclicity_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_EVIDENCE_GRAPH_REPORT_BYTES:
        raise EvidenceGraphAcyclicityError("evidence graph report exceeds byte limit")
    return text + "\n"


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return a canonical digest for source-free JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _node_to_dict(node: EvidenceGraphNode) -> dict[str, object]:
    return {
        "contract": node.contract,
        "evidence_id": node.evidence_id,
        "node_kind": node.node_kind,
        "source_free": node.source_free,
        "status": node.status,
    }


def _edge_to_dict(edge: EvidenceGraphEdge) -> dict[str, object]:
    return {
        "bound_digest": edge.bound_digest,
        "edge_kind": edge.edge_kind,
        "from_evidence_id": edge.from_evidence_id,
        "source_free": edge.source_free,
        "to_evidence_id": edge.to_evidence_id,
    }


def _validate_graph(
    nodes: tuple[EvidenceGraphNode, ...],
    edges: tuple[EvidenceGraphEdge, ...],
) -> None:
    if not nodes:
        raise EvidenceGraphAcyclicityError("evidence graph nodes required")
    if len(nodes) > MAX_EVIDENCE_GRAPH_NODES:
        raise EvidenceGraphAcyclicityError("evidence graph node limit exceeded")
    if len(edges) > MAX_EVIDENCE_GRAPH_EDGES:
        raise EvidenceGraphAcyclicityError("evidence graph edge limit exceeded")

    node_ids: set[str] = set()
    for node in nodes:
        if node.evidence_id in node_ids:
            raise EvidenceGraphAcyclicityError("evidence graph duplicate node")
        node_ids.add(node.evidence_id)

    edge_pairs: set[tuple[str, str]] = set()
    for edge in edges:
        if edge.from_evidence_id not in node_ids or edge.to_evidence_id not in node_ids:
            raise EvidenceGraphAcyclicityError("evidence graph edge endpoint missing")
        pair = (edge.from_evidence_id, edge.to_evidence_id)
        if pair in edge_pairs:
            raise EvidenceGraphAcyclicityError("evidence graph duplicate edge")
        edge_pairs.add(pair)

    cycle = _find_cycle(tuple(sorted(node_ids)), edges)
    if cycle:
        raise EvidenceGraphAcyclicityError(
            "evidence graph cycle detected: " + " -> ".join(cycle)
        )


def _find_cycle(
    node_ids: tuple[str, ...],
    edges: tuple[EvidenceGraphEdge, ...],
) -> tuple[str, ...]:
    adjacency = _adjacency(node_ids, edges)
    state: dict[str, int] = {node_id: 0 for node_id in node_ids}
    stack: list[str] = []

    def visit(node_id: str) -> tuple[str, ...]:
        state[node_id] = 1
        stack.append(node_id)
        for neighbor in adjacency[node_id]:
            if state[neighbor] == 0:
                cycle = visit(neighbor)
                if cycle:
                    return cycle
            elif state[neighbor] == 1:
                return tuple(stack[stack.index(neighbor) :] + [neighbor])
        stack.pop()
        state[node_id] = 2
        return ()

    for node_id in node_ids:
        if state[node_id] == 0:
            cycle = visit(node_id)
            if cycle:
                return cycle
    return ()


def _dependency_first_topological_order(
    nodes: tuple[EvidenceGraphNode, ...],
    edges: tuple[EvidenceGraphEdge, ...],
) -> tuple[str, ...]:
    node_ids = tuple(sorted(node.evidence_id for node in nodes))
    adjacency = _adjacency(node_ids, edges)
    seen: set[str] = set()
    order: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        for neighbor in adjacency[node_id]:
            visit(neighbor)
        order.append(node_id)

    for node_id in node_ids:
        visit(node_id)
    return tuple(order)


def _adjacency(
    node_ids: tuple[str, ...],
    edges: tuple[EvidenceGraphEdge, ...],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        grouped[edge.from_evidence_id].append(edge.to_evidence_id)
    return {node_id: tuple(sorted(neighbors)) for node_id, neighbors in grouped.items()}


def _validate_token(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise EvidenceGraphAcyclicityError(f"evidence graph {label} invalid")
    if len(value.encode("utf-8")) > MAX_EVIDENCE_GRAPH_FIELD_BYTES:
        raise EvidenceGraphAcyclicityError(f"evidence graph {label} exceeds limit")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise EvidenceGraphAcyclicityError(f"evidence graph {label} invalid")


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise EvidenceGraphAcyclicityError(
                f"evidence graph contains forbidden fragment: {fragment}"
            )


__all__ = [
    "EVIDENCE_GRAPH_ACYCLICITY_EDGE_DIRECTION",
    "EVIDENCE_GRAPH_ACYCLICITY_EVIDENCE_POLICY",
    "EVIDENCE_GRAPH_ACYCLICITY_GATE_CONTRACT",
    "EVIDENCE_GRAPH_ACYCLICITY_GATE_ID",
    "EVIDENCE_GRAPH_ACYCLICITY_GATE_STATUS",
    "EVIDENCE_GRAPH_ACYCLICITY_GRAPH_SCOPE",
    "EVIDENCE_GRAPH_ACYCLICITY_REPORT_SCHEMA_VERSION",
    "EVIDENCE_GRAPH_ACYCLICITY_REQUIRED_INVARIANTS",
    "EvidenceGraphAcyclicityError",
    "EvidenceGraphAcyclicityReport",
    "EvidenceGraphEdge",
    "EvidenceGraphNode",
    "assert_evidence_graph_acyclicity_report",
    "build_evidence_graph_acyclicity_report",
    "digest_json_payload",
    "dump_evidence_graph_acyclicity_report",
    "evidence_graph_acyclicity_report_to_dict",
]
