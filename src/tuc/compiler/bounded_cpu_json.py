"""Strict, inert JSON ingestion for the bounded CPU application subset.

This module reads only supplied bytes. It opens no files and starts no parser
worker, native compiler, process, plugin or device operation. Source-code ingestion
and the existing research parser admission boundaries remain separate.
"""

from __future__ import annotations

import json
import math
import re
from typing import NoReturn, cast

from tuc.compiler.bounded_c11_application import (
    BoundedC11Application,
    encode_bounded_c11_inputs,
)
from tuc.compiler.bounded_source import BoundedBackendBinding, _checked_module
from tuc.frontend.source_intent import SourceIntentModule
from tuc.frontend.source_intent_intake import source_intent_from_mapping

MAX_GRAPH_JSON_BYTES = 65536
MAX_GRAPH_JSON_DEPTH = 12
MAX_GRAPH_JSON_TOKENS = 4096
MAX_INPUT_JSON_BYTES = 2097152
MAX_INPUT_JSON_DEPTH = 6
MAX_INPUT_JSON_TOKENS = 200000
MAX_JSON_NUMBER_CHARS = 64
MAX_INPUT_NUMBERS = 65536
INPUT_SCHEMA_VERSION = "tuc.bounded_cpu_inputs.v0"
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_HEX = frozenset("0123456789abcdefABCDEF")


class BoundedCPUJSONError(ValueError):
    """Closed, source-free JSON boundary diagnostic."""

    def __init__(self, reason: str) -> None:
        if type(reason) is not str or reason not in ("graph_json_rejected", "input_json_rejected"):
            raise ValueError("invalid bounded CPU JSON diagnostic")
        self._reason = reason
        super().__init__(reason)

    @property
    def reason(self) -> str:
        return self._reason


def _reject() -> NoReturn:
    raise ValueError("bounded CPU JSON rejected")


def _scan(text: str, max_depth: int, max_tokens: int) -> None:
    """Bound lexical tokens, nesting and numeric conversion before json.loads."""
    stack: list[str] = []
    index, tokens, size = 0, 0, len(text)
    while index < size:
        char = text[index]
        if char in " \t\r\n":
            index += 1
            continue
        tokens += 1
        if tokens > max_tokens:
            _reject()
        if char in "[{":
            stack.append("]" if char == "[" else "}")
            if len(stack) > max_depth:
                _reject()
            index += 1
        elif char in "]}":
            if not stack or stack.pop() != char:
                _reject()
            index += 1
        elif char in ",:":
            index += 1
        elif char == '"':
            index += 1
            while index < size and text[index] != '"':
                if ord(text[index]) < 32:
                    _reject()
                if text[index] == "\\":
                    index += 1
                    if index >= size or text[index] not in '\\"/bfnrtu':
                        _reject()
                    if text[index] == "u":
                        if (index + 4 >= size or
                                any(c not in _HEX for c in text[index + 1:index + 5])):
                            _reject()
                        index += 4
                index += 1
            if index >= size:
                _reject()
            index += 1
        elif char in "-0123456789":
            start = index
            while index < size and text[index] not in " \t\r\n,]}:":
                index += 1
                if index - start > MAX_JSON_NUMBER_CHARS:
                    _reject()
            if _NUMBER.fullmatch(text[start:index]) is None:
                _reject()
        elif text.startswith("true", index):
            index += 4
        elif text.startswith("false", index):
            index += 5
        elif text.startswith("null", index):
            index += 4
        else:
            _reject()
    if stack or tokens == 0:
        _reject()


def _float(token: str) -> float:
    value = float(token)
    mantissa = token.lower().split("e", 1)[0]
    if (not math.isfinite(value) or
            (value == 0.0 and any(char in "123456789" for char in mantissa))):
        _reject()
    return value


def _decode(data: bytes, *, max_bytes: int, max_depth: int, max_tokens: int,
            inputs: bool) -> object:
    if (type(data) is not bytes or not 1 <= len(data) <= max_bytes or
            data.startswith(b"\xef\xbb\xbf")):
        _reject()
    text = data.decode("utf-8", errors="strict")
    _scan(text, max_depth, max_tokens)

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                _reject()
            result[key] = value
        return result

    def constant(value: str) -> NoReturn:
        _reject()

    result: object = json.loads(text, object_pairs_hook=pairs, parse_constant=constant,
                                parse_int=_float if inputs else int, parse_float=_float)
    # CPython combines valid escaped surrogate pairs; lone surrogates reject.
    # The lexical prepass has already bounded both traversal depth and tokens.
    pending = [result]
    while pending:
        value = pending.pop()
        if type(value) is dict:
            pending.extend(value)
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
        elif type(value) is str:
            value.encode("utf-8", errors="strict")
    return result


