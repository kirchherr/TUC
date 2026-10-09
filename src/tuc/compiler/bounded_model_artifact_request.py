"""Bounded, inert invocation data tied to a portable model artifact bundle."""

from __future__ import annotations

import hmac
import json
import struct
from dataclasses import dataclass
from hashlib import sha256
from math import prod
from typing import NoReturn

from tuc.compiler.bounded_cpu_json import _decode
from tuc.compiler.bounded_cpu_model import expand_model_inputs
from tuc.compiler.bounded_model_artifact_bundle import (
    BoundedModelArtifactBundle,
    inspect_bounded_model_artifact_bundle,
    validate_bounded_model_artifact_bundle,
)
from tuc.compiler.bounded_source import BoundedBackendBinding

MODEL_ARTIFACT_REQUEST_CONTRACT = "tuc.bounded_model_artifact_request.v0"
MAX_MODEL_ARTIFACT_REQUEST_BYTES = 2 * 1024 * 1024
MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS = 65536


class BoundedModelArtifactRequestError(ValueError):
    """Closed diagnostic for malformed or substituted invocation data."""

    def __init__(self) -> None:
        super().__init__("model_artifact_request_rejected")

    @property
    def reason(self) -> str:
        return "model_artifact_request_rejected"


@dataclass(frozen=True, slots=True)
class BoundedModelArtifactRequestInput:
    """Exact FP32 input bits at a bundle-defined tensor position."""

    tensor_name: str
    tensor_index: int
    shape: tuple[int, ...]
    value_bits: str


@dataclass(frozen=True, slots=True)
class BoundedModelArtifactRequest:
    """Immutable data only; acceptance does not authorize execution."""

    request_digest: str
    bundle_digest: str
    model_digest: str
    model_compilation_digest: str
    backend_bindings_digest: str
    inputs: tuple[BoundedModelArtifactRequestInput, ...]


def _reject() -> NoReturn:
    raise BoundedModelArtifactRequestError()


def _json(value: object) -> bytes:
    data = (
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        + b"\n"
    )
    if len(data) > MAX_MODEL_ARTIFACT_REQUEST_BYTES:
        _reject()
    return data


def _payload(
    bundle: BoundedModelArtifactBundle, inputs: tuple[BoundedModelArtifactRequestInput, ...]
) -> dict[str, object]:
    return {
        "contract": MODEL_ARTIFACT_REQUEST_CONTRACT,
        "bundle_digest": bundle.bundle_digest,
        "model_digest": bundle.model_digest,
        "model_compilation_digest": bundle.model_compilation_digest,
        "backend_bindings_digest": bundle.backend_bindings_digest,
        "inputs": [
            {
                "tensor_name": item.tensor_name,
                "tensor_index": item.tensor_index,
                "shape": list(item.shape),
                "dtype": "float32",
                "value_bits": item.value_bits,
            }
            for item in inputs
        ],
    }


def create_bounded_model_artifact_request(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
) -> bytes:
    """Validate original context and bind fixed plus variable inputs as data."""

    try:
        bundle = validate_bounded_model_artifact_bundle(model_data, backend_bindings, bundle_data)
        if (
            sum(
                prod(item.shape)
                for item in (*bundle.parameter_bindings, *bundle.variable_input_bindings)
            )
            > MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS
        ):
            _reject()
        # Reuse the admitted model input gate: exact names, extents and normal FP32.
        expanded = json.loads(expand_model_inputs(model_data, input_data))["inputs"]
        inputs = tuple(
            BoundedModelArtifactRequestInput(
                item.tensor_name,
                item.tensor_index,
                item.shape,
                b"".join(struct.pack("<f", v) for v in expanded[item.tensor_name]).hex(),
            )
            for item in sorted(
                (*bundle.parameter_bindings, *bundle.variable_input_bindings),
                key=lambda item: item.tensor_index,
            )
        )
        payload = _payload(bundle, inputs)
        return _json({**payload, "request_digest": sha256(_json(payload)).hexdigest()})
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedModelArtifactRequestError() from None


