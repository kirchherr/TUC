"""Behavior and hostile-data tests for the public Source Intent compiler."""

from dataclasses import fields, replace
from types import MappingProxyType

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_source as api
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage


def altered(value, **changes):
    """Model corrupted frozen input without running its constructor first."""
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(value, field.name)))
    return result


def source():
    return SourceIntentModule(
        "public_branch",
        tuple(
            SourceIntentTensor(name, shape)
            for name, shape in (
                ("a", (3, 2)),
                ("b", (2, 4)),
                ("p", (3, 4)),
                ("r", (3, 4)),
                ("y", (3,)),
                ("z", (3,)),
            )
        ),
        (
            SourceIntentOperation("project", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation(
                "activate",
                "elementwise",
                ("p",),
                ("r",),
                attributes={"elementwise_kind": "relu"},
            ),
            SourceIntentOperation("raw_sum", "reduction", ("p",), ("y",), attributes={"axis": 1}),
            SourceIntentOperation("relu_sum", "reduction", ("r",), ("z",), attributes={"axis": 1}),
        ),
        returns=(SourceIntentReturn("positive", "z"), SourceIntentReturn("raw", "y")),
    )


def cpu(name="cpu"):
    return api.BoundedBackendBinding(
        BackendCapability(
            name,
            frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}),
            memory_domain=MemoryDomainKind.HOST_RAM,
        ),
        DAGTarget.C11,
    )


def gpu():
    return api.BoundedBackendBinding(
        BackendCapability(
            "gpu",
            frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.UNKNOWN,
        ),
        DAGTarget.CUDA_SM86,
    )


def test_public_compilation_preserves_intent_aliases_and_explains_placement():
    module = source()
    host = api.compile_bounded_source_intent(module, (cpu(),))
    mixed = api.compile_bounded_source_intent(module, (cpu(), gpu()))
    assert host.compilation.dump(IRStage.HAC_IR) == mixed.compilation.dump(IRStage.HAC_IR)
    assert host.artifacts.c11_source == mixed.artifacts.c11_source
    assert host.artifacts.cuda_source == mixed.artifacts.cuda_source
    assert host.source_intent_digest == mixed.source_intent_digest
    assert host.backend_bindings_digest != mixed.backend_bindings_digest
    assert tuple(b.public_name for b in mixed.output_bindings) == ("positive", "raw")
    assert tuple(b.tensor_name for b in mixed.output_bindings) == ("z", "y")
    assert tuple(b.tensor_name for b in mixed.input_bindings) == ("a", "b")
    plan = mixed.compilation.partition_plan
    assert tuple(a.backend_name for a in plan.assignments) == ("gpu", "cpu", "cpu", "cpu")
    assert all(not a.reason.startswith("fallback:") for a in plan.assignments)
    assert plan.override_effects == ()
    assert plan.candidate_scores
    assert "preferred_for:matmul" in mixed.compilation.dump_decision_report()
    assert plan.total_transfer_bytes() > 0
    api.validate_bounded_source_compilation(module, (cpu(), gpu()), mixed)


def test_unused_capability_is_bound_but_not_emitted_as_selected_target():
    module = source()
    secondary = altered(
        gpu(),
        capability=replace(
            gpu().capability,
            preferred_for=frozenset(),
        ),
    )
    # Give CPU an explicit preference for every accepted operation.
    primary = altered(
        cpu(),
        capability=replace(
            cpu().capability,
            preferred_for=cpu().capability.supported_ops,
        ),
    )
    result = api.compile_bounded_source_intent(module, (primary, secondary))
    assert {a.backend_name for a in result.compilation.partition_plan.assignments} == {"cpu"}
    drift = altered(secondary, capability=replace(secondary.capability, name="other_gpu"))
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(module, (primary, drift), result)


def test_deterministic_recompile_and_independent_returned_artifact_mapping():
    first = api.compile_bounded_source_intent(source(), (cpu(), gpu()))
    second = api.compile_bounded_source_intent(source(), (cpu(), gpu()))
    assert first == second
    data = first.artifacts.files()
    data["generated.c"] = "changed"
    assert first.artifacts == second.artifacts


