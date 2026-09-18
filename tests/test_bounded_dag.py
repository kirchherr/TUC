"""Independent dataflow checks for source-only bounded DAG lowering.

The interpreters below execute Python binary32 arithmetic, never emitted native
code. They check normalized schedule semantics, not native execution evidence.
"""

from __future__ import annotations

import ctypes
import itertools
import json
import re
import socket
import struct
import subprocess
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from math import prod

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import (
    DAGTarget,
    lower_bounded_dag,
    validate_bounded_dag_artifacts,
)
from tuc.compiler.pipeline import compile_graph
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRStage
from tuc.runtime.overrides import RuntimeOverrideAction, RuntimeOverrideRule, RuntimeOverrideSet


def _op(name, kind, inputs, output, **attributes):
    return ComputeOperation(name, kind, tuple(inputs), (output,), attributes)


def _graph(family="chain", dimensions=(3, 2, 3)):
    rows, inner, columns = dimensions
    a = TensorRef("a", (rows, inner))
    b = TensorRef("b", (inner, columns))
    p = TensorRef("projection", (rows, columns))
    q = TensorRef("positive", (rows, columns))
    y = TensorRef("sum", (rows,))
    raw = TensorRef("raw", (rows,))
    mm = _op("project", OperationKind.MATMUL, (a, b), p)
    relu = _op("activate", OperationKind.ELEMENTWISE, (p,), q, kernel="relu")
    total = _op("reduce", OperationKind.REDUCTION, (q,), y, axis=1)
    if family == "chain":
        operations = (mm, relu, total)
    elif family == "fanout":
        direct = _op("direct", OperationKind.REDUCTION, (p,), raw, axis=1)
        operations = (mm, relu, direct, total)
    elif family == "fanin":
        left = TensorRef("left", a.shape)
        right = TensorRef("right", b.shape)
        operations = (
            _op("left_relu", OperationKind.ELEMENTWISE, (a,), left, kernel="relu"),
            _op("right_relu", OperationKind.ELEMENTWISE, (b,), right, kernel="relu"),
            _op("project", OperationKind.MATMUL, (left, right), p),
            _op("reduce", OperationKind.REDUCTION, (p,), y, axis=1),
        )
    elif family == "rejoin":
        # This graph has three Matmuls, a shared signed intermediate and two
        # different produced operands meeting at the last Matmul. It is not one
        # of the historical fixed native programs.
        assert rows == columns
        c = TensorRef("c", (columns, columns))
        branch = TensorRef("branch", (rows, columns))
        right = TensorRef("right", branch.shape)
        joined = TensorRef("joined", branch.shape)
        operations = (
            mm,
            relu,
            _op("branch_matmul", OperationKind.MATMUL, (p, c), branch),
            _op("right_relu", OperationKind.ELEMENTWISE, (branch,), right, kernel="relu"),
            _op("join", OperationKind.MATMUL, (q, right), joined),
            _op("direct", OperationKind.REDUCTION, (p,), raw, axis=1),
            _op("reduce", OperationKind.REDUCTION, (joined,), y, axis=1),
        )
    else:
        raise AssertionError(family)
    return ComputeGraph("test_dag", operations)


def _compiled(graph=None, profile=None):
    graph = _graph() if graph is None else graph
    profile = "c" * len(graph.operations) if profile is None else profile
    assert len(profile) == len(graph.operations)
    kinds = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
    caps = (
        BackendCapability("cpu", kinds, memory_domain=MemoryDomainKind.HOST_RAM),
        BackendCapability("gpu", kinds, memory_domain=MemoryDomainKind.UNKNOWN),
    )
    overrides = RuntimeOverrideSet(
        tuple(
            RuntimeOverrideRule(
                op.name,
                RuntimeOverrideAction.REQUIRE_BACKEND,
                "cpu" if character == "c" else "gpu",
            )
            for op, character in zip(graph.operations, profile, strict=True)
        )
    )
    compiled = compile_graph(graph, caps, runtime_overrides=overrides)
    targets = {"cpu": DAGTarget.C11, "gpu": DAGTarget.CUDA_SM86}
    used = {assignment.backend_name for assignment in compiled.partition_plan.assignments}
    return compiled.hac_ir, compiled.partition_plan, {key: targets[key] for key in sorted(used)}


