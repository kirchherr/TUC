"""Decode generated C data without compiling or executing any native code."""

import json
import math
import re
import struct

import pytest

from examples import bounded_dag_c11 as oracle
from examples import bounded_dag_compiler as portfolio
from examples import bounded_dag_native as proof
from tuc.ir.model import OperationKind


def _initializer(source, declaration):
    match = re.search(re.escape(declaration) + r"\s*=\s*(\{.*?\});", source, re.S)
    assert match is not None
    return match[1]


def _integers(text):
    # A restricted data grammar, never eval or a compiler. The generated
    # arrays cannot smuggle identifiers, expressions or source fragments.
    assert re.fullmatch(r"[0-9U{},\s]+", text)
    return json.loads(text.replace("U", "").replace("{", "[").replace("}", "]"))


def _names(text):
    assert re.fullmatch(r"[a-zA-Z_0-9{},\s]+", text)
    quoted = re.sub(r"\b[A-Za-z_]\w*\b", lambda match: json.dumps(match[0]), text)
    return json.loads(quoted.replace("{", "[").replace("}", "]"))


@pytest.fixture(scope="module")
def data():
    rows = proof.bundles()
    bindings = proof._bindings(rows)
    graphs = _integers(_initializer(
        bindings, "const struct tuc_graph tuc_graphs[TUC_GRAPH_COUNT]"
    ))
    plans = _integers(_initializer(
        bindings, "const struct tuc_plan tuc_plans[TUC_PLAN_COUNT]"
    ))
    return rows, graphs, plans


def _source_tensors(family, shape):
    graph = portfolio.graph_for(family, shape)
    tensors = {}
    for operation in graph.operations:
        for tensor in (*operation.inputs, *operation.outputs):
            tensors.setdefault(tensor.name, tensor)
    return graph, list(tensors.values())


