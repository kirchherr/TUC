"""Bounded, inert model JSON: an existing graph plus fixed FP32 parameters.

No files, imports of caller modules, native compilation or execution occur here.
Every public operation accepts bytes and revalidates the complete model rather
than trusting caller-constructed model objects or supplied digests.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from hashlib import sha256
from typing import NoReturn, cast

from tuc.compiler.bounded_cpu_batch import BATCH_SCHEMA_VERSION, MAX_BATCH_JSON_BYTES
from tuc.compiler.bounded_cpu_json import (
    INPUT_SCHEMA_VERSION,
    MAX_GRAPH_JSON_BYTES,
    MAX_INPUT_JSON_BYTES,
    _array,
    _decode,
    _object,
    source_intent_from_json,
)
from tuc.frontend.source_intent import SourceIntentModule

MODEL_SCHEMA_VERSION = "tuc.bounded_cpu_model.v0"
MAX_MODEL_JSON_BYTES = 2 * 1024 * 1024
_DEPTH = 13
_TOKENS = 204096


class BoundedCPUModelError(ValueError):
    """Closed diagnostic without source, parameter or filesystem details."""

    def __init__(self) -> None:
        super().__init__("model_json_rejected")

    @property
    def reason(self) -> str:
        return "model_json_rejected"


@dataclass(frozen=True, slots=True)
class BoundedCPUModel:
    """Inert parsed data; this object never confers execution authority."""

    model_json: bytes
    graph_json: bytes
    parameters: tuple[tuple[str, tuple[float, ...]], ...]
    variable_inputs: tuple[str, ...]
    model_digest: str


def _reject() -> NoReturn:
    raise ValueError("bounded CPU model rejected")


def _json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("ascii")


def _graph(module: SourceIntentModule) -> dict[str, object]:
    return {
        "schema_version": "source_intent.v0",
        "name": module.name,
        "tensors": [
            {"name": t.name, "shape": list(t.shape), "dtype": t.dtype} for t in module.tensors
        ],
        "operations": [
            {
                "name": op.name,
                "family": op.family,
                "inputs": list(op.inputs),
                "outputs": list(op.outputs),
                "attributes": dict(op.attributes),
                "hints": dict(op.hints),
            }
            for op in module.operations
        ],
        "returns": [
            {"public_name": r.public_name, "tensor_name": r.tensor_name, "required": r.required}
            for r in module.returns
        ],
    }


def _external(module: SourceIntentModule) -> dict[str, int]:
    produced = {name for op in module.operations for name in op.outputs}
    used = {name for op in module.operations for name in op.inputs}
    return {
        t.name: math.prod(t.shape)
        for t in module.tensors
        if t.name in used and t.name not in produced
    }


def _numbers(value: object) -> tuple[float, ...]:
    result = []
    for number in _array(value, 1, 4096):
        if type(number) is not float or not math.isfinite(number):
            _reject()
        encoded = struct.pack("<f", number)
        bits = struct.unpack("<I", encoded)[0] & 0x7FFFFFFF
        if bits >= 0x7F800000 or (bits != 0 and bits < 0x00800000) or (number != 0.0 and bits == 0):
            _reject()
        result.append(struct.unpack("<f", encoded)[0])
    return tuple(result)


def _values(value: object) -> dict[str, tuple[float, ...]]:
    if type(value) is not dict or len(value) > 24:
        _reject()
    result = {}
    count = 0
    for name, raw in value.items():
        if type(name) is not str or not 1 <= len(name) <= 64:
            _reject()
        numbers = _numbers(raw)
        count += len(numbers)
        if count > 65536:
            _reject()
        result[name] = numbers
    return result


def _build(graph: object, parameters: object) -> BoundedCPUModel:
    raw_graph = _json(graph)
    if len(raw_graph) > MAX_GRAPH_JSON_BYTES:
        _reject()
    module = source_intent_from_json(raw_graph)
    graph = _graph(module)
    canonical_graph = _json(graph)
    # Canonical output must itself remain admissible, including graph defaults.
    source_intent_from_json(canonical_graph)
    external = _external(module)
    fixed = _values(parameters)
    if not fixed or not set(fixed) < set(external):
        _reject()
    if any(len(numbers) != external[name] for name, numbers in fixed.items()):
        _reject()
    ordered = tuple((name, fixed[name]) for name in sorted(fixed))
    canonical = (
        _json({"schema_version": MODEL_SCHEMA_VERSION, "graph": graph, "parameters": dict(ordered)})
        + b"\n"
    )
    if len(canonical) > MAX_MODEL_JSON_BYTES:
        _reject()
    identity = _json(
        {
            "schema_version": MODEL_SCHEMA_VERSION,
            "graph": graph,
            "parameter_bits": {
                name: b"".join(struct.pack("<f", n) for n in numbers).hex()
                for name, numbers in ordered
            },
        }
    )
    return BoundedCPUModel(
        canonical,
        canonical_graph,
        ordered,
        tuple(name for name in external if name not in fixed),
        sha256(identity).hexdigest(),
    )


def model_from_json(data: bytes) -> BoundedCPUModel:
    """Validate graph integers and FP32 parameters, preserving a literal -0."""
    try:
        structural = _decode(
            data, max_bytes=MAX_MODEL_JSON_BYTES, max_depth=_DEPTH, max_tokens=_TOKENS, inputs=False
        )
        envelope = _object(
            structural, frozenset({"schema_version", "graph", "parameters"}), frozenset()
        )
        if envelope["schema_version"] != MODEL_SCHEMA_VERSION:
            _reject()
        numeric = cast(
            dict[str, object],
            _decode(
                data,
                max_bytes=MAX_MODEL_JSON_BYTES,
                max_depth=_DEPTH,
                max_tokens=_TOKENS,
                inputs=True,
            ),
        )
        return _build(envelope["graph"], numeric["parameters"])
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedCPUModelError() from None


def pack_model(graph_data: bytes, parameter_data: bytes) -> bytes:
    """Pack a graph and an existing input envelope containing only fixed inputs."""
    try:
        module = source_intent_from_json(graph_data)
        decoded = _decode(
            parameter_data,
            max_bytes=MAX_INPUT_JSON_BYTES,
            max_depth=6,
            max_tokens=200000,
            inputs=True,
        )
        envelope = _object(decoded, frozenset({"schema_version", "inputs"}), frozenset())
        if envelope["schema_version"] != INPUT_SCHEMA_VERSION:
            _reject()
        return _build(_graph(module), envelope["inputs"]).model_json
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedCPUModelError() from None


def expand_model_inputs(model_data: bytes, input_data: bytes) -> bytes:
    """Expand exact variable inputs without allowing fixed-parameter overrides."""
    try:
        model = model_from_json(model_data)
        decoded = _decode(
            input_data, max_bytes=MAX_INPUT_JSON_BYTES, max_depth=6, max_tokens=200000, inputs=True
        )
        envelope = _object(decoded, frozenset({"schema_version", "inputs"}), frozenset())
        if envelope["schema_version"] != INPUT_SCHEMA_VERSION:
            _reject()
        supplied = _values(envelope["inputs"])
        if set(supplied) != set(model.variable_inputs):
            _reject()
        external = _external(source_intent_from_json(model.graph_json))
        if any(len(values) != external[name] for name, values in supplied.items()):
            _reject()
        expanded = _json(
            {
                "schema_version": INPUT_SCHEMA_VERSION,
                "inputs": {**dict(model.parameters), **supplied},
            }
        )
        if len(expanded) > MAX_INPUT_JSON_BYTES:
            _reject()
        return expanded
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedCPUModelError() from None


def expand_model_batch(model_data: bytes, batch_data: bytes) -> bytes:
    """Merge fixed inputs into shared data; the existing batch gate checks all requests."""
    try:
        model = model_from_json(model_data)
        decoded = _decode(
            batch_data, max_bytes=MAX_BATCH_JSON_BYTES, max_depth=8, max_tokens=200000, inputs=True
        )
        envelope = _object(
            decoded, frozenset({"schema_version", "requests"}), frozenset({"shared_inputs"})
        )
        if envelope["schema_version"] != BATCH_SCHEMA_VERSION:
            _reject()
        fixed = dict(model.parameters)
        shared = _values(envelope.get("shared_inputs", {}))
        if set(shared) & set(fixed):
            _reject()
        for value in _array(envelope["requests"], 1, 16):
            request = _object(value, frozenset({"id", "inputs"}), frozenset())
            specific = _values(request["inputs"])
            if set(specific) & set(fixed):
                _reject()
        expanded = _json({**envelope, "shared_inputs": {**fixed, **shared}})
        if len(expanded) > MAX_BATCH_JSON_BYTES:
            _reject()
        return expanded
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedCPUModelError() from None


__all__ = [
    "MODEL_SCHEMA_VERSION",
    "MAX_MODEL_JSON_BYTES",
    "BoundedCPUModel",
    "BoundedCPUModelError",
    "model_from_json",
    "pack_model",
    "expand_model_inputs",
    "expand_model_batch",
]