def _f32(value):
    return struct.unpack("!f", struct.pack("!f", value))[0]


def _bits(values):
    return b"".join(struct.pack("!f", value) for value in values)


def _external_inputs(graph, corpus_index):
    produced = {tensor.name for op in graph.operations for tensor in op.outputs}
    tensors = {}
    for op in graph.operations:
        for tensor in op.inputs:
            if tensor.name not in produced:
                tensors.setdefault(tensor.name, tensor)
    # Dyadic and non-dyadic operands, distinct tensors, positive and negative
    # values, and non-square shapes expose operand/stride/order confusion.
    return {
        name: [
            _f32((((index * 11 + ordinal * 7 + corpus_index * 13) % 23) - 11) / 7)
            for index in range(prod(tensor.shape))
        ]
        for ordinal, (name, tensor) in enumerate(tensors.items())
    }


def _graph_reference(graph, external):
    """Evaluate original tensor edges using independently nested row lists."""
    values = {key: list(value) for key, value in external.items()}
    consumed = {tensor.name for op in graph.operations for tensor in op.inputs}
    for op in graph.operations:
        if op.kind is OperationKind.MATMUL:
            left, right = op.inputs
            rows, inner = left.shape
            columns = right.shape[1]
            left_rows = [values[left.name][row * inner : (row + 1) * inner] for row in range(rows)]
            right_rows = [
                values[right.name][row * columns : (row + 1) * columns] for row in range(inner)
            ]
            result = []
            for row in left_rows:
                for column in zip(*right_rows, strict=True):
                    total = 0.0
                    for a, b in zip(row, column, strict=True):
                        total = _f32(total + _f32(a * b))
                    result.append(total)
        elif op.kind is OperationKind.ELEMENTWISE:
            result = [value if value > 0 else 0.0 for value in values[op.inputs[0].name]]
        else:
            assert op.kind is OperationKind.REDUCTION
            width = op.inputs[0].shape[1]
            source = values[op.inputs[0].name]
            result = []
            for start in range(0, len(source), width):
                total = 0.0
                for value in source[start : start + width]:
                    total = _f32(total + value)
                result.append(total)
        values[op.outputs[0].name] = result
    return {
        tensor.name: values[tensor.name]
        for op in graph.operations
        for tensor in op.outputs
        if tensor.name not in consumed
    }


def _replay(manifest, external):
    """Replay normalized slots without consulting the original graph or planner."""
    tensors = manifest["tensors"]
    buffers = manifest["buffers"]
    operations = manifest["operations"]
    slots = {}
    published = {}
    calls = []
    for ordinal, event in enumerate(manifest["events"]):
        assert event["index"] == ordinal
        for slot in (*event["inputs"], *event["outputs"]):
            assert type(slot) is int and 0 <= slot < len(buffers)
        assert all(slot in slots for slot in event["inputs"])
        assert all(slot not in slots for slot in event["outputs"])
        kind = event["kind"]
        if kind == "bind_input":
            assert not event["inputs"] and len(event["outputs"]) == 1
            out = event["outputs"][0]
            assert buffers[out]["space"] == "host"
            tensor = tensors[buffers[out]["tensor"]]
            slots[out] = list(external[tensor["name"]])
        elif kind == "copy":
            (source,) = event["inputs"]
            (out,) = event["outputs"]
            assert buffers[source]["tensor"] == buffers[out]["tensor"]
            assert buffers[source]["space"] != buffers[out]["space"]
            assert buffers[source]["bytes"] == buffers[out]["bytes"]
            slots[out] = list(slots[source])
        elif kind == "execute":
            op = operations[event["operation"]]
            assert op["index"] not in calls
            calls.append(op["index"])
            assert [buffers[slot]["tensor"] for slot in event["inputs"]] == op["inputs"]
            assert [buffers[slot]["tensor"] for slot in event["outputs"]] == op["outputs"]
            assert event["target"] == op["target"]
            space = "host" if op["target"] == "c11" else "accelerator"
            assert all(
                buffers[slot]["space"] == space for slot in (*event["inputs"], *event["outputs"])
            )
            args = [slots[slot] for slot in event["inputs"]]
            shape = op["output_shape"]
            if op["kind"] == "matmul":
                rows, columns = shape
                inner = op["input_shapes"][0][1]
                output = [0.0] * (rows * columns)
                for element in range(len(output)):
                    row, column = divmod(element, columns)
                    for k in range(inner):
                        output[element] = _f32(
                            output[element]
                            + _f32(args[0][row * inner + k] * args[1][k * columns + column])
                        )
            elif op["kind"] == "relu":
                output = [max(0.0, value) for value in args[0]]
            else:
                assert op["kind"] == "sum_axis1"
                width = op["input_shapes"][0][1]
                output = [0.0] * shape[0]
                for row in range(shape[0]):
                    for column in range(width):
                        output[row] = _f32(output[row] + args[0][row * width + column])
            (out,) = event["outputs"]
            slots[out] = output
        else:
            assert kind == "publish_output" and not event["outputs"]
            (source,) = event["inputs"]
            assert buffers[source]["space"] == "host"
            tensor = tensors[buffers[source]["tensor"]]
            assert tensor["name"] not in published
            published[tensor["name"]] = slots[source]
        for slot, value in slots.items():
            assert len(value) * 4 == buffers[slot]["bytes"]
    assert calls == list(range(len(operations)))
    assert len(slots) == len(buffers)
    assert set(published) == {tensors[index]["name"] for index in manifest["output_tensors"]}
    return published


