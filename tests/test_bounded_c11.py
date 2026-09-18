"""Pure public API and hostile-data tests; these are not native C execution."""

import json
import re
import struct
from dataclasses import fields, replace
from hashlib import sha256
from types import MappingProxyType

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_c11_codegen import (
    C11GraphSpec,
    C11OperationSpec,
    emit_checked_graph,
    validate_spec,
)
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import (
    BoundedC11Entrypoint,
    emit_bounded_c11_entrypoint,
    validate_bounded_c11_entrypoint,
)
from tuc.compiler.bounded_source import BoundedBackendBinding, compile_bounded_source_intent
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def source(name="entrypoint_test", *, reverse=False):
    returns = (SourceIntentReturn("z_raw", "raw"), SourceIntentReturn("a_positive", "positive"))
    return SourceIntentModule(
        name,
        tuple(SourceIntentTensor(name, shape) for name, shape in (
            ("a", (2, 3)), ("b", (3, 4)), ("product", (2, 4)), ("relu", (2, 4)),
            ("raw", (2,)), ("positive", (2,)),
        )),
        (
            SourceIntentOperation("project", "matmul", ("a", "b"), ("product",)),
            SourceIntentOperation("activate", "elementwise", ("product",), ("relu",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("raw_rows", "reduction", ("product",), ("raw",),
                                  attributes={"axis": 1}),
            SourceIntentOperation("positive_rows", "reduction", ("relu",), ("positive",),
                                  attributes={"axis": 1}),
        ), returns=returns[::-1] if reverse else returns,
    )


def cpu(*, preferred=False):
    kinds = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
    return BoundedBackendBinding(BackendCapability(
        "cpu", kinds, preferred_for=kinds if preferred else frozenset(),
        memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11)


def gpu():
    return BoundedBackendBinding(BackendCapability(
        "gpu", frozenset({OperationKind.MATMUL}), memory_domain=MemoryDomainKind.UNKNOWN),
        DAGTarget.CUDA_SM86)


def compile_source(module=None, bindings=None):
    module = source() if module is None else module
    bindings = (cpu(),) if bindings is None else bindings
    result = compile_bounded_source_intent(module, bindings)
    artifact = emit_bounded_c11_entrypoint(module, bindings, result)
    return module, bindings, result, artifact


def corrupt(value, **changes):
    altered = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(altered, field.name, changes.get(field.name, getattr(value, field.name)))
    return altered


def simple_spec():
    return C11GraphSpec(((2, 3), (3, 2), (2, 2), (2,)),
                        (C11OperationSpec("matmul", (0, 1), 2),
                         C11OperationSpec("sum_axis1", (2,), 3)), (0, 1), (3,))


def test_public_artifact_is_inert_deterministic_and_bound_to_original_compilation():
    module, bindings, compilation, artifact = compile_source()
    validate_bounded_c11_entrypoint(module, bindings, compilation, artifact)
    assert artifact == emit_bounded_c11_entrypoint(module, bindings, compilation)
    files = artifact.files()
    assert set(files) == {"entrypoint.h", "entrypoint.c", "entrypoint.json"}
    files.clear()
    assert len(artifact.files()) == 3
    manifest = json.loads(artifact.manifest_json)
    assert manifest["native_execution_observed"] is False
    assert manifest["normal_runtime_admission"] is False
    assert manifest["latency_ns"] is manifest["energy_pj"] is None
    assert manifest["scratch_bytes"] == 152
    assert manifest["scalar_work"] == 72
    assert manifest["source_intent_digest"] == compilation.source_intent_digest
    assert manifest["backend_bindings_digest"] == compilation.backend_bindings_digest
    for name in ("entrypoint.c", "entrypoint.h"):
        assert manifest["source_digests"][name] == sha256(
            artifact.files()[name].encode()).hexdigest()
    assert artifact.entrypoint_symbol == "tuc_c11_" + manifest["binding_digest"] + "_run"
    assert re.fullmatch(r"tuc_c11_[0-9a-f]{64}_run", artifact.entrypoint_symbol)


def test_public_output_order_controls_publication_and_namespace():
    first = compile_source()[-1]
    second = compile_source(source(reverse=True))[-1]
    left, right = json.loads(first.manifest_json), json.loads(second.manifest_json)
    assert [item["public_name"] for item in left["outputs"]] == ["z_raw", "a_positive"]
    assert [item["tensor_name"] for item in right["outputs"]] == ["positive", "raw"]
    assert first.entrypoint_symbol != second.entrypoint_symbol
    assert "memcpy(out[0].data, tensor_4, sizeof(tensor_4));" in first.source
    assert "memcpy(out[0].data, tensor_5, sizeof(tensor_5));" in second.source


def test_two_graph_headers_share_only_common_abi_and_have_unique_exported_symbols():
    first = compile_source()[-1]
    second = compile_source(source("another_graph"))[-1]
    assert first.entrypoint_symbol != second.entrypoint_symbol
    for artifact in (first, second):
        assert "#ifndef TUC_C11_ABI_V0" in artifact.header
        assert artifact.source.startswith('#include "entrypoint.h"')
        assert "#define TUC_C11_INPUT_COUNT" not in artifact.header
        assert artifact.entrypoint_symbol in artifact.header
        assert artifact.entrypoint_symbol in artifact.source
        assert "extern \"C\"" in artifact.header
    guards = [re.search(r"#ifndef (\w+)", item.header).group(1) for item in (first, second)]
    assert guards[0] != guards[1]


def test_unused_gpu_binding_allowed_but_selected_gpu_rejected():
    module, bindings, result, artifact = compile_source(bindings=(gpu(), cpu(preferred=True)))
    validate_bounded_c11_entrypoint(module, bindings, result, artifact)
    host_only = compile_source(module, (cpu(preferred=True),))[-1]
    assert artifact.entrypoint_symbol != host_only.entrypoint_symbol
    changed = replace(gpu(), capability=replace(gpu().capability,
                                               preferred_for=frozenset({OperationKind.MATMUL})))
    bindings = (cpu(), changed)
    mixed = compile_bounded_source_intent(module, bindings)
    with pytest.raises(ValueError, match="CPU"):
        emit_bounded_c11_entrypoint(module, bindings, mixed)


def test_binding_order_does_not_change_artifact():
    first = compile_source(bindings=(gpu(), cpu(preferred=True)))[-1]
    second = compile_source(bindings=(cpu(preferred=True), gpu()))[-1]
    assert first == second


@pytest.mark.parametrize("field", ("header", "source", "manifest_json", "entrypoint_symbol"))
def test_each_artifact_field_is_revalidated(field):
    module, bindings, compilation, artifact = compile_source()
    altered = corrupt(artifact, **{field: getattr(artifact, field) + " "})
    with pytest.raises(ValueError):
        validate_bounded_c11_entrypoint(module, bindings, compilation, altered)


class Hook:
    def __iter__(self):
        raise AssertionError("caller iteration invoked")

    def __eq__(self, other):
        raise AssertionError("caller equality invoked")


class HookString(str):
    def encode(self, *args, **kwargs):
        raise AssertionError("caller encoding invoked")


@pytest.mark.parametrize("bad", (None, False, 0, [], {}, Hook(), HookString("text"),
                                "\ud800", "x" * 262145), ids=map(str, range(9)))
@pytest.mark.parametrize("field", ("header", "source", "manifest_json", "entrypoint_symbol"))
def test_artifact_revalidation_rejects_nondata_and_budget_before_hooks(field, bad):
    module, bindings, compilation, artifact = compile_source()
    altered = corrupt(artifact, **{field: bad})
    with pytest.raises(ValueError):
        validate_bounded_c11_entrypoint(module, bindings, compilation, altered)


def test_extra_artifact_method_and_mutated_compiler_metadata_reject_without_dispatch():
    module, bindings, compilation, artifact = compile_source()
    object.__setattr__(artifact, "files", Hook())
    with pytest.raises(ValueError):
        validate_bounded_c11_entrypoint(module, bindings, compilation, artifact)
    object.__setattr__(compilation.compilation.hac_ir.graph, "metadata", {"malicious": Hook()})
    with pytest.raises(ValueError):
        emit_bounded_c11_entrypoint(module, bindings, compilation)


def test_result_nested_mapping_proxy_cannot_dispatch_custom_mapping():
    class HookDict(dict):
        def __iter__(self):
            raise AssertionError("caller iteration invoked")

    module, bindings, compilation, _ = compile_source()
    object.__setattr__(compilation.compilation.hac_ir.graph, "metadata",
                       MappingProxyType(HookDict()))
    with pytest.raises(ValueError):
        emit_bounded_c11_entrypoint(module, bindings, compilation)


def test_artifact_class_subclasses_are_not_data():
    class Derived(BoundedC11Entrypoint):
        def __eq__(self, other):
            raise AssertionError("caller equality invoked")

    module, bindings, compilation, artifact = compile_source()
    altered = Derived(artifact.header, artifact.source, artifact.manifest_json,
                      artifact.entrypoint_symbol)
    with pytest.raises(ValueError):
        validate_bounded_c11_entrypoint(module, bindings, compilation, altered)


def test_source_and_compilation_drift_rejected_before_emission():
    module, bindings, compilation, artifact = compile_source()
    with pytest.raises(ValueError):
        emit_bounded_c11_entrypoint(source("changed"), bindings, compilation)
    with pytest.raises(ValueError):
        validate_bounded_c11_entrypoint(module, bindings, Hook(), artifact)
    with pytest.raises(ValueError):
        emit_bounded_c11_entrypoint(module, bindings, corrupt(compilation, output_bindings=()))


def test_wrapper_validates_parameters_before_payloads_and_publishes_only_after_checks():
    artifact = compile_source()[-1]
    body = artifact.source.split("enum tuc_c11_status " + artifact.entrypoint_symbol, 1)[1]
    payload = body.index("tuc_normal(&in[0].data[i])")
    assert body.index("input_count != 2U") < body.index("memcpy(in, inputs") < payload
    assert body.index("tuc_overlap(ranges[i], ranges[j])") < payload
    assert body.index("_mm_getcsr()") < payload
    assert body.index("(csr & 0xe040U)") < payload
    assert body.index("(csr & 0x1f80U) != 0x1f80U") < payload
    publication = body.index("memcpy(out[0].data")
    assert body.rindex("return TUC_C11_NUMERIC") < publication
    assert body.rindex("return TUC_C11_ARGUMENT") < publication
    assert body.rindex("return TUC_C11_ENVIRONMENT") < publication
    assert body[publication:].count("return ") == 1
    assert "UINTPTR_MAX - bytes" in artifact.source
    assert "malloc(" not in artifact.source
    assert "tuc_dag_op_" not in artifact.source


def test_each_primitive_checks_arithmetic_intermediates():
    text = compile_source()[-1].source
    multiply = text.split("static int tuc_multiply", 1)[1].split("static int tuc_op_0", 1)[0]
    assert "volatile float rounded = left * right;" in multiply
    assert "if (!tuc_normal(&value)" in multiply
    assert "(lbits & UINT32_C(0x7fffffff)) != 0U" in multiply
    assert "(rbits & UINT32_C(0x7fffffff)) != 0U" in multiply
    assert multiply.index("if (!tuc_normal(&value)") < multiply.index("*output = value")
    add = text.split("static int tuc_add", 1)[1].split("static int tuc_multiply", 1)[0]
    assert "volatile float rounded = left + right;" in add
    assert add.index("if (!tuc_normal(&value)") < add.index("*output = value")
    matmul = text.split("static int tuc_op_0", 1)[1].split("static int tuc_op_1", 1)[0]
    assert matmul.index("!tuc_multiply") < matmul.index("!tuc_add") < matmul.index("out[i] = sum")
    assert "a0[(i / 4U) * 3U + k]" in matmul
    assert "a1[k * 4U + i % 4U]" in matmul


@pytest.mark.parametrize("rank", (1, 2))
def test_relu_only_has_no_unused_arithmetic_helpers(rank):
    shape = (3,) if rank == 1 else (2, 3)
    spec = C11GraphSpec((shape, shape), (C11OperationSpec("relu", (0,), 1),), (0,), (1,))
    _, text, _ = emit_checked_graph(spec, "a" * 64)
    assert "static int tuc_add" not in text
    assert "static int tuc_multiply" not in text


@pytest.mark.parametrize("bad", (None, [], (), (True,), (0,), (65,), (1, 2, 3), (1.0,),
                                (Hook(),), Hook()))
def test_private_emitter_rejects_malformed_shapes(bad):
    with pytest.raises(ValueError):
        emit_checked_graph(replace(simple_spec(), tensor_shapes=(bad, (3, 2), (2, 2), (2,))),
                           "a" * 64)


@pytest.mark.parametrize("bad", (None, [], (True,), (9,), (Hook(),), (), (0, 0), "01"))
def test_private_emitter_rejects_invalid_boundary(bad):
    with pytest.raises(ValueError):
        emit_checked_graph(replace(simple_spec(), input_tensors=bad), "a" * 64)


@pytest.mark.parametrize("changes", (
    {"kind": Hook()}, {"kind": "other"}, {"inputs": [0, 1]}, {"inputs": (True, 1)},
    {"inputs": (0,)}, {"output": True}, {"output": -1}, {"output": 4}, {"output": 0},
    {"inputs": (3, 1)}, {"inputs": (1, 0)},
))
def test_private_emitter_rejects_invalid_operation(changes):
    spec = simple_spec()
    altered = corrupt(spec.operations[0], **changes)
    with pytest.raises(ValueError):
        emit_checked_graph(replace(spec, operations=(altered, spec.operations[1])), "a" * 64)


@pytest.mark.parametrize("digest", (None, True, Hook(), HookString("a" * 64), "a" * 63,
                                   "a" * 65, "A" * 64, '"' * 64, "g" * 64),
                         ids=map(str, range(9)))
def test_private_emitter_never_accepts_c_source_names_or_fragments(digest):
    with pytest.raises(ValueError):
        emit_checked_graph(simple_spec(), digest)


def test_private_emitter_rejects_shadowed_methods_ssa_and_budgets():
    spec = simple_spec()
    object.__setattr__(spec, "anything", Hook())
    with pytest.raises(ValueError):
        validate_spec(spec)
    spec = simple_spec()
    with pytest.raises(ValueError):
        validate_spec(replace(spec, operations=spec.operations[::-1]))
    with pytest.raises(ValueError):
        validate_spec(replace(spec, operations=(spec.operations[0], spec.operations[0])))
    with pytest.raises(ValueError):
        validate_spec(replace(spec, output_tensors=(2,)))
    with pytest.raises(ValueError):
        validate_spec(replace(spec, tensor_shapes=(*spec.tensor_shapes, (1,))))
    large = C11GraphSpec(((64, 64),) * 4,
                         (C11OperationSpec("matmul", (0, 1), 2),
                          C11OperationSpec("matmul", (2, 1), 3)), (0, 1), (3,))
    with pytest.raises(ValueError):
        validate_spec(large)  # 1,048,576 scalar operations.


def test_declared_numeric_policy_covers_hidden_intermediate_failures():
    policy = json.loads(compile_source()[-1].manifest_json)["numeric_policy"]
    assert policy["every_rounded_product_and_sequential_sum_checked"] is True
    assert policy["nonzero_operands_product_rounding_to_zero_rejected"] is True
    # Independent binary32 examples explain the required guards. They do not
    # claim to execute or certify the emitted native code.
    f32 = lambda value: struct.unpack("<f", struct.pack("<f", value))[0]  # noqa: E731
    subnormal = f32(2.0 ** -126 * 0.5)
    assert 0 < subnormal < 2.0 ** -126
    assert f32(subnormal + 1.0) == 1.0  # A final-output-only check misses this.
    assert f32(2.0 ** -100 * 2.0 ** -100) == 0.0
    assert f32(1.0 + -1.0) == 0.0  # Exact cancellation remains allowed.
    close = f32(2.0 ** -126 + 2.0 ** -149)
    assert 0 < f32(close - 2.0 ** -126) < 2.0 ** -126
