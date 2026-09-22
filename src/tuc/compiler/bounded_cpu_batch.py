"""Strict, inert batches of inputs for one revalidated bounded CPU application.

Parsing never builds or executes a program. All requests and aggregate budgets
are checked before a batch is returned; digests bind data, not execution evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import NoReturn, cast

from tuc.compiler.bounded_c11_application import (
    BoundedC11Application,
    encode_bounded_c11_inputs,
    validate_bounded_c11_application,
)
from tuc.compiler.bounded_cpu_json import (
    INPUT_SCHEMA_VERSION,
    _array,
    _decode,
    _object,
    inputs_from_json,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import SourceIntentModule

BATCH_SCHEMA_VERSION = "tuc.bounded_cpu_batch.v0"
MAX_BATCH_JSON_BYTES = 2097152
MAX_BATCH_REQUESTS = 16
MAX_BATCH_INPUT_ELEMENTS = 65536
MAX_BATCH_OUTPUT_ELEMENTS = 65536
_MAX_DEPTH = 8
_MAX_TOKENS = 200000
_REQUEST_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


class BoundedCPUBatchError(ValueError):
    """Closed diagnostic for rejected data, graph or application artifacts."""

    def __init__(self) -> None:
        super().__init__("batch_json_rejected")

    @property
    def reason(self) -> str:
        return "batch_json_rejected"


@dataclass(frozen=True, slots=True)
class BoundedCPURequest:
    """One validated request, with immutable inputs in public binding order."""

    request_id: str
    inputs: tuple[tuple[str, tuple[float, ...]], ...]
    request_digest: str

    def values(self) -> dict[str, tuple[float, ...]]:
        """Return a fresh input mapping; immutable numeric tuples may be shared."""
        return dict(self.inputs)


@dataclass(frozen=True, slots=True)
class BoundedCPUBatch:
    """A complete validated input batch, with no native execution authority."""

    program_digest: str
    batch_digest: str
    requests: tuple[BoundedCPURequest, ...]


def _reject() -> NoReturn:
    raise ValueError("bounded CPU batch rejected")


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _inputs(value: object) -> dict[str, list[float]]:
    if type(value) is not dict or len(value) > 24:
        _reject()
    result: dict[str, list[float]] = {}
    for name, raw in value.items():
        if type(name) is not str or not 1 <= len(name) <= 64:
            _reject()
        numbers = _array(raw, 1, 4096)
        if any(type(number) is not float for number in numbers):
            _reject()
        result[name] = cast(list[float], numbers)
    return result


def batch_from_json(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application,
    data: bytes,
) -> BoundedCPUBatch:
    """Validate every request before returning immutable, ordered batch data.

    Shared and request-specific names must be disjoint. Shared elements count once
    for every expanded request. Each expansion uses the unchanged single-request
    JSON/FP32 encoder; identities bind encoded binary32 payloads, not JSON spelling.
    """
    try:
        decoded = _decode(data, max_bytes=MAX_BATCH_JSON_BYTES, max_depth=_MAX_DEPTH,
                          max_tokens=_MAX_TOKENS, inputs=True)
        envelope = _object(decoded, frozenset({"schema_version", "requests"}),
                           frozenset({"shared_inputs"}))
        if envelope["schema_version"] != BATCH_SCHEMA_VERSION:
            _reject()
        shared = _inputs(envelope.get("shared_inputs", {}))
        pending: list[tuple[str, dict[str, list[float]]]] = []
        identifiers: set[str] = set()
        input_elements = 0
        for value in _array(envelope["requests"], 1, MAX_BATCH_REQUESTS):
            request = _object(value, frozenset({"id", "inputs"}), frozenset())
            request_id = request["id"]
            if (type(request_id) is not str or len(request_id) > 64 or
                    _REQUEST_ID.fullmatch(request_id) is None or request_id in identifiers):
                _reject()
            specific = _inputs(request["inputs"])
            if shared.keys() & specific.keys():
                _reject()
            expanded = {**shared, **specific}
            input_elements += sum(len(numbers) for numbers in expanded.values())
            if input_elements > MAX_BATCH_INPUT_ELEMENTS:
                _reject()
            identifiers.add(request_id)
            pending.append((request_id, expanded))

        # Only an independently reconstructed, exact application may supply the
        # manifest shapes/names or program identity used in the following checks.
        validate_bounded_c11_application(module, backend_bindings, application)
        manifest = json.loads(application.application_json)
        public_names = tuple(binding["public_name"] for binding in manifest["inputs"])
        if (len(pending) * sum(manifest["output_elements"]) > MAX_BATCH_OUTPUT_ELEMENTS or
                any(set(values) != set(public_names) for _, values in pending)):
            _reject()

        requests = []
        for request_id, expanded in pending:
            values = inputs_from_json(module, backend_bindings, application,
                                      _json({"schema_version": INPUT_SCHEMA_VERSION,
                                             "inputs": expanded}))
            frame = encode_bounded_c11_inputs(module, backend_bindings, application, values)
            requests.append(BoundedCPURequest(
                request_id, tuple((name, values[name]) for name in public_names),
                frame[40:72].hex()))
        program_digest = application.program_digest
        batch_digest = sha256(_json({
            "schema_version": BATCH_SCHEMA_VERSION,
            "program_digest": program_digest,
            "requests": [{"id": item.request_id, "request_digest": item.request_digest}
                         for item in requests],
        })).hexdigest()
        return BoundedCPUBatch(program_digest, batch_digest, tuple(requests))
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUBatchError() from None


__all__ = [
    "BATCH_SCHEMA_VERSION", "MAX_BATCH_JSON_BYTES", "MAX_BATCH_REQUESTS",
    "MAX_BATCH_INPUT_ELEMENTS", "MAX_BATCH_OUTPUT_ELEMENTS", "BoundedCPURequest",
    "BoundedCPUBatch", "BoundedCPUBatchError", "batch_from_json",
]