@pytest.mark.parametrize("family", ["chain", "fanout", "fanin", "rejoin"])
def test_every_placement_preserves_independent_fp32_dataflow(family):
    graph = _graph(family)
    baselines = None
    for characters in itertools.product("cg", repeat=len(graph.operations)):
        profile = "".join(characters)
        module, partition, targets = _compiled(graph, profile)
        artifacts = lower_bounded_dag(module, partition, targets)
        manifest = json.loads(artifacts.manifest_json)
        kernels = (artifacts.c11_header, artifacts.c11_source, artifacts.cuda_source)
        if baselines is None:
            baselines = (manifest["hac_ir"], kernels)
        assert (manifest["hac_ir"], kernels) == baselines
        assert manifest["normal_runtime_admission"] is False
        assert manifest["native_execution_observed"] is False
        assert manifest["latency_ns"] is None and manifest["energy_pj"] is None
        for corpus_index in range(3):
            external = _external_inputs(graph, corpus_index)
            expected = _graph_reference(graph, external)
            observed = _replay(manifest, external)
            assert {key: _bits(value) for key, value in observed.items()} == {
                key: _bits(value) for key, value in expected.items()
            }, (family, profile, corpus_index)


@pytest.mark.parametrize("dimensions", [(1, 1, 1), (2, 5, 7), (33, 7, 5), (64, 1, 64)])
def test_static_shapes_are_lowered_from_graph_not_historical_templates(dimensions):
    graph = _graph("fanin", dimensions)
    artifacts = lower_bounded_dag(*_compiled(graph, "gcgg"))
    manifest = json.loads(artifacts.manifest_json)
    external = _external_inputs(graph, 2)
    assert _replay(manifest, external) == _graph_reference(graph, external)


def test_rank_one_relu_and_multiple_independent_outputs():
    tensors = [TensorRef(name, (5,)) for name in ("a", "b", "x", "y")]
    graph = ComputeGraph(
        "vectors",
        (
            _op(
                "first",
                OperationKind.ELEMENTWISE,
                (tensors[0],),
                tensors[2],
                kernel="relu",
            ),
            _op(
                "second",
                OperationKind.ELEMENTWISE,
                (tensors[1],),
                tensors[3],
                kernel="relu",
            ),
        ),
    )
    manifest = json.loads(lower_bounded_dag(*_compiled(graph, "gc")).manifest_json)
    external = _external_inputs(graph, 0)
    assert _replay(manifest, external) == _graph_reference(graph, external)


def test_shared_projection_is_copied_once_for_two_host_consumers():
    manifest = json.loads(lower_bounded_dag(*_compiled(_graph("fanout"), "gccc")).manifest_json)
    tensors, buffers = manifest["tensors"], manifest["buffers"]
    projection = next(t["index"] for t in tensors if t["name"] == "projection")
    copies = [
        event
        for event in manifest["events"]
        if event["kind"] == "copy" and buffers[event["outputs"][0]]["tensor"] == projection
    ]
    assert len(copies) == 1
    shared = copies[0]["outputs"][0]
    consumers = [
        event
        for event in manifest["events"]
        if event["kind"] == "execute" and shared in event["inputs"]
    ]
    assert len(consumers) == 2
    assert manifest["planned_copy_bytes"] == 4 * (3 * 2 + 2 * 3 + 3 * 3)


