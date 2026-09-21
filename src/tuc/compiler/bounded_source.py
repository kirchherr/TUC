"""Data-only Source Intent entry point for the bounded DAG artifact compiler.

Only explicit, static FP32 Matmul/ReLU/Add/row-Sum modules are accepted. Backend
descriptors are planning data, not backend objects or execution permissions.
No source parser, registry discovery, native compiler or runtime is invoked.
"""

from __future__ import annotations

import gc
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from hashlib import sha256
from math import isfinite, prod
from types import MappingProxyType
from typing import Any, NoReturn, cast

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import (
    MAX_DAG_ARTIFACT_BYTES,
    MAX_DAG_BUFFER_BYTES,
    MAX_DAG_DIMENSION,
    MAX_DAG_METADATA_BYTES,
    MAX_DAG_NAME_BYTES,
    MAX_DAG_OPERATIONS,
    MAX_DAG_SCALAR_WORK,
    MAX_DAG_TENSORS,
    BoundedDAGArtifacts,
    DAGTarget,
    lower_bounded_dag,
)
from tuc.compiler.pipeline import CompilationResult, compile_graph
from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.frontend.source_intent_metadata import source_intent_to_triton_metadata
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind

MAX_BOUNDED_ERROR_BUDGET = 1_000_000.0
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_BACKEND_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")
_KINDS = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
_BOOLEAN_HINTS = frozenset({"robust_to_noise", "prefer_sparsity", "prefer_linear_accelerator"})


@dataclass(frozen=True)
class BoundedBackendBinding:
    """One declarative capability bound to a closed source-emission target."""

    capability: BackendCapability
    target: DAGTarget


@dataclass(frozen=True)
class BoundedTensorBinding:
    """A public tensor name and its exact identity in the artifact manifest."""

    public_name: str
    tensor_name: str
    tensor_index: int
    shape: tuple[int, ...]
    dtype: str = "float32"


@dataclass(frozen=True)
class BoundedSourceCompilation:
    """Inspectable compiler outputs; these data do not grant native execution.

    Nested legacy compiler metadata remains mutable. Revalidate this entire
    result against the original module and bindings before consuming it.
    """

    compilation: CompilationResult
    artifacts: BoundedDAGArtifacts
    input_bindings: tuple[BoundedTensorBinding, ...]
    output_bindings: tuple[BoundedTensorBinding, ...]
    source_intent_digest: str
    backend_bindings_digest: str


def _reject() -> NoReturn:
    raise ValueError("bounded Source Intent compilation rejected")


def _record(value: object, expected: type[Any]) -> dict[str, object]:
    if type(value) is not expected:
        _reject()
    try:
        state = object.__getattribute__(value, "__dict__")
    except AttributeError:
        _reject()
    names = {field.name for field in fields(cast(Any, expected))}
    if (type(state) is not dict or len(state) != len(names) or
            any(type(key) is not str or len(key) > 64 for key in state) or set(state) != names):
        _reject()
    return cast(dict[str, object], state)


def _mapping(value: object, limit: int) -> dict[str, object]:
    if type(value) is MappingProxyType:
        # CPython exposes the backing mapping through its built-in GC traversal.
        # The proxy may wrap hostile Mapping objects, so never call its methods.
        # Other interpreter/reference layouts fail closed rather than dispatch.
        references = gc.get_referents(value)
        if len(references) != 1 or type(references[0]) is not dict:
            _reject()
        value = references[0]
    if type(value) is not dict:
        _reject()
    mapping = cast(dict[object, object], value)
    if (len(mapping) > limit or
            any(type(key) is not str or len(key) > 128 for key in mapping)):
        _reject()
    return cast(dict[str, object], dict.copy(mapping))


def _name(value: object, *, backend: bool = False) -> str:
    if (type(value) is not str or len(value) > MAX_DAG_NAME_BYTES or
            (_BACKEND_NAME if backend else _NAME).fullmatch(value) is None):
        _reject()
    return value