@pytest.mark.parametrize("index", range(12))
def test_c_graph_initializers_preserve_source_shapes_ports_and_launches(data, index):
    rows, graphs, plans = data
    assert len(graphs) == 12 and len(plans) == 36
    family, shape = rows[index * 3][:2]
    source, tensors = _source_tensors(family, shape)
    ids = {tensor.name: i for i, tensor in enumerate(tensors)}
    graph = graphs[index]
    count, op_count, input_count, output_count, tensor_rows, ops, inputs, outputs = graph
    assert count == len(tensors) and op_count == len(source.operations)
    assert tensor_rows == [[len(t.shape), t.shape[0], t.shape[1] if len(t.shape) == 2 else 1,
                            4 * math.prod(t.shape)] for t in tensors]
    kinds = {OperationKind.MATMUL: 0, OperationKind.ELEMENTWISE: 1,
             OperationKind.REDUCTION: 2}
    for actual, operation in zip(ops, source.operations, strict=True):
        assert actual == [kinds[operation.kind], ids[operation.inputs[0].name],
                          ids[operation.inputs[1].name] if len(operation.inputs) == 2 else 255,
                          ids[operation.outputs[0].name],
                          (math.prod(operation.outputs[0].shape) + 127) // 128, 128]
    produced = {t.name for op in source.operations for t in op.outputs}
    consumed = {t.name for op in source.operations for t in op.inputs}
    assert set(inputs[:input_count]) == {ids[name] for name in consumed - produced}
    assert set(outputs[:output_count]) == {ids[name] for name in produced - consumed}
    assert inputs[input_count:] == [255] * (3 - input_count)
    assert outputs[output_count:] == [255] * (2 - output_count)


@pytest.mark.parametrize("index", range(36))
def test_integer_plan_replay_checks_slots_copies_and_receipt_counters(data, index):
    rows, graphs, plans = data
    graph_id, profile, nbuffer, nevent, buffer_bytes, copy_bytes, targets, buffers, events = (
        plans[index]
    )
    assert (graph_id, profile) == (index // 3, index % 3)
    _, nops, ninputs, noutputs, tensors, ops, inputs, outputs = graphs[graph_id]
    assert targets == ([0] * nops if profile == 0 else [1] * nops if profile == 1 else
                       [int(op % 2 == 0) for op in range(nops)])
    assert nbuffer == len(buffers) <= 16 and nevent == len(events) <= 18
    assert buffer_bytes == sum(slot[2] for slot in buffers) <= 7432
    assert len({tuple(slot[:2]) for slot in buffers}) == nbuffer
    for tensor, space, size in buffers:
        assert space in (0, 1) and size == tensors[tensor][3]
    ready, bound, published = set(), set(), set()
    next_op = 0
    copied = 0
    counts = dict.fromkeys(proof.COUNTERS, 0)
    for kind, operation, target, input0, input1, output in events:
        if kind != 2:
            assert operation == target == 255
        if kind == 0:
            tensor, space, _ = buffers[output]
            assert input0 == input1 == 255 and output not in ready and space == 0
            assert tensor in inputs[:ninputs] and tensor not in bound
            bound.add(tensor)
        elif kind == 1:
            source, destination = buffers[input0], buffers[output]
            assert input0 in ready and input1 == 255 and output not in ready
            assert source[0] == destination[0] and source[2] == destination[2]
            assert source[1] != destination[1]
            copied += destination[2]
            direction = "download" if destination[1] == 0 else "upload"
            counts[direction + "_calls"] += 1
            counts[direction + "_bytes"] += destination[2]
        elif kind == 2:
            assert operation == next_op and target == targets[operation]
            op_kind, lhs, rhs, result, _, _ = ops[operation]
            assert input0 in ready and output not in ready
            assert buffers[input0][:2] == [lhs, target]
            assert buffers[output][:2] == [result, target]
            if op_kind == 0:
                assert input1 in ready and buffers[input1][:2] == [rhs, target]
            else:
                assert input1 == rhs == 255
            counts["cpu_calls" if target == 0 else "gpu_calls"] += 1
            if target == 1:
                counts["validation_download_calls"] += 1
                counts["validation_download_bytes"] += buffers[output][2]
            next_op += 1
        else:
            assert kind == 3 and next_op == nops
            assert input0 in ready and input1 == output == 255
            tensor, space, size = buffers[input0]
            assert space == 0 and tensor in outputs[:noutputs] and tensor not in published
            published.add(tensor)
            counts["published_outputs"] += 1
            counts["scalar_checks"] += size // 4
        if output != 255:
            ready.add(output)
    assert next_op == nops and ready == set(range(nbuffer))
    assert bound == set(inputs[:ninputs]) and published == set(outputs[:noutputs])
    assert copied == copy_bytes <= 2656
    counts["case_runs"] = 1
    receipt = proof.expected_receipt(index, "matrix", rows=rows)
    assert {key: value * 6 for key, value in counts.items()} == {
        key: receipt[key] for key in counts
    }


def test_corpus_pointer_tables_have_exact_extents_and_independent_reference_bits(data):
    rows, graphs, _ = data
    source = proof._corpora(rows)
    arrays = {}
    for name, contents in re.findall(
        r"static const uint32_t (tuc_\w+)\[\] = \{([^}]+)\};", source
    ):
        assert name not in arrays
        assert re.fullmatch(r"UINT32_C\(0x[0-9a-f]{8}\)(,UINT32_C\(0x[0-9a-f]{8}\))*", contents)
        arrays[name] = [int(value, 16) for value in re.findall(r"0x([0-9a-f]{8})", contents)]
    tables = _names(_initializer(source, "const struct tuc_corpus tuc_corpora[TUC_GRAPH_COUNT]"))
    assert len(tables) == 12
    referenced = set()
    for graph_id, table in enumerate(tables):
        family, shape = rows[3 * graph_id][:2]
        _, tensors = _source_tensors(family, shape)
        _, _, ninputs, noutputs, _, _, inputs, outputs = graphs[graph_id]
        assert len(table) == 2
        for group_id, vectors in enumerate(table):
            ids = inputs[:ninputs] if group_id == 0 else outputs[:noutputs]
            assert len(vectors) == 3
            for vector, names in enumerate(vectors):
                values = (oracle.fixed_inputs(shape, vector) if group_id == 0 else
                          oracle.reference_outputs(family, shape, vector))
                assert len(names) == 10
                for tensor_id, name in enumerate(names):
                    if tensor_id not in ids:
                        assert name == "NULL"
                        continue
                    assert name in arrays and name not in referenced
                    referenced.add(name)
                    tensor = tensors[tensor_id]
                    expected = [struct.unpack("<I", struct.pack("<f", value))[0]
                                for value in values[tensor.name]]
                    assert len(arrays[name]) == math.prod(tensor.shape)
                    assert arrays[name] == expected
    assert referenced == set(arrays)