@pytest.mark.parametrize("family", ["chain", "fanout", "fanin", "rejoin"])
def test_static_schedule_header_and_manifest_describe_identical_events(family):
    graph = _graph(family)
    profile = ("gc" * len(graph.operations))[: len(graph.operations)]
    artifacts = lower_bounded_dag(*_compiled(graph, profile))
    manifest = json.loads(artifacts.manifest_json)

    def rows(name):
        match = re.search(
            rf"static const struct [a-z_]+ {name}\[\] = \{{(.*?)\n\}};",
            artifacts.schedule_header,
            flags=re.DOTALL,
        )
        assert match is not None
        result = []
        for line in match[1].strip().splitlines():
            assert re.fullmatch(r"\s*\{[0-9U, ]+\},", line)
            result.append([int(number) for number in re.findall(r"([0-9]+)U", line)])
        return result

    assert rows("tuc_dag_buffers") == [
        [buffer["tensor"], 0 if buffer["space"] == "host" else 1, buffer["bytes"]]
        for buffer in manifest["buffers"]
    ]
    kinds = {"matmul": 0, "relu": 1, "sum_axis1": 2}
    assert rows("tuc_dag_operations") == [
        [
            kinds[op["kind"]],
            op["inputs"][0],
            op["inputs"][1] if len(op["inputs"]) == 2 else 255,
            op["outputs"][0],
        ]
        for op in manifest["operations"]
    ]
    events = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}
    targets = {"c11": 0, "cuda-sm86": 1, None: 255}
    assert rows("tuc_dag_events") == [
        [
            events[event["kind"]],
            event["operation"] if event["operation"] is not None else 255,
            targets[event["target"]],
            *(event["inputs"] + [255, 255])[:2],
            event["outputs"][0] if event["outputs"] else 255,
        ]
        for event in manifest["events"]
    ]


def test_renaming_symbols_cannot_change_or_inject_native_code():
    graph = _graph("rejoin")
    tensors = {
        tensor.name: TensorRef("renamed_" + tensor.name, tensor.shape)
        for op in graph.operations
        for tensor in (*op.inputs, *op.outputs)
    }
    renamed = ComputeGraph(
        "renamed_graph",
        tuple(
            replace(
                op,
                name="renamed_" + op.name,
                inputs=tuple(tensors[tensor.name] for tensor in op.inputs),
                outputs=tuple(tensors[tensor.name] for tensor in op.outputs),
            )
            for op in graph.operations
        ),
    )
    before = lower_bounded_dag(*_compiled(graph))
    after = lower_bounded_dag(*_compiled(renamed))
    assert (before.c11_header, before.c11_source, before.cuda_source, before.schedule_header) == (
        after.c11_header,
        after.c11_source,
        after.cuda_source,
        after.schedule_header,
    )
    assert before.manifest_json != after.manifest_json


def test_artifacts_are_deterministic_frozen_and_content_bound():
    inputs = _compiled(_graph("fanin"), "gcgg")
    artifacts = lower_bounded_dag(*inputs)
    assert artifacts == lower_bounded_dag(*inputs)
    validate_bounded_dag_artifacts(artifacts, *inputs)
    manifest = json.loads(artifacts.manifest_json)
    for name, expected in manifest["source_digests"].items():
        assert expected == "sha256:" + sha256(artifacts.files()[name].encode()).hexdigest()
    assert manifest["hac_ir_digest"] == "sha256:" + sha256(manifest["hac_ir"].encode()).hexdigest()
    for op in manifest["operations"]:
        count = prod(op["output_shape"])
        geometry = op["launch"]
        assert geometry["dimensions"] == 1
        assert geometry["threads_per_block"] == 128
        assert (geometry["blocks"] - 1) * 128 < count <= geometry["blocks"] * 128
    with pytest.raises(FrozenInstanceError):
        artifacts.c11_source = "changed"
    files = artifacts.files()
    files["generated.c"] = "changed"
    assert artifacts.c11_source != "changed"