def _tuple(value: object, minimum: int, maximum: int) -> tuple[object, ...]:
    if type(value) is not tuple or not minimum <= len(value) <= maximum:
        _reject()
    return cast(tuple[object, ...], value)


def _error_budget(value: object) -> float:
    if type(value) not in (int, float):
        _reject()
    number = cast(int | float, value)
    # Compare before float conversion or isfinite: huge Python integers reject
    # without conversion overflow or attacker-defined numeric methods.
    if not 0 <= number <= MAX_BOUNDED_ERROR_BUDGET or not isfinite(number):
        _reject()
    return float(number)


def _operation_set(value: object, *, nonempty: bool) -> frozenset[OperationKind]:
    if type(value) is not frozenset or not int(nonempty) <= len(value) <= 3:
        _reject()
    values = cast(frozenset[object], value)
    if any(type(item) is not OperationKind for item in values):
        _reject()
    result = cast(frozenset[OperationKind], values)
    if not result.issubset(_KINDS):
        _reject()
    return result


def _checked_bindings(value: object) -> tuple[BoundedBackendBinding, ...]:
    result = []
    names, targets = set(), set()
    for item in _tuple(value, 1, 2):
        binding = _record(item, BoundedBackendBinding)
        target = binding["target"]
        if type(target) is not DAGTarget or target in targets:
            _reject()
        capability = _record(binding["capability"], BackendCapability)
        name = _name(capability["name"], backend=True)
        if name in names:
            _reject()
        supported = _operation_set(capability["supported_ops"], nonempty=True)
        preferred = _operation_set(capability["preferred_for"], nonempty=False)
        if not preferred.issubset(supported):
            _reject()
        for field in ("supports_noise_model", "supports_calibration"):
            if type(capability[field]) is not bool:
                _reject()
        domain = (MemoryDomainKind.HOST_RAM if target is DAGTarget.C11
                  else MemoryDomainKind.UNKNOWN)
        if type(capability["memory_domain"]) is not MemoryDomainKind:
            _reject()
        if capability["memory_domain"] is not domain:
            _reject()
        for field in ("supported_layouts", "produced_layouts"):
            layouts = capability[field]
            if (type(layouts) is not frozenset or len(layouts) != 1 or
                    any(type(layout) is not LayoutKind or layout is not LayoutKind.ROW_MAJOR
                        for layout in cast(frozenset[object], layouts))):
                _reject()
        budget = capability["max_error_budget"]
        clean = BackendCapability(
            name=name, supported_ops=supported, preferred_for=preferred,
            supports_noise_model=cast(bool, capability["supports_noise_model"]),
            supports_calibration=cast(bool, capability["supports_calibration"]),
            max_error_budget=None if budget is None else _error_budget(budget),
            memory_domain=domain, supported_layouts=frozenset({LayoutKind.ROW_MAJOR}),
            produced_layouts=frozenset({LayoutKind.ROW_MAJOR}),
        )
        result.append(BoundedBackendBinding(clean, target))
        names.add(name)
        targets.add(target)
    return tuple(sorted(result, key=lambda binding: binding.capability.name))


