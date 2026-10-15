"""Explicit data admission from model bundle requests to the checked C11 protocol.

Preparation and response decoding perform no native build, execution or I/O.
Protocol consistency is not authentication or evidence of observed execution.
"""

from __future__ import annotations

import hmac
import json
import struct
from dataclasses import dataclass
from hashlib import sha256
from typing import NoReturn

from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import (
    BoundedC11Application,
    decode_bounded_c11_outputs,
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.compiler.bounded_cpu_model import model_from_json
from tuc.compiler.bounded_model_artifact_request import validate_bounded_model_artifact_request
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import SourceIntentModule

MODEL_APPLICATION_RESULT_CONTRACT = "tuc.bounded_model_application_result.v0"


class BoundedModelApplicationError(ValueError):
    """Closed diagnostic for context, CPU admission and response failures."""

    def __init__(self) -> None:
        super().__init__("model_application_rejected")

    @property
    def reason(self) -> str:
        return "model_application_rejected"


@dataclass(frozen=True, slots=True)
class BoundedModelApplication:
    """Inert prepared application and frame, not a native execution handle."""

    module: SourceIntentModule
    application: BoundedC11Application
    input_values: tuple[tuple[str, tuple[float, ...]], ...]
    request_frame: bytes
    bundle_digest: str
    request_digest: str
    model_digest: str
    model_compilation_digest: str
    backend_bindings_digest: str


@dataclass(frozen=True, slots=True)
class BoundedModelApplicationOutput:
    """Public output binding with exact checked response bits."""

    public_name: str
    tensor_name: str
    tensor_index: int
    shape: tuple[int, ...]
    value_bits: str


@dataclass(frozen=True, slots=True)
class BoundedModelApplicationResult:
    """Immutable protocol result; caller-supplied response is not provenance."""

    result_digest: str
    receipt_data: bytes
    outputs: tuple[BoundedModelApplicationOutput, ...]


def _reject() -> NoReturn:
    raise BoundedModelApplicationError()


def _json(value: object) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        + b"\n"
    )


def prepare_bounded_model_application(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
    request_data: bytes,
) -> BoundedModelApplication:
    """Fully validate original context before admitting a CPU application frame.

    Every declared binding must target C11; there is no target replacement or
    fallback. Fixed and variable input bits come only from the validated request.
    """
    try:
        request = validate_bounded_model_artifact_request(
            model_data, backend_bindings, bundle_data, input_data, request_data
        )
        if any(binding.target is not DAGTarget.C11 for binding in backend_bindings):
            _reject()
        model = model_from_json(model_data)
        module = source_intent_from_json(model.graph_json)
        application = prepare_bounded_c11_application(module, backend_bindings)
        manifest = json.loads(application.application_json)
        by_tensor = {item.tensor_name: item for item in request.inputs}
        values = tuple(
            (
                item["public_name"],
                tuple(
                    value
                    for (value,) in struct.iter_unpack(
                        "<f", bytes.fromhex(by_tensor[item["tensor_name"]].value_bits)
                    )
                ),
            )
            for item in manifest["inputs"]
        )
        frame = encode_bounded_c11_inputs(module, backend_bindings, application, dict(values))
        return BoundedModelApplication(
            module,
            application,
            values,
            frame,
            request.bundle_digest,
            request.request_digest,
            request.model_digest,
            request.model_compilation_digest,
            request.backend_bindings_digest,
        )
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedModelApplicationError() from None


def decode_bounded_model_application_response(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
    request_data: bytes,
    response_data: bytes,
    exit_code: int,
) -> BoundedModelApplicationResult:
    """Recreate admission and check response against the exact binary request.

    Error status, malformed data and context drift reject without a result.
    Native execution and numerical correctness cannot be inferred from bytes.
    """
    try:
        prepared = prepare_bounded_model_application(
            model_data, backend_bindings, bundle_data, input_data, request_data
        )
        outputs = decode_bounded_c11_outputs(
            prepared.module,
            backend_bindings,
            prepared.application,
            prepared.request_frame,
            response_data,
            exit_code,
        )
        manifest = json.loads(prepared.application.application_json)
        bindings = tuple(
            BoundedModelApplicationOutput(
                item["public_name"],
                item["tensor_name"],
                item["tensor_index"],
                tuple(item["shape"]),
                b"".join(struct.pack("<f", value) for value in outputs[item["public_name"]]).hex(),
            )
            for item in manifest["outputs"]
        )
        payload = {
            "contract": MODEL_APPLICATION_RESULT_CONTRACT,
            "bundle_digest": prepared.bundle_digest,
            "request_digest": prepared.request_digest,
            "model_digest": prepared.model_digest,
            "model_compilation_digest": prepared.model_compilation_digest,
            "backend_bindings_digest": prepared.backend_bindings_digest,
            "program_digest": prepared.application.program_digest,
            "protocol_request_digest": prepared.request_frame[40:72].hex(),
            "response_sha256": sha256(response_data).hexdigest(),
            "outputs": [
                {
                    "public_name": item.public_name,
                    "tensor_name": item.tensor_name,
                    "tensor_index": item.tensor_index,
                    "shape": list(item.shape),
                    "dtype": "float32",
                    "value_bits": item.value_bits,
                }
                for item in bindings
            ],
            "protocol_validated": True,
            "native_execution_observed": False,
        }
        digest = sha256(_json(payload)).hexdigest()
        receipt = _json({**payload, "result_digest": digest})
        return BoundedModelApplicationResult(digest, receipt, bindings)
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedModelApplicationError() from None


def validate_bounded_model_application_result(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
    request_data: bytes,
    response_data: bytes,
    exit_code: int,
    receipt_data: bytes,
) -> BoundedModelApplicationResult:
    """Recompute a receipt from original request/response bytes, not its hashes."""
    if type(receipt_data) is not bytes or len(receipt_data) > 1024 * 1024:
        _reject()
    fresh = decode_bounded_model_application_response(
        model_data,
        backend_bindings,
        bundle_data,
        input_data,
        request_data,
        response_data,
        exit_code,
    )
    if not hmac.compare_digest(receipt_data, fresh.receipt_data):
        _reject()
    return fresh


__all__ = [
    "MODEL_APPLICATION_RESULT_CONTRACT",
    "BoundedModelApplicationError",
    "BoundedModelApplication",
    "BoundedModelApplicationOutput",
    "BoundedModelApplicationResult",
    "prepare_bounded_model_application",
    "decode_bounded_model_application_response",
    "validate_bounded_model_application_result",
]