@pytest.mark.parametrize(
    "field", ["manifest_json", "c11_header", "c11_source", "cuda_source", "schedule_header"]
)
def test_artifact_drift_rejects_before_any_execution(field):
    inputs = _compiled()
    artifacts = lower_bounded_dag(*inputs)
    with pytest.raises(ValueError):
        validate_bounded_dag_artifacts(
            replace(artifacts, **{field: getattr(artifacts, field) + " "}), *inputs
        )


def test_lowering_does_not_launch_processes_load_libraries_or_access_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source-only lowering crossed an execution boundary")

    inputs = _compiled(_graph("fanin"), "gcgg")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(ctypes, "CDLL", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    artifacts = lower_bounded_dag(*inputs)
    validate_bounded_dag_artifacts(artifacts, *inputs)


@pytest.mark.parametrize(
    "fault",
    [
        "stage",
        "raw-stage",
        "module-target",
        "graph-type",
        "operations-list",
        "operation-type",
        "ports-list",
        "tensor-type",
        "shape-list",
        "bool-dimension",
        "dimension-limit",
        "dtype",
        "name-limit",
        "unsafe-name",
        "module-type",
    ],
)
def test_malformed_typed_records_are_revalidated(fault):
    module, partition, targets = _compiled()
    graph = module.graph
    op = graph.operations[0]
    tensor = op.inputs[0]
    if fault == "stage":
        module = replace(module, stage=IRStage.TLIR)
    elif fault == "raw-stage":
        module = replace(module, stage="hac-ir")
    elif fault == "module-target":
        module = replace(module, target="unexpected")
    elif fault == "graph-type":
        module = replace(module, graph={})
    elif fault == "operations-list":
        object.__setattr__(graph, "operations", list(graph.operations))
    elif fault == "operation-type":
        object.__setattr__(graph, "operations", ({}, *graph.operations[1:]))
    elif fault == "ports-list":
        object.__setattr__(op, "inputs", list(op.inputs))
    elif fault == "tensor-type":
        object.__setattr__(op, "inputs", ({}, op.inputs[1]))
    elif fault == "shape-list":
        object.__setattr__(tensor, "shape", list(tensor.shape))
    elif fault == "bool-dimension":
        object.__setattr__(tensor, "shape", (True, 2))
    elif fault == "dimension-limit":
        object.__setattr__(tensor, "shape", (65, 2))
    elif fault == "dtype":
        object.__setattr__(tensor, "dtype", "float64")
    elif fault == "name-limit":
        object.__setattr__(tensor, "name", "x" * 65)
    elif fault == "unsafe-name":
        object.__setattr__(tensor, "name", 'x;system("bad")')
    elif fault == "module-type":
        module = {"stage": "hac-ir"}
    with pytest.raises(ValueError):
        lower_bounded_dag(module, partition, targets)


@pytest.mark.parametrize(
    "index,attributes",
    [
        (0, {"alpha": 2}),
        (0, {"transpose_a": True}),
        (0, {"tuc.layout": "column_major"}),
        (0, {"tuc.layout_tile_shape": (2, 2)}),
        (1, {"kernel": "sigmoid"}),
        (1, {"kernel": None}),
        (1, {"elementwise_kind": "relu"}),
        (1, {"elementwise_kind": "add"}),
        (2, {"axis": 0}),
        (2, {"axis": True}),
        (2, {"axis": -1}),
        (2, {"keepdims": True}),
    ],
)
def test_unsupported_or_ambiguous_semantics_reject(index, attributes):
    module, partition, targets = _compiled()
    op = module.graph.operations[index]
    changed = dict(op.attributes)
    changed.update(attributes)
    if changed.get("kernel", "present") is None:
        changed.pop("kernel")
    operations = list(module.graph.operations)
    operations[index] = replace(op, attributes=changed)
    module = replace(module, graph=replace(module.graph, operations=tuple(operations)))
    with pytest.raises(ValueError):
        lower_bounded_dag(module, partition, targets)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-producer",
        "forward-use",
        "in-place",
        "tensor-shape",
        "matmul-inner",
        "reduction-output",
        "relu-output",
    ],
)
def test_graph_semantic_and_ssa_faults_reject(fault):
    module, partition, targets = _compiled()
    ops = list(module.graph.operations)
    if fault == "duplicate-producer":
        ops[1] = replace(ops[1], outputs=ops[0].outputs)
    elif fault == "forward-use":
        ops[0] = replace(ops[0], inputs=(ops[1].outputs[0], ops[0].inputs[1]))
    elif fault == "in-place":
        ops[1] = replace(ops[1], outputs=ops[1].inputs)
    elif fault == "tensor-shape":
        object.__setattr__(ops[1], "inputs", (TensorRef("projection", (3, 4)),))
    elif fault == "matmul-inner":
        ops[0] = replace(ops[0], inputs=(ops[0].inputs[0], TensorRef("b", (4, 3))))
    elif fault == "reduction-output":
        ops[2] = replace(ops[2], outputs=(TensorRef("sum", (2,)),))
    elif fault == "relu-output":
        object.__setattr__(ops[1], "outputs", (TensorRef("positive", (2, 3)),))
    object.__setattr__(module.graph, "operations", tuple(ops))
    with pytest.raises(ValueError):
        lower_bounded_dag(module, partition, targets)