def inspect_bounded_model_artifact_request(
    bundle_data: bytes, request_data: bytes
) -> BoundedModelArtifactRequest:
    """Check untrusted request structure, bits, integrity and bundle binding."""

    try:
        bundle = inspect_bounded_model_artifact_bundle(bundle_data)
        root = _decode(
            request_data,
            max_bytes=MAX_MODEL_ARTIFACT_REQUEST_BYTES,
            max_depth=6,
            max_tokens=2048,
            inputs=False,
        )
        if type(root) is not dict or set(root) != {
            "contract",
            "bundle_digest",
            "model_digest",
            "model_compilation_digest",
            "backend_bindings_digest",
            "inputs",
            "request_digest",
        }:
            _reject()
        records = root["inputs"]
        bindings = sorted(
            (*bundle.parameter_bindings, *bundle.variable_input_bindings),
            key=lambda item: item.tensor_index,
        )
        if sum(prod(item.shape) for item in bindings) > MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS:
            _reject()
        if type(records) is not list or len(records) != len(bindings):
            _reject()
        inputs = []
        for record, binding in zip(records, bindings, strict=True):
            if type(record) is not dict or set(record) != {
                "tensor_name",
                "tensor_index",
                "shape",
                "dtype",
                "value_bits",
            }:
                _reject()
            expected = {
                "tensor_name": binding.tensor_name,
                "tensor_index": binding.tensor_index,
                "shape": list(binding.shape),
                "dtype": "float32",
            }
            for key, value in expected.items():
                if type(record[key]) is not type(value) or record[key] != value:
                    _reject()
            if any(type(d) is not int for d in record["shape"]):
                _reject()
            bits = record["value_bits"]
            if (
                type(bits) is not str
                or len(bits) != 8 * prod(binding.shape)
                or any(char not in "0123456789abcdef" for char in bits)
            ):
                _reject()
            for (number,) in struct.iter_unpack("<I", bytes.fromhex(bits)):
                magnitude = number & 0x7FFFFFFF
                if magnitude >= 0x7F800000 or 0 < magnitude < 0x00800000:
                    _reject()
            if binding.value_bits is not None and not hmac.compare_digest(bits, binding.value_bits):
                _reject()
            inputs.append(
                BoundedModelArtifactRequestInput(
                    binding.tensor_name, binding.tensor_index, binding.shape, bits
                )
            )
        immutable_inputs = tuple(inputs)
        payload = _payload(bundle, immutable_inputs)
        digest = sha256(_json(payload)).hexdigest()
        expected_data = _json({**payload, "request_digest": digest})
        if not hmac.compare_digest(request_data, expected_data):
            _reject()
        return BoundedModelArtifactRequest(
            digest,
            bundle.bundle_digest,
            bundle.model_digest,
            bundle.model_compilation_digest,
            bundle.backend_bindings_digest,
            immutable_inputs,
        )
    except (ValueError, TypeError, OverflowError, RecursionError, struct.error):
        raise BoundedModelArtifactRequestError() from None


def validate_bounded_model_artifact_request(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
    request_data: bytes,
) -> BoundedModelArtifactRequest:
    """Recompute all invocation data from the original model, plan and inputs."""

    value = inspect_bounded_model_artifact_request(bundle_data, request_data)
    expected = create_bounded_model_artifact_request(
        model_data, backend_bindings, bundle_data, input_data
    )
    if not hmac.compare_digest(request_data, expected):
        _reject()
    return value


__all__ = [
    "MODEL_ARTIFACT_REQUEST_CONTRACT",
    "MAX_MODEL_ARTIFACT_REQUEST_BYTES",
    "MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS",
    "BoundedModelArtifactRequest",
    "BoundedModelArtifactRequestInput",
    "BoundedModelArtifactRequestError",
    "create_bounded_model_artifact_request",
    "inspect_bounded_model_artifact_request",
    "validate_bounded_model_artifact_request",
]