def test_non_alphabetic_public_return_order_survives_frontend_alias_sorting():
    module = replace(
        source(),
        returns=(
            SourceIntentReturn("z_first", "z"),
            SourceIntentReturn("a_second", "y"),
        ),
    )
    result = api.compile_bounded_source_intent(module, (cpu(),))
    assert tuple(b.public_name for b in result.output_bindings) == ("z_first", "a_second")
    assert tuple(b.tensor_name for b in result.output_bindings) == ("z", "y")
    api.validate_bounded_source_compilation(module, (cpu(),), result)


def test_capability_order_is_canonical():
    module = source()
    left = api.compile_bounded_source_intent(module, (cpu(), gpu()))
    right = api.compile_bounded_source_intent(module, (gpu(), cpu()))
    assert left == right
    api.validate_bounded_source_compilation(module, (gpu(), cpu()), left)


def fail_if_called(*args, **kwargs):
    raise AssertionError("untrusted input reached a method or later compiler stage")


def before_adapter(monkeypatch):
    monkeypatch.setattr(api, "source_intent_to_triton_metadata", fail_if_called)
    monkeypatch.setattr(api, "compile_graph", fail_if_called)
    monkeypatch.setattr(api, "lower_bounded_dag", fail_if_called)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "x" * 65),
        ("name", "../../source"),
        ("name", "bad\nsource"),
        ("contract", "unknown"),
        ("tensors", []),
        ("tensors", ()),
        ("operations", []),
        ("operations", ()),
        ("returns", ()),
        ("returns", []),
    ],
)
def test_module_boundary_rejects_before_adapter(monkeypatch, field, value):
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(altered(source(), **{field: value}), (cpu(),))


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "x" * 65),
        ("shape", (True, 2)),
        ("shape", (0, 2)),
        ("shape", (65, 2)),
        ("shape", (2, 2, 2)),
        ("shape", [3, 2]),
        ("dtype", "float64"),
        ("dtype", object()),
    ],
)
def test_tensor_boundary_rejects_before_adapter(monkeypatch, field, value):
    module = source()
    bad = altered(module.tensors[0], **{field: value})
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(
            altered(module, tensors=(bad, *module.tensors[1:])), (cpu(),)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "x" * 65),
        ("family", "softmax"),
        ("family", "unknown"),
        ("inputs", []),
        ("inputs", ("a",)),
        ("inputs", ("a", "missing")),
        ("outputs", ()),
        ("outputs", ("p", "r")),
        ("outputs", ("a",)),
        ("attributes", MappingProxyType({"transposed": True})),
        ("attributes", MappingProxyType({"axis": 1})),
        ("hints", MappingProxyType({"max_error_budget": float("inf")})),
        ("hints", MappingProxyType({"max_error_budget": True})),
        ("hints", MappingProxyType({"max_error_budget": 1 << 4096})),
        ("hints", MappingProxyType({"robust_to_noise": 1})),
        ("hints", MappingProxyType({"command": "ignored?"})),
    ],
)
def test_operation_boundary_rejects_before_adapter(monkeypatch, field, value):
    module = source()
    bad = altered(module.operations[0], **{field: value})
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(
            altered(module, operations=(bad, *module.operations[1:])), (cpu(),)
        )


@pytest.mark.parametrize(
    "index,attributes",
    [
        (1, {}),
        (1, {"elementwise_kind": "identity"}),
        (1, {"elementwise_kind": "gelu"}),
        (1, {"elementwise_kind": "relu", "axis": 1}),
        (2, {}),
        (2, {"axis": True}),
        (2, {"axis": 0}),
        (2, {"axis": -1}),
    ],
)
def test_only_explicit_relu_and_axis_one_sum(monkeypatch, index, attributes):
    module = source()
    ops = list(module.operations)
    ops[index] = altered(ops[index], attributes=MappingProxyType(attributes))
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(altered(module, operations=tuple(ops)), (cpu(),))