@pytest.mark.parametrize(
    "fault",
    [
        "graph",
        "assignment-count",
        "assignment-order",
        "assignment-type",
        "domain",
        "layout",
        "backend",
        "edges-missing",
        "edges-duplicate",
        "edges-size",
        "raw-target",
        "missing-target",
        "extra-target",
        "target-type",
    ],
)
def test_partition_and_target_mapping_cannot_forge_residency(fault):
    module, partition, targets = _compiled(_graph("fanout"), "gccc")
    if fault == "graph":
        partition = replace(partition, graph_name="other")
    elif fault == "assignment-count":
        partition = replace(partition, assignments=partition.assignments[:-1])
    elif fault == "assignment-order":
        partition = replace(partition, assignments=tuple(reversed(partition.assignments)))
    elif fault == "assignment-type":
        partition = replace(partition, assignments=({}, *partition.assignments[1:]))
    elif fault in ("domain", "layout", "backend"):
        field, value = {
            "domain": ("memory_domain", MemoryDomainKind.HOST_RAM),
            "layout": ("produced_layout", LayoutKind.BLOCKED),
            "backend": ("backend_name", "absent"),
        }[fault]
        partition = replace(
            partition,
            assignments=(
                replace(partition.assignments[0], **{field: value}),
                *partition.assignments[1:],
            ),
        )
    elif fault == "edges-missing":
        partition = replace(partition, transfer_edges=partition.transfer_edges[1:])
    elif fault == "edges-duplicate":
        partition = replace(
            partition, transfer_edges=(*partition.transfer_edges, partition.transfer_edges[0])
        )
    elif fault == "edges-size":
        edge = replace(partition.transfer_edges[0], bytes_moved=4, cost_estimate=None)
        partition = replace(partition, transfer_edges=(edge, *partition.transfer_edges[1:]))
    elif fault == "raw-target":
        targets["gpu"] = "cuda-sm86"
    elif fault == "missing-target":
        del targets["gpu"]
    elif fault == "extra-target":
        targets["unused"] = DAGTarget.C11
    elif fault == "target-type":
        targets = tuple(targets.items())
    with pytest.raises(ValueError):
        lower_bounded_dag(module, partition, targets)


def test_operation_budget_is_checked_before_emission():
    shape = (2, 2)
    tensor = TensorRef("input", shape)
    operations = []
    for index in range(9):
        output = TensorRef(f"v{index}", shape)
        operations.append(
            _op(
                f"relu{index}",
                OperationKind.ELEMENTWISE,
                (tensor,),
                output,
                kernel="relu",
            )
        )
        tensor = output
    inputs = _compiled(ComputeGraph("too_many", tuple(operations)))
    with pytest.raises(ValueError):
        lower_bounded_dag(*inputs)


def test_scalar_work_budget_prevents_large_composed_matmul():
    tensor = TensorRef("input", (64, 64))
    operations = []
    for index in range(5):
        right = TensorRef(f"w{index}", (64, 64))
        output = TensorRef(f"v{index}", (64, 64))
        operations.append(_op(f"mm{index}", OperationKind.MATMUL, (tensor, right), output))
        tensor = output
    with pytest.raises(ValueError):
        lower_bounded_dag(*_compiled(ComputeGraph("too_much_work", tuple(operations))))