def _object(value: object, required: frozenset[str], optional: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict:
        _reject()
    result = cast(dict[str, object], value)
    if not required.issubset(result) or set(result) - required - optional:
        _reject()
    return result


def _array(value: object, minimum: int, maximum: int) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _reject()
    return cast(list[object], value)


def _name(value: object) -> None:
    if type(value) is not str or not 1 <= len(value) <= 64:
        _reject()


def _graph_preflight(value: object) -> dict[str, object]:
    """Apply narrow counts/fields before the broader legacy intake constructs IR."""
    graph = _object(value, frozenset({"schema_version", "name", "tensors", "operations",
                                     "returns"}), frozenset())
    if graph["schema_version"] != "source_intent.v0":
        _reject()
    _name(graph["name"])
    for item in _array(graph["tensors"], 2, 24):
        tensor = _object(item, frozenset({"name", "shape"}), frozenset({"dtype"}))
        _name(tensor["name"])
        if tensor.get("dtype", "float32") != "float32":
            _reject()
        for dimension in _array(tensor["shape"], 1, 2):
            if type(dimension) is not int or not 1 <= dimension <= 64:
                _reject()
    for item in _array(graph["operations"], 1, 8):
        op = _object(item, frozenset({"name", "family", "inputs", "outputs"}),
                     frozenset({"attributes", "hints"}))
        _name(op["name"])
        if (type(op["family"]) is not str or
                op["family"] not in ("matmul", "elementwise", "reduction", "softmax")):
            _reject()
        for port in (*_array(op["inputs"], 1, 2), *_array(op["outputs"], 1, 1)):
            _name(port)
        attributes = _object(op.get("attributes", {}), frozenset(),
                             frozenset({"axis", "elementwise_kind", "rhs_transposed"}))
        if len(attributes) > 1:
            _reject()
        for key, attribute in attributes.items():
            if ((key == "axis" and (type(attribute) is not int or attribute != 1)) or
                    (key == "rhs_transposed" and attribute is not True) or
                    (key == "elementwise_kind" and
                     (type(attribute) is not str or attribute not in ("relu", "add", "mul")))):
                _reject()
        hints = _object(op.get("hints", {}), frozenset(), frozenset({
            "robust_to_noise", "prefer_sparsity", "prefer_linear_accelerator", "max_error_budget"}))
        for key, hint in hints.items():
            if key == "max_error_budget":
                if type(hint) not in (int, float) or not 0 <= cast(float, hint) <= 1_000_000:
                    _reject()
            elif type(hint) is not bool:
                _reject()
    for item in _array(graph["returns"], 1, 8):
        returned = _object(item, frozenset({"public_name", "tensor_name"}), frozenset({"required"}))
        _name(returned["public_name"])
        _name(returned["tensor_name"])
        if returned.get("required", True) is not True:
            _reject()
    return graph


def source_intent_from_json(data: bytes) -> SourceIntentModule:
    """Decode explicit source_intent.v0 JSON into a fresh bounded typed module."""
    try:
        decoded = _decode(data, max_bytes=MAX_GRAPH_JSON_BYTES, max_depth=MAX_GRAPH_JSON_DEPTH,
                          max_tokens=MAX_GRAPH_JSON_TOKENS, inputs=False)
        mapping = _graph_preflight(decoded)
        return _checked_module(source_intent_from_mapping(mapping))
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUJSONError("graph_json_rejected") from None


def inputs_from_json(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application, data: bytes,
) -> dict[str, tuple[float, ...]]:
    """Decode named JSON numbers, then revalidate the application and exact FP32 I/O.

    Both integer and fractional JSON tokens convert to exact Python floats.
    Negative zero is preserved. Numeric overflow or nonzero binary64 underflow
    rejects before the existing binary32 encoder performs its stricter checks.
    """
    try:
        decoded = _decode(data, max_bytes=MAX_INPUT_JSON_BYTES, max_depth=MAX_INPUT_JSON_DEPTH,
                          max_tokens=MAX_INPUT_JSON_TOKENS, inputs=True)
        envelope = _object(decoded, frozenset({"schema_version", "inputs"}), frozenset())
        if (envelope["schema_version"] != INPUT_SCHEMA_VERSION or
                type(envelope["inputs"]) is not dict):
            _reject()
        values = cast(dict[str, object], envelope["inputs"])
        if not 1 <= len(values) <= 24:
            _reject()
        result: dict[str, tuple[float, ...]] = {}
        total = 0
        for name, value in values.items():
            _name(name)
            sequence = _array(value, 1, 4096)
            total += len(sequence)
            if total > MAX_INPUT_NUMBERS or any(type(item) is not float for item in sequence):
                _reject()
            result[name] = cast(tuple[float, ...], tuple(sequence))
        encode_bounded_c11_inputs(module, backend_bindings, application, result)
        return result
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUJSONError("input_json_rejected") from None


__all__ = ["BoundedCPUJSONError", "MAX_GRAPH_JSON_BYTES", "MAX_INPUT_JSON_BYTES",
           "INPUT_SCHEMA_VERSION", "source_intent_from_json", "inputs_from_json"]
