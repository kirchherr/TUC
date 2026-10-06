"""Capability-planned inert artifacts for an existing bounded model.

The model remains data. This module validates its graph and fixed FP32 values,
uses the existing bounded Source Intent compiler, and binds the resulting source
artifacts to the model without compiling or executing generated code.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from hashlib import sha256
from typing import NoReturn

from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.compiler.bounded_cpu_model import BoundedCPUModelError, model_from_json
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    BoundedSourceCompilation,
    BoundedTensorBinding,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)

MODEL_ARTIFACT_CONTRACT = "tuc.bounded_model_artifacts.v0"


class BoundedModelArtifactError(ValueError):
    """Closed diagnostic for the complete model-to-artifact boundary."""

    def __init__(self) -> None:
        super().__init__("model_artifact_rejected")

    @property
    def reason(self) -> str:
        return "model_artifact_rejected"


@dataclass(frozen=True, slots=True)
class BoundedModelParameterBinding:
    """One fixed FP32 input at its exact generated-artifact tensor position."""

    public_name: str
    tensor_name: str
    tensor_index: int
    shape: tuple[int, ...]
    values: tuple[float, ...]
    dtype: str = "float32"


@dataclass(frozen=True, slots=True)
class BoundedModelArtifacts:
    """Inspectable data-only model compilation; never execution authority."""

    model_digest: str
    model_compilation_digest: str
    source_compilation: BoundedSourceCompilation
    parameter_bindings: tuple[BoundedModelParameterBinding, ...]
    variable_input_bindings: tuple[BoundedTensorBinding, ...]


def _reject() -> NoReturn:
    raise BoundedModelArtifactError()


def _parameter(
    binding: BoundedTensorBinding, values: tuple[float, ...]
) -> BoundedModelParameterBinding:
    if len(values) != _elements(binding.shape):
        _reject()
    return BoundedModelParameterBinding(
        binding.public_name,
        binding.tensor_name,
        binding.tensor_index,
        binding.shape,
        values,
        binding.dtype,
    )


def _elements(shape: tuple[int, ...]) -> int:
    result = 1
    for dimension in shape:
        result *= dimension
    return result


def _binding_record(binding: BoundedTensorBinding) -> dict[str, object]:
    return {
        "dtype": binding.dtype,
        "public_name": binding.public_name,
        "shape": list(binding.shape),
        "tensor_index": binding.tensor_index,
        "tensor_name": binding.tensor_name,
    }


def _compilation_digest(
    model_digest: str,
    source: BoundedSourceCompilation,
    parameters: tuple[BoundedModelParameterBinding, ...],
    variables: tuple[BoundedTensorBinding, ...],
) -> str:
    files = source.artifacts.files()
    payload = {
        "artifact_sha256": {
            name: sha256(text.encode("utf-8")).hexdigest() for name, text in sorted(files.items())
        },
        "backend_bindings_digest": source.backend_bindings_digest,
        "contract": MODEL_ARTIFACT_CONTRACT,
        "model_digest": model_digest,
        "outputs": [_binding_record(item) for item in source.output_bindings],
        "parameters": [
            {
                **_binding_record(
                    BoundedTensorBinding(
                        item.public_name,
                        item.tensor_name,
                        item.tensor_index,
                        item.shape,
                        item.dtype,
                    )
                ),
                "value_bits": b"".join(struct.pack("<f", value) for value in item.values).hex(),
            }
            for item in parameters
        ],
        "source_intent_digest": source.source_intent_digest,
        "variable_inputs": [_binding_record(item) for item in variables],
    }
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def _match_tensor_bindings(value: object, expected: tuple[BoundedTensorBinding, ...]) -> bool:
    if type(value) is not tuple or len(value) != len(expected):
        return False
    for item, wanted in zip(value, expected, strict=True):
        if (
            type(item) is not BoundedTensorBinding
            or type(item.public_name) is not str
            or type(item.tensor_name) is not str
            or type(item.tensor_index) is not int
            or type(item.shape) is not tuple
            or any(type(dimension) is not int for dimension in item.shape)
            or type(item.dtype) is not str
            or item.public_name != wanted.public_name
            or item.tensor_name != wanted.tensor_name
            or item.tensor_index != wanted.tensor_index
            or item.shape != wanted.shape
            or item.dtype != wanted.dtype
        ):
            return False
    return True


def _match_parameter_bindings(
    value: object, expected: tuple[BoundedModelParameterBinding, ...]
) -> bool:
    if type(value) is not tuple or len(value) != len(expected):
        return False
    for item, wanted in zip(value, expected, strict=True):
        if (
            type(item) is not BoundedModelParameterBinding
            or type(item.public_name) is not str
            or type(item.tensor_name) is not str
            or type(item.tensor_index) is not int
            or type(item.shape) is not tuple
            or any(type(dimension) is not int for dimension in item.shape)
            or type(item.values) is not tuple
            or any(type(number) is not float for number in item.values)
            or type(item.dtype) is not str
            or item.public_name != wanted.public_name
            or item.tensor_name != wanted.tensor_name
            or item.tensor_index != wanted.tensor_index
            or item.shape != wanted.shape
            or item.values != wanted.values
            or item.dtype != wanted.dtype
        ):
            return False
    return True


def compile_bounded_model_artifacts(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
) -> BoundedModelArtifacts:
    """Plan and emit inert source artifacts for a validated fixed-parameter model."""

    try:
        model = model_from_json(model_data)
        module = source_intent_from_json(model.graph_json)
        source = compile_bounded_source_intent(module, backend_bindings)
        fixed = dict(model.parameters)
        by_name = {item.tensor_name: item for item in source.input_bindings}
        if set(by_name) != set(fixed) | set(model.variable_inputs):
            _reject()
        parameters = tuple(
            _parameter(item, fixed[item.tensor_name])
            for item in source.input_bindings
            if item.tensor_name in fixed
        )
        variables = tuple(
            item for item in source.input_bindings if item.tensor_name in model.variable_inputs
        )
        if {item.tensor_name for item in parameters} != set(fixed) or tuple(
            item.tensor_name for item in variables
        ) != tuple(
            item.tensor_name
            for item in source.input_bindings
            if item.tensor_name in model.variable_inputs
        ):
            _reject()
        digest = _compilation_digest(model.model_digest, source, parameters, variables)
        return BoundedModelArtifacts(model.model_digest, digest, source, parameters, variables)
    except BoundedModelArtifactError:
        raise
    except (BoundedCPUModelError, ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedModelArtifactError() from None


def validate_bounded_model_artifacts(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    value: BoundedModelArtifacts,
) -> None:
    """Rebuild and match every field before model artifacts cross a trust boundary."""

    try:
        if type(value) is not BoundedModelArtifacts:
            _reject()
        expected = compile_bounded_model_artifacts(model_data, backend_bindings)
        if type(value.source_compilation) is not BoundedSourceCompilation:
            _reject()
        module = source_intent_from_json(model_from_json(model_data).graph_json)
        validate_bounded_source_compilation(module, backend_bindings, value.source_compilation)
        if (
            type(value.model_digest) is not str
            or type(value.model_compilation_digest) is not str
            or value.model_digest != expected.model_digest
            or value.model_compilation_digest != expected.model_compilation_digest
            or not _match_parameter_bindings(value.parameter_bindings, expected.parameter_bindings)
            or not _match_tensor_bindings(
                value.variable_input_bindings, expected.variable_input_bindings
            )
        ):
            _reject()
    except BoundedModelArtifactError:
        raise
    except (BoundedCPUModelError, ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedModelArtifactError() from None


__all__ = [
    "MODEL_ARTIFACT_CONTRACT",
    "BoundedModelArtifactError",
    "BoundedModelArtifacts",
    "BoundedModelParameterBinding",
    "compile_bounded_model_artifacts",
    "validate_bounded_model_artifacts",
]
