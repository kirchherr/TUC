"""Bounded Softmax source/JSON/compiler admission; no native execution."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

import tuc.bounded_cpu_application_cli as cli
import tuc.compiler.bounded_source as source
from integration.bounded_cpu_batch import consumer as batch_consumer
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_json import BoundedCPUJSONError, source_intent_from_json
from tuc.compiler.bounded_cpu_source import (
    _SECURITY,
    WORKER_PROTOCOL,
    decode_source_response,
    prepare_source_request,
)
from tuc.frontend.source_intent_intake import source_intent_from_mapping
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def graph(shape=(2, 3)):
    return {"schema_version": "source_intent.v0", "name": "caller_softmax",
            "tensors": [{"name": "x", "shape": list(shape)},
                        {"name": "y", "shape": list(shape)}],
            "operations": [{"name": "normalize", "family": "softmax", "inputs": ["x"],
                            "outputs": ["y"], "attributes": {"axis": 1}}],
            "returns": [{"public_name": "probabilities", "tensor_name": "y",
                         "required": True}]}


def composed(family):
    if family == "classifier":
        tensors = {"x": (2, 3), "w": (4, 3), "b": (4,), "projected": (2, 4),
                   "logits": (2, 4), "y": (2, 4)}
        operations = [
            ("project", "matmul", ["x", "w"], "projected", {"rhs_transposed": True}),
            ("bias", "elementwise", ["projected", "b"], "logits", {"elementwise_kind": "add"}),
            ("normalize", "softmax", ["logits"], "y", {"axis": 1}),
        ]
    else:
        tensors = {"q": (2, 3), "k": (4, 3), "v": (4, 5), "scores": (2, 4),
                   "probabilities": (2, 4), "y": (2, 5)}
        operations = [
            ("scores", "matmul", ["q", "k"], "scores", {"rhs_transposed": True}),
            ("normalize", "softmax", ["scores"], "probabilities", {"axis": 1}),
            ("mix", "matmul", ["probabilities", "v"], "y", {}),
        ]
    return {"schema_version": "source_intent.v0", "name": family,
            "tensors": [{"name": name, "shape": list(shape)} for name, shape in tensors.items()],
            "operations": [{"name": name, "family": kind, "inputs": inputs,
                            "outputs": [output], "attributes": attributes}
                           for name, kind, inputs, output, attributes in operations],
            "returns": [{"public_name": "result", "tensor_name": "y", "required": True}]}


def module(document=None):
    return source_intent_from_json(json.dumps(graph() if document is None else document).encode())


@pytest.mark.parametrize("shape", [(1, 1), (1, 7), (5, 1), (2, 3), (64, 64)])
def test_typed_and_json_softmax_emit_identical_artifacts_and_exact_work(shape):
    document = graph(shape)
    typed = source_intent_from_mapping(document)
    decoded = module(document)
    assert decoded == typed
    bindings = cli.cpu_bindings(softmax=True)
    first = source.compile_bounded_source_intent(typed, bindings)
    second = source.compile_bounded_source_intent(decoded, bindings)
    assert first == second
    source.validate_bounded_source_compilation(decoded, bindings, first)
    manifest = json.loads(first.artifacts.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_softmax_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "softmax_axis1"
    assert manifest["scalar_work"] == 5 * shape[0] * shape[1]
    assert first.input_bindings[0].shape == shape
    assert first.output_bindings[0].shape == shape
    assert first.output_bindings[0].public_name == "probabilities"
    assert first.compilation.hac_ir.graph.operations[0].kind is OperationKind.SOFTMAX
    assert first.compilation.hac_ir.graph.operations[0].attributes["axis"] == 1
    assert len(prepare_bounded_c11_application(decoded, bindings).program_digest) == 64


@pytest.mark.parametrize("family,kinds,work", [
    ("classifier", ["matmul_rhs_transposed", "add_row_bias", "softmax_axis1"], 96),
    ("attention", ["matmul_rhs_transposed", "softmax_axis1", "matmul"], 168),
])
def test_composition_preserves_existing_operations_and_prioritizes_softmax(family, kinds, work):
    compiled = source.compile_bounded_source_intent(module(composed(family)),
                                                     cli.cpu_bindings(softmax=True))
    manifest = json.loads(compiled.artifacts.manifest_json)
    assert [op["kind"] for op in manifest["operations"]] == kinds
    assert manifest["scalar_work"] == work
    assert all(op["target"] == "c11" for op in manifest["operations"])
    assert len(compiled.output_bindings) == 1
    assert compiled.output_bindings[0].public_name == "result"


@pytest.mark.parametrize("axis", [None, True, False, 0, -1, 2, 1.0, "1", [], {}, 10**100])
def test_json_axis_is_exact_canonical_integer_one(axis):
    document = graph()
    document["operations"][0]["attributes"]["axis"] = axis
    with pytest.raises(BoundedCPUJSONError, match="graph_json_rejected"):
        module(document)


@pytest.mark.parametrize("mutation", [
    "rank1", "rank3", "mismatch", "dtype", "bool-dimension", "large-dimension",
    "empty-input", "two-inputs", "two-outputs", "inplace", "missing-axis", "extra-attribute",
    "backend-hint", "optional-return", "wrong-return", "unused-tensor",
])
def test_json_rejects_invalid_softmax_contract(mutation):
    document = graph()
    op = document["operations"][0]
    if mutation in {"rank1", "rank3"}:
        shape = [3] if mutation == "rank1" else [1, 2, 3]
        for tensor in document["tensors"]:
            tensor["shape"] = shape
    elif mutation in {"mismatch", "bool-dimension", "large-dimension"}:
        document["tensors"][1]["shape"] = {
            "mismatch": [3, 2], "bool-dimension": [True, 3], "large-dimension": [65, 3],
        }[mutation]
    elif mutation == "dtype":
        document["tensors"][0]["dtype"] = "float64"
    elif mutation in {"empty-input", "two-inputs"}:
        op["inputs"] = [] if mutation == "empty-input" else ["x", "x"]
    elif mutation == "two-outputs":
        op["outputs"] = ["y", "y"]
    elif mutation == "inplace":
        op["outputs"] = ["x"]
    elif mutation == "missing-axis":
        op["attributes"] = {}
    elif mutation == "extra-attribute":
        op["attributes"]["elementwise_kind"] = "relu"
    elif mutation == "backend-hint":
        op["hints"] = {"backend": "cuda"}
    elif mutation == "optional-return":
        document["returns"][0]["required"] = False
    elif mutation == "wrong-return":
        document["returns"][0]["tensor_name"] = "x"
    else:
        document["tensors"].append({"name": "unused", "shape": [2, 3]})
    with pytest.raises(BoundedCPUJSONError):
        module(document)


@pytest.mark.parametrize("attribute", [True, 1.0, "1", None, [], {}])
def test_typed_malformed_axis_rejects_before_planner(monkeypatch, attribute):
    value = module()
    object.__setattr__(value.operations[0], "attributes", {"axis": attribute})
    monkeypatch.setattr(source, "compile_graph", lambda *a, **k: pytest.fail("planner called"))
    with pytest.raises(ValueError):
        source.compile_bounded_source_intent(value, cli.cpu_bindings(softmax=True))


def test_hostile_metadata_proxy_is_rejected_without_mapping_hooks(monkeypatch):
    calls = []
    class Hostile(dict):
        def __iter__(self):
            calls.append("iter")
            raise AssertionError

        def __len__(self):
            calls.append("len")
            raise AssertionError

        def items(self):
            calls.append("items")
            raise AssertionError
    value = module()
    object.__setattr__(value.operations[0], "attributes", MappingProxyType(Hostile(axis=1)))
    monkeypatch.setattr(source, "compile_graph", lambda *a, **k: pytest.fail("planner called"))
    with pytest.raises(ValueError):
        source.compile_bounded_source_intent(value, cli.cpu_bindings(softmax=True))
    assert calls == []


def test_logical_work_budget_includes_softmax_before_planning(monkeypatch):
    # Matmuls alone cost 999424 units; Softmax takes the graph over one million.
    document = composed("attention")
    shapes = {"q": [64, 64], "k": [61, 64], "v": [61, 64], "scores": [64, 61],
              "probabilities": [64, 61], "y": [64, 64]}
    for tensor in document["tensors"]:
        tensor["shape"] = shapes[tensor["name"]]
    value = source_intent_from_mapping(document)
    monkeypatch.setattr(source, "compile_graph", lambda *a, **k: pytest.fail("planner called"))
    with pytest.raises(ValueError):
        source.compile_bounded_source_intent(value, cli.cpu_bindings(softmax=True))


def test_softmax_requires_explicit_capability_without_fallback(monkeypatch):
    monkeypatch.setattr(source, "compile_graph", lambda *a, **k: pytest.fail("planner called"))
    with pytest.raises(ValueError):
        source.compile_bounded_source_intent(module(), cli.cpu_bindings())


def test_cuda_softmax_target_rejects_without_cpu_fallback():
    binding = cli.cpu_bindings(softmax=True)[0]
    cuda = replace(binding, target=DAGTarget.CUDA_SM86,
                   capability=replace(binding.capability, memory_domain=MemoryDomainKind.UNKNOWN))
    with pytest.raises(ValueError):
        source.compile_bounded_source_intent(module(), (cuda,))


@pytest.mark.parametrize("flag", [0, 1, None, "true", [], {}])
def test_cli_binding_selection_rejects_nonboolean_flags(flag):
    with pytest.raises(ValueError):
        cli.cpu_bindings(softmax=flag)


def test_existing_cli_bindings_are_unchanged():
    assert cli.cpu_bindings() == cli.cpu_bindings(softmax=False)
    legacy = cli.cpu_bindings()[0]
    extended = cli.cpu_bindings(softmax=True)[0]
    assert legacy.capability.supported_ops == frozenset({
        OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
    assert replace(extended.capability, supported_ops=legacy.capability.supported_ops) == (
        legacy.capability)


@pytest.mark.parametrize("softmax", [False, True])
def test_cli_inspect_selects_only_validated_graphs_capability(monkeypatch, softmax):
    document = graph()
    if not softmax:
        document["operations"][0].update(family="elementwise",
                                          attributes={"elementwise_kind": "relu"})
    original = cli.cpu_bindings
    calls = []
    def selected(*, softmax=False):
        calls.append(softmax)
        return original(softmax=softmax)
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    monkeypatch.setattr(cli, "_read_file", lambda *a: json.dumps(document).encode())
    monkeypatch.setattr(cli, "cpu_bindings", selected)
    result = json.loads(cli._execute("inspect", "synthetic.json", None, None))
    assert calls == [softmax]
    assert result["native_execution_observed"] is False


def test_source_parser_result_crosses_unchanged_synthetic_protocol():
    """Owned literal and synthetic security claims; no OCI observation is made."""
    text = ("import triton\nimport triton.language as tl\n@triton.jit\n"
            "def normalized(x, y):\n    p = tl.softmax(x, axis=1)\n    tl.store(y, p)\n")
    signature = {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "normalizer",
                 "kernel_name": "normalized", "tensor_shapes": {"x": [2, 3], "y": [2, 3]}}
    request = prepare_source_request(text.encode(), json.dumps(signature).encode())
    parsed = ingest_triton_module_source_to_source_intent(
        text, source_name="normalizer", kernel_name="normalized",
        tensor_shapes={"x": (2, 3), "y": (2, 3)})
    response = {"protocol": WORKER_PROTOCOL, "status": "accepted",
                "request_digest": json.loads(request)["request_digest"],
                "security": dict(_SECURITY),
                "source_intent_payload": parsed.parser_result.source_intent_payload,
                "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                    parsed.report)}
    decoded = decode_source_response(request, json.dumps(response).encode())
    assert source_intent_from_json(decoded) == parsed.parser_result.module


@pytest.mark.parametrize("index", range(6))
def test_observed_pre_softmax_program_ids_remain_identical(index):
    """Pure reconstruction of retained IDs, not repetition of native observations."""
    path = Path(__file__).resolve().parents[1] / "docs/evidence/bounded-cpu-batch-35609641378.json"
    recorded = json.loads(path.read_bytes())["integration"]["programs"][index]
    document = batch_consumer.graph(recorded["family"], recorded["profile"])
    application = prepare_bounded_c11_application(module(document), cli.cpu_bindings())
    assert application.program_digest == recorded["program_digest"]


def test_json_key_reordering_does_not_change_softmax_compilation():
    document = graph()
    reordered = dict(reversed(list(copy.deepcopy(document).items())))
    first = source.compile_bounded_source_intent(module(document), cli.cpu_bindings(softmax=True))
    second = source.compile_bounded_source_intent(module(reordered), cli.cpu_bindings(softmax=True))
    assert first == second