def _checked_module(value: object) -> SourceIntentModule:
    module = _record(value, SourceIntentModule)
    name = _name(module["name"])
    if type(module["contract"]) is not str or module["contract"] != SOURCE_INTENT_IR_CONTRACT:
        _reject()
    raw_tensors = _tuple(module["tensors"], 2, MAX_DAG_TENSORS)
    raw_operations = _tuple(module["operations"], 1, MAX_DAG_OPERATIONS)
    raw_returns = _tuple(module["returns"], 1, MAX_DAG_OPERATIONS)
    tensors: dict[str, SourceIntentTensor] = {}
    total_bytes = 0
    for item in raw_tensors:
        tensor = _record(item, SourceIntentTensor)
        tensor_name = _name(tensor["name"])
        shape = _tuple(tensor["shape"], 1, 2)
        if (type(tensor["dtype"]) is not str or tensor["dtype"] != "float32" or
                any(type(d) is not int or not 1 <= d <= MAX_DAG_DIMENSION
                    for d in shape) or tensor_name in tensors):
            _reject()
        typed_shape = cast(tuple[int, ...], shape)
        total_bytes += 4 * prod(typed_shape)
        if total_bytes > MAX_DAG_BUFFER_BYTES:
            _reject()
        tensors[tensor_name] = SourceIntentTensor(tensor_name, typed_shape)
    operations = []
    operation_names: set[str] = set()
    produced: set[str] = set()
    consumed: set[str] = set()
    work = 0
    for item in raw_operations:
        operation = _record(item, SourceIntentOperation)
        op_name = _name(operation["name"])
        family = operation["family"]
        if (type(family) is not str or len(family) > 16 or
                family not in {"matmul", "elementwise", "reduction"}
                or op_name in operation_names):
            _reject()
        inputs = tuple(_name(port) for port in _tuple(operation["inputs"], 1, 2))
        outputs = tuple(_name(port) for port in _tuple(operation["outputs"], 1, 1))
        if (any(port not in tensors for port in (*inputs, *outputs)) or
                outputs[0] in produced or outputs[0] in inputs):
            _reject()
        hints = _mapping(operation["hints"], 4)
        if set(hints) - (_BOOLEAN_HINTS | {"max_error_budget"}):
            _reject()
        for key, hint in hints.items():
            if key in _BOOLEAN_HINTS:
                if type(hint) is not bool:
                    _reject()
            else:
                hints[key] = _error_budget(hint)
        attributes = _mapping(operation["attributes"], 1)
        shapes = tuple(tensors[port].shape for port in inputs)
        output_shape = tensors[outputs[0]].shape
        if family == "matmul":
            if (set(attributes) - {"rhs_transposed"} or
                    ("rhs_transposed" in attributes and attributes["rhs_transposed"] is not True) or
                    len(shapes) != 2 or
                    any(len(shape) != 2 for shape in (*shapes, output_shape))):
                _reject()
            rows, inner = shapes[0]
            if attributes.get("rhs_transposed") is True:
                columns, other_inner = shapes[1]
            else:
                other_inner, columns = shapes[1]
            if inner != other_inner or output_shape != (rows, columns):
                _reject()
            work += 2 * rows * inner * columns
        elif family == "elementwise":
            if (set(attributes) != {"elementwise_kind"} or
                    type(attributes["elementwise_kind"]) is not str or
                    attributes["elementwise_kind"] not in {"relu", "add", "mul"}):
                _reject()
            if attributes["elementwise_kind"] == "relu":
                if len(shapes) != 1 or output_shape != shapes[0]:
                    _reject()
            elif attributes["elementwise_kind"] == "mul":
                if len(shapes) != 2 or shapes[0] != shapes[1] or output_shape != shapes[0]:
                    _reject()
            elif (len(shapes) != 2 or output_shape != shapes[0] or
                  not (shapes[1] == shapes[0] or
                       (len(shapes[0]) == 2 and shapes[1] == (shapes[0][1],)))):
                _reject()
            work += prod(output_shape)
        else:
            if (set(attributes) != {"axis"} or type(attributes["axis"]) is not int or
                    attributes["axis"] != 1 or len(shapes) != 1 or len(shapes[0]) != 2 or
                    output_shape != (shapes[0][0],)):
                _reject()
            work += prod(shapes[0])
        if work > MAX_DAG_SCALAR_WORK:
            _reject()
        operations.append(SourceIntentOperation(op_name, family, inputs, outputs,
                                                hints, attributes))
        operation_names.add(op_name)
        consumed.update(inputs)
        produced.update(outputs)
    if produced | consumed != set(tensors):
        _reject()
    # Resolve all producers first: a forward reference must not become an input.
    ready = set(tensors) - produced
    for ordered_op in operations:
        if any(port not in ready for port in ordered_op.inputs):
            _reject()
        ready.update(ordered_op.outputs)
    terminal = produced - consumed
    returns = []
    public_names, returned = set(), set()
    for item in raw_returns:
        binding = _record(item, SourceIntentReturn)
        public = _name(binding["public_name"])
        tensor_name = _name(binding["tensor_name"])
        if (binding["required"] is not True or public in public_names or
                tensor_name in returned or tensor_name not in terminal):
            _reject()
        returns.append(SourceIntentReturn(public, tensor_name, True))
        public_names.add(public)
        returned.add(tensor_name)
    if returned != terminal:
        _reject()
    return SourceIntentModule(name, tuple(tensors.values()), tuple(operations),
                              returns=tuple(returns))


