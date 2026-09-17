from dataclasses import replace

import pytest

from examples import bounded_mixed_native as mixed
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, TensorRef
from tuc.runtime import residency
from tuc.runtime.partitioning import partition_graph


def parameters():
    compiled, _ = mixed.compile_case("mixed")
    host = residency.ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    spaces = {
        "bounded-c11": host,
        "bounded-cuda": residency.ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
    }
    return compiled.hac_ir.graph, compiled.partition_plan, spaces, host


def test_shared_plan_includes_boundary_and_internal_transfers():
    graph, partition, spaces, host = parameters()
    result = residency.plan_residency(graph, partition, spaces, host)
    assert result.copy_bytes == 2516
    assert sum(b.bytes for b in result.buffers) == 5032
    assert len(result.steps) == 11
    assert [s.backend for s in result.steps if s.kind == "execute"] == [
        "bounded-cuda",
        "bounded-c11",
        "bounded-cuda",
    ]
    assert [result.buffers[s.outputs[0]].tensor for s in result.steps if s.kind == "copy"] == [
        "a",
        "b",
        "projection",
        "activated",
        "row_sum",
    ]
    assert partition.total_transfer_bytes() == 1320
    assert result.steps[-1].kind == "publish_output"


@pytest.mark.parametrize("separate", [True, False])
def test_space_identity_not_memory_technology_controls_copies(separate):
    graph, partition, _, _ = parameters()
    kind = MemoryDomainKind.UNKNOWN
    host = residency.ResidencySpace("host", kind)
    accelerator = residency.ResidencySpace("accelerator", kind) if separate else host
    assignments = tuple(replace(a, memory_domain=kind) for a in partition.assignments)
    partition = replace(partition, assignments=assignments, transfer_edges=())
    result = residency.plan_residency(
        graph, partition, {"bounded-c11": host, "bounded-cuda": accelerator}, host
    )
    assert result.copy_bytes == (2516 if separate else 0)


def test_fanout_reuses_immutable_resident_copy_and_publishes_both_outputs():
    graph, _, spaces, host = parameters()
    projection, relu, _ = graph.operations
    second = replace(relu, name="second_relu", outputs=(TensorRef("second", (33, 5)),))
    graph = ComputeGraph("fanout", (projection, relu, second))
    from tuc.backends.base import BackendCapability

    partition = partition_graph(
        graph,
        [
            BackendCapability(
                "bounded-c11", frozenset({relu.kind}), memory_domain=host.physical_kind
            ),
            BackendCapability(
                "bounded-cuda", frozenset({projection.kind}), memory_domain=MemoryDomainKind.UNKNOWN
            ),
        ],
    )
    assert len(partition.transfer_edges) == 2
    result = residency.plan_residency(graph, partition, spaces, host)
    copies = [s for s in result.steps if s.kind == "copy"]
    assert len(copies) == 3
    assert result.copy_bytes == 1724
    assert len([s for s in result.steps if s.kind == "publish_output"]) == 2


@pytest.mark.parametrize(
    "change",
    [
        "name",
        "missing",
        "order",
        "domain",
        "domain-string",
        "layout",
        "backend",
        "edge-missing",
        "edge-duplicate",
        "edge-bytes",
        "edge-layout",
        "space-conflict",
        "space-extra",
    ],
)
def test_misaligned_partition_rejected(change):
    graph, plan, spaces, host = parameters()
    if change == "name":
        plan = replace(plan, graph_name="different")
    elif change == "missing":
        plan = replace(plan, assignments=plan.assignments[:-1])
    elif change == "order":
        plan = replace(plan, assignments=tuple(reversed(plan.assignments)))
    elif change in ("domain", "domain-string", "layout", "backend"):
        updates = {
            "domain": {"memory_domain": MemoryDomainKind.HOST_RAM},
            "domain-string": {"memory_domain": "unknown"},
            "layout": {"produced_layout": LayoutKind.BLOCKED},
            "backend": {"backend_name": "absent"},
        }[change]
        plan = replace(
            plan, assignments=(replace(plan.assignments[0], **updates), *plan.assignments[1:])
        )
    elif change == "edge-missing":
        plan = replace(plan, transfer_edges=plan.transfer_edges[1:])
    elif change == "edge-duplicate":
        plan = replace(plan, transfer_edges=(*plan.transfer_edges, plan.transfer_edges[0]))
    elif change == "edge-bytes":
        edge = replace(plan.transfer_edges[0], bytes_moved=4, cost_estimate=None)
        plan = replace(plan, transfer_edges=(edge, *plan.transfer_edges[1:]))
    elif change == "edge-layout":
        edge = replace(plan.transfer_edges[0], source_layout=LayoutKind.BLOCKED)
        plan = replace(plan, transfer_edges=(edge, *plan.transfer_edges[1:]))
    elif change == "space-conflict":
        spaces["bounded-cuda"] = residency.ResidencySpace("host", MemoryDomainKind.UNKNOWN)
    else:
        spaces["extra"] = host
    with pytest.raises(ValueError):
        residency.plan_residency(graph, plan, spaces, host)


@pytest.mark.parametrize(
    "limit,value",
    [
        ("MAX_RESIDENCY_OPERATIONS", 2),
        ("MAX_RESIDENCY_PORTS", 2),
        ("MAX_RESIDENCY_BYTES", 1024),
        ("MAX_RESIDENCY_BUFFERS", 3),
    ],
)
def test_resource_budgets(limit, value, monkeypatch):
    args = parameters()
    monkeypatch.setattr(residency, limit, value)
    with pytest.raises(ValueError, match="budget"):
        residency.plan_residency(*args)


@pytest.mark.parametrize("name", ["x" * 129, "../../host", "a b", "", 1])
def test_space_names_are_bounded_identifiers(name):
    with pytest.raises(ValueError):
        residency.ResidencySpace(name, MemoryDomainKind.UNKNOWN)


@pytest.mark.parametrize("change", ["forward", "duplicate", "in-place"])
def test_non_ssa_graph_rejected(change):
    graph, plan, spaces, host = parameters()
    if change == "forward":
        graph = replace(graph, operations=tuple(reversed(graph.operations)))
        plan = replace(plan, assignments=tuple(reversed(plan.assignments)))
    else:
        op = graph.operations[1]
        name = "projection" if change == "duplicate" else "activated"
        op = replace(op, outputs=(TensorRef(name, (33, 5)),))
        if change == "in-place":
            op = replace(op, inputs=op.outputs)
        graph = replace(graph, operations=(graph.operations[0], op, graph.operations[2]))
    with pytest.raises(ValueError):
        residency.plan_residency(graph, plan, spaces, host)