def test_logical_buffer_budget_counts_device_and_host_output_copies():
    operations = []
    for index in range(8):
        left = TensorRef(f"a{index}", (64, 1))
        right = TensorRef(f"b{index}", (1, 64))
        output = TensorRef(f"v{index}", (64, 64))
        operations.append(_op(f"mm{index}", OperationKind.MATMUL, (left, right), output))
    # Seven independent outer products are below the byte limit, while eight
    # need 270336 bytes despite having little scalar arithmetic work.
    seven = lower_bounded_dag(*_compiled(ComputeGraph("seven", tuple(operations[:7])), "g" * 7))
    assert json.loads(seven.manifest_json)["planned_buffer_bytes"] == 236544
    with pytest.raises(ValueError):
        lower_bounded_dag(*_compiled(ComputeGraph("eight", tuple(operations)), "g" * 8))


@pytest.mark.parametrize("changed", ["shape", "placement", "graph-name"])
def test_artifact_validation_binds_current_input_graph_and_partition(changed):
    original = _compiled()
    artifacts = lower_bounded_dag(*original)
    if changed == "shape":
        different = _compiled(_graph(dimensions=(2, 3, 4)))
    elif changed == "placement":
        different = _compiled(profile="cgc")
    else:
        different = _compiled(replace(_graph(), name="another_graph"))
    with pytest.raises(ValueError):
        validate_bounded_dag_artifacts(artifacts, *different)


@pytest.mark.parametrize("metadata", [{"payload": "x" * (64 * 1024 + 1)}, {"payload": object()}])
def test_module_metadata_is_bounded_before_serialization(metadata):
    module, partition, targets = _compiled()
    with pytest.raises(ValueError):
        lower_bounded_dag(replace(module, metadata=metadata), partition, targets)


@pytest.mark.parametrize(
    "policy,aliases",
    [
        ("explicit_public_returns", ("result:projection", "raw:raw", "sum:sum")),
        ("explicit_public_returns", ("result:a", "raw:raw", "sum:sum")),
        ("explicit_public_returns", ("result:missing", "raw:raw", "sum:sum")),
        ("explicit_public_returns", ("raw:raw",)),
        ("explicit_public_returns", ()),
        ("unknown_policy", ("raw:raw", "sum:sum")),
        ("explicit_public_returns", ("raw:raw:extra", "sum:sum")),
        ("explicit_public_returns", ("duplicate:raw", "duplicate:sum")),
        ("explicit_public_returns", (True, "sum:sum")),
        ("explicit_public_returns", "raw:raw"),
        (None, ("raw:raw", "sum:sum")),
        ("explicit_public_returns", None),
    ],
)
def test_explicit_source_returns_cannot_be_silently_replaced_by_terminal_outputs(policy, aliases):
    metadata = {}
    if policy is not None:
        metadata["frontend.source_intent_return_policy"] = policy
    if aliases is not None:
        metadata["frontend.source_intent_return_aliases"] = aliases
    graph = _graph("fanout").with_metadata(**metadata)
    with pytest.raises(ValueError):
        lower_bounded_dag(*_compiled(graph, "gccc"))


def test_matching_explicit_public_returns_remain_bound_in_artifact_manifest():
    graph = _graph("fanout").with_metadata(
        **{
            "frontend.source_intent_return_policy": "explicit_public_returns",
            "frontend.source_intent_return_aliases": ("positive_result:sum", "raw_result:raw"),
        }
    )
    inputs = _compiled(graph, "gccc")
    artifacts = lower_bounded_dag(*inputs)
    manifest = json.loads(artifacts.manifest_json)
    assert "positive_result:sum" in manifest["hac_ir"]
    assert "raw_result:raw" in manifest["hac_ir"]
    names = {tensor["index"]: tensor["name"] for tensor in manifest["tensors"]}
    assert {
        binding["public_name"]: names[binding["tensor"]] for binding in manifest["public_outputs"]
    } == {"positive_result": "sum", "raw_result": "raw"}
    external = _external_inputs(graph, 1)
    assert _replay(manifest, external) == _graph_reference(graph, external)
    validate_bounded_dag_artifacts(artifacts, *inputs)