def _digest(value: object) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    data = text.encode("utf-8")
    if len(data) > MAX_DAG_METADATA_BYTES:
        _reject()
    return "sha256:" + sha256(data).hexdigest()


def _source_digest(module: SourceIntentModule) -> str:
    return _digest({
        "schema_version": "tuc.bounded_source_intent.v0", "name": module.name,
        "contract": module.contract,
        "tensors": [{"name": t.name, "shape": t.shape, "dtype": t.dtype} for t in module.tensors],
        "operations": [{"name": op.name, "family": op.family, "inputs": op.inputs,
                        "outputs": op.outputs, "hints": dict(op.hints),
                        "attributes": dict(op.attributes)} for op in module.operations],
        "returns": [{"public_name": r.public_name, "tensor_name": r.tensor_name,
                     "required": r.required} for r in module.returns],
    })


def _bindings_digest(bindings: tuple[BoundedBackendBinding, ...]) -> str:
    return _digest({
        "schema_version": "tuc.bounded_backend_bindings.v0",
        "bindings": [{
            "target": binding.target.value, "name": binding.capability.name,
            "supported_ops": sorted(kind.value for kind in binding.capability.supported_ops),
            "preferred_for": sorted(kind.value for kind in binding.capability.preferred_for),
            "supports_noise_model": binding.capability.supports_noise_model,
            "supports_calibration": binding.capability.supports_calibration,
            "max_error_budget": binding.capability.max_error_budget,
            "memory_domain": binding.capability.memory_domain.value,
            "supported_layouts": [LayoutKind.ROW_MAJOR.value],
            "produced_layouts": [LayoutKind.ROW_MAJOR.value],
        } for binding in bindings],
    })


def compile_bounded_source_intent(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
) -> BoundedSourceCompilation:
    """Validate typed source data, plan supported placements and emit inert text.

    Input tuples contain exact canonical dataclasses, never backend instances.
    Binding order is canonicalized by name. Every produced terminal value must
    have one explicit required public return; declared unused tensors reject.
    """
    clean_module = _checked_module(module)
    bindings = _checked_bindings(backend_bindings)
    source_digest = _source_digest(clean_module)
    bindings_digest = _bindings_digest(bindings)
    graph = source_intent_to_triton_metadata(clean_module).to_compute_graph()
    capabilities = tuple(binding.capability for binding in bindings)
    if any(not any(capability.supports(op) for capability in capabilities)
           for op in graph.operations):
        _reject()
    compilation = compile_graph(graph, capabilities, include_candidate_scores=True)
    by_name = {binding.capability.name: binding for binding in bindings}
    partition = compilation.partition_plan
    if (partition.override_effects or partition.layout_conversions or
            len(partition.assignments) != len(compilation.hac_ir.graph.operations)):
        _reject()
    for operation, assignment in zip(compilation.hac_ir.graph.operations,
                                     partition.assignments, strict=True):
        binding = by_name.get(assignment.backend_name)
        if (binding is None or assignment.reason.startswith("fallback:") or
                assignment.reason.startswith("manual_override:") or
                assignment.operation_name != operation.name or
                not binding.capability.supports(operation) or
                assignment.memory_domain is not binding.capability.memory_domain or
                assignment.produced_layout is not LayoutKind.ROW_MAJOR):
            _reject()
    used = {assignment.backend_name for assignment in partition.assignments}
    targets = {binding.capability.name: binding.target for binding in bindings
               if binding.capability.name in used}
    if any(op.attributes.get("elementwise_kind") == "mul" for op in clean_module.operations):
        from tuc.backends.bounded_mul_dag import lower_bounded_mul_dag

        artifacts = lower_bounded_mul_dag(compilation.hac_ir, partition, targets)
    elif any(op.attributes.get("rhs_transposed") is True for op in clean_module.operations):
        from tuc.backends.bounded_linear_dag import lower_bounded_linear_dag

        artifacts = lower_bounded_linear_dag(compilation.hac_ir, partition, targets)
    elif any(op.attributes.get("elementwise_kind") == "add" for op in clean_module.operations):
        # RFC 0327 keeps the historical DAG/CUDA emitter and its hash-bound
        # observations unchanged. The extension has its own CPU-only contract.
        from tuc.backends.bounded_add_dag import lower_bounded_add_dag

        artifacts = lower_bounded_add_dag(compilation.hac_ir, partition, targets)
    else:
        artifacts = lower_bounded_dag(compilation.hac_ir, partition, targets)
    manifest = json.loads(artifacts.manifest_json)
    tensors = manifest["tensors"]

    def public_binding(public: str, index: int) -> BoundedTensorBinding:
        tensor = tensors[index]
        return BoundedTensorBinding(public, tensor["name"], index, tuple(tensor["shape"]),
                                    tensor["dtype"])

    inputs = tuple(public_binding(tensors[index]["name"], index)
                   for index in manifest["input_tensors"])
    tensor_ids = {tensor["name"]: tensor["index"] for tensor in tensors}
    outputs = tuple(public_binding(item.public_name, tensor_ids[item.tensor_name])
                    for item in clean_module.returns)
    return BoundedSourceCompilation(compilation, artifacts, inputs, outputs,
                                     source_digest, bindings_digest)