@pytest.mark.parametrize(
    "returns",
    [
        (SourceIntentReturn("raw", "y"),),
        (SourceIntentReturn("raw", "y", required=False), SourceIntentReturn("positive", "z")),
        (SourceIntentReturn("raw", "y"), SourceIntentReturn("raw", "z")),
        (SourceIntentReturn("one", "y"), SourceIntentReturn("two", "y")),
        (SourceIntentReturn("raw", "p"), SourceIntentReturn("positive", "z")),
    ],
)
def test_returns_must_cover_terminals_once_and_be_required(monkeypatch, returns):
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(altered(source(), returns=returns), (cpu(),))


def test_forward_references_duplicate_definitions_and_dead_declarations(monkeypatch):
    module = source()
    before_adapter(monkeypatch)
    invalid = (
        altered(
            module, operations=(module.operations[1], module.operations[0], *module.operations[2:])
        ),
        altered(module, operations=(*module.operations, module.operations[0])),
        altered(module, tensors=(*module.tensors, SourceIntentTensor("unused", (2, 2)))),
        altered(module, tensors=(*module.tensors, module.tensors[0])),
        altered(module, operations=module.operations * 3),
        altered(module, tensors=module.tensors * 5),
    )
    for candidate in invalid:
        with pytest.raises(ValueError):
            api.compile_bounded_source_intent(candidate, (cpu(),))


def test_scalar_work_budget_is_checked_before_adapter(monkeypatch):
    module = SourceIntentModule(
        "large_work",
        tuple(SourceIntentTensor(n, (64, 64)) for n in ("a", "b", "p", "y")),
        (
            SourceIntentOperation("first", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation("second", "matmul", ("p", "b"), ("y",)),
        ),
        returns=(SourceIntentReturn("result", "y"),),
    )
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(module, (cpu(),))


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "x" * 65),
        ("name", "../cpu"),
        ("supported_ops", []),
        ("supported_ops", frozenset()),
        ("supported_ops", frozenset({"matmul"})),
        ("preferred_for", frozenset({"matmul"})),
        ("supports_noise_model", 1),
        ("supports_calibration", 0),
        ("max_error_budget", float("nan")),
        ("max_error_budget", float("inf")),
        ("max_error_budget", True),
        ("max_error_budget", 1 << 4096),
        ("memory_domain", MemoryDomainKind.GPU_HBM),
        ("memory_domain", "host_ram"),
        ("supported_layouts", frozenset()),
        ("supported_layouts", frozenset({"row_major"})),
        ("produced_layouts", frozenset()),
    ],
)
def test_capability_validation_precedes_planner(monkeypatch, field, value):
    binding = cpu()
    bad = altered(binding, capability=altered(binding.capability, **{field: value}))
    before_adapter(monkeypatch)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(source(), (bad,))


def test_binding_container_cardinality_identity_and_targets(monkeypatch):
    before_adapter(monkeypatch)
    for bindings in (
        [],
        (),
        [cpu()],
        (cpu(), cpu(), gpu()),
        (cpu(), cpu()),
        (cpu(), cpu("another")),
        (altered(cpu(), target="c11"),),
        (altered(cpu(), capability=object()),),
        (
            altered(
                gpu(), capability=replace(gpu().capability, memory_domain=MemoryDomainKind.GPU_HBM)
            ),
        ),
    ):
        with pytest.raises(ValueError):
            api.compile_bounded_source_intent(source(), bindings)


def test_capability_gap_cannot_fall_back_even_with_reference_cpu_name(monkeypatch):
    binding = altered(
        cpu("reference-cpu"),
        capability=replace(
            cpu("reference-cpu").capability,
            supported_ops=frozenset({OperationKind.MATMUL}),
        ),
    )
    monkeypatch.setattr(api, "lower_bounded_dag", fail_if_called)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(source(), (binding,))


class HookDict(dict):
    __len__ = fail_if_called
    __iter__ = fail_if_called
    __getitem__ = fail_if_called
    items = fail_if_called
    keys = fail_if_called
    get = fail_if_called


class HookTuple(tuple):
    __len__ = fail_if_called
    __iter__ = fail_if_called