def _match_result(value: object, expected: object) -> None:
    """Compare against fresh trusted structure without caller equality or dumps."""
    remaining = 20_000

    def match(actual: object, reference: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 24 or type(actual) is not type(reference):
            _reject()
        if reference is None:
            return
        if type(reference) in (str, bool, int, float):
            # Exact built-ins cannot invoke user equality; large strings reject
            # by length before content comparison or encoding.
            if type(reference) is str and len(cast(str, actual)) != len(reference):
                _reject()
            if actual != reference:
                _reject()
        elif isinstance(reference, StrEnum):
            if actual is not reference:
                _reject()
        elif type(reference) is tuple:
            a, b = cast(tuple[object, ...], actual), cast(tuple[object, ...], reference)
            if len(a) != len(b) or len(a) > 128:
                _reject()
            for left, right in zip(a, b, strict=True):
                match(left, right, depth + 1)
        elif type(reference) in (dict, MappingProxyType):
            left, right = _mapping(actual, 128), _mapping(reference, 128)
            if set(left) != set(right):
                _reject()
            for key in right:
                match(left[key], right[key], depth + 1)
        elif is_dataclass(reference):
            # Only the freshly reconstructed reference chooses the exact class
            # and its field names; the caller cannot supply reflective hooks.
            left, right = _record(actual, type(reference)), _record(reference, type(reference))
            for key in right:
                match(left[key], right[key], depth + 1)
        else:
            _reject()

    match(value, expected, 0)


def validate_bounded_source_compilation(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    result: BoundedSourceCompilation,
) -> None:
    """Reconstruct and check every result field, including mutable compiler data."""
    state = _record(result, BoundedSourceCompilation)
    artifacts = _record(state["artifacts"], BoundedDAGArtifacts)
    total = 0
    for text in artifacts.values():
        if type(text) is not str or len(text) > MAX_DAG_ARTIFACT_BYTES:
            _reject()
        total += len(text.encode("utf-8"))
        if total > MAX_DAG_ARTIFACT_BYTES:
            _reject()
    _match_result(result, compile_bounded_source_intent(module, backend_bindings))


__all__ = [
    "BoundedBackendBinding",
    "BoundedSourceCompilation",
    "BoundedTensorBinding",
    "compile_bounded_source_intent",
    "validate_bounded_source_compilation",
]