def test_mapping_proxy_backing_must_be_plain_data_without_dispatch(monkeypatch):
    module = source()
    before_adapter(monkeypatch)
    for field in ("hints", "attributes"):
        op = altered(module.operations[0], **{field: MappingProxyType(HookDict())})
        with pytest.raises(ValueError):
            api.compile_bounded_source_intent(
                altered(module, operations=(op, *module.operations[1:])), (cpu(),)
            )
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(
            altered(module, operations=HookTuple(module.operations)), (cpu(),)
        )


def test_capability_instance_methods_are_not_dispatched():
    binding = cpu()
    object.__setattr__(binding.capability, "supports", fail_if_called)
    object.__setattr__(binding.capability, "produced_layout_for", fail_if_called)
    with pytest.raises(ValueError):
        api.compile_bounded_source_intent(source(), (binding,))


@pytest.mark.parametrize(
    "field",
    [
        "manifest_json",
        "c11_header",
        "c11_source",
        "cuda_source",
        "schedule_header",
    ],
)
def test_artifact_substitution_is_rejected(field):
    module, bindings = source(), (cpu(), gpu())
    result = api.compile_bounded_source_intent(module, bindings)
    artifacts = altered(result.artifacts, **{field: getattr(result.artifacts, field) + " "})
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(
            module, bindings, altered(result, artifacts=artifacts)
        )


@pytest.mark.parametrize("field", ["source_intent_digest", "backend_bindings_digest"])
def test_provenance_digest_substitution_is_rejected(field):
    module, bindings = source(), (cpu(),)
    result = api.compile_bounded_source_intent(module, bindings)
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(
            module, bindings, altered(result, **{field: "sha256:" + "0" * 64})
        )


def test_source_return_and_backend_claim_drift_are_rejected():
    module, bindings = source(), (cpu(),)
    result = api.compile_bounded_source_intent(module, bindings)
    for changed in (
        replace(module, name="other_source"),
        replace(module, returns=tuple(reversed(module.returns))),
    ):
        with pytest.raises(ValueError):
            api.validate_bounded_source_compilation(changed, bindings, result)
    changed_binding = altered(
        cpu(), capability=replace(cpu().capability, supports_calibration=True)
    )
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(module, (changed_binding,), result)


def test_mutable_compilation_and_io_drift_are_rejected():
    module, bindings = source(), (cpu(),)
    result = api.compile_bounded_source_intent(module, bindings)
    result.compilation.hac_ir.metadata["extra"] = "drift"
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(module, bindings, result)
    result = api.compile_bounded_source_intent(module, bindings)
    bad_output = altered(result.output_bindings[0], tensor_index=999)
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(
            module,
            bindings,
            altered(
                result,
                output_bindings=(bad_output, *result.output_bindings[1:]),
            ),
        )


def test_revalidator_rejects_hostile_nested_objects_without_comparison_hooks():
    class Hook:
        __eq__ = fail_if_called
        __repr__ = fail_if_called
        __str__ = fail_if_called

    module, bindings = source(), (cpu(),)
    for field in (
        "compilation",
        "artifacts",
        "input_bindings",
        "output_bindings",
        "source_intent_digest",
    ):
        result = api.compile_bounded_source_intent(module, bindings)
        with pytest.raises(ValueError):
            api.validate_bounded_source_compilation(
                module, bindings, altered(result, **{field: Hook()})
            )
    result = api.compile_bounded_source_intent(module, bindings)
    result.compilation.hac_ir.metadata["payload"] = Hook()
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(module, bindings, result)


def test_revalidator_bounds_cycles_and_artifact_size():
    module, bindings = source(), (cpu(),)
    result = api.compile_bounded_source_intent(module, bindings)
    result.compilation.hac_ir.metadata["loop"] = result.compilation.hac_ir.metadata
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(module, bindings, result)
    result = api.compile_bounded_source_intent(module, bindings)
    with pytest.raises(ValueError):
        api.validate_bounded_source_compilation(
            module,
            bindings,
            altered(
                result,
                artifacts=altered(result.artifacts, c11_source="x" * (256 * 1024 + 1)),
            ),
        )
