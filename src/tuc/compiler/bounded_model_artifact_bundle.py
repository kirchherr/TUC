"""Portable, bounded serialization for inert model compiler artifacts.

The bundle is plain canonical JSON. It contains source text and fixed-parameter
bits as data, but it never writes files, compiles source, loads code, or grants
runtime or device authority.
"""

from __future__ import annotations

import hmac
import json
import re
import struct
from dataclasses import dataclass
from hashlib import sha256
from math import prod
from typing import NoReturn, cast

from tuc.backends.bounded_dag import (
    MAX_DAG_ARTIFACT_BYTES,
    MAX_DAG_DIMENSION,
    MAX_DAG_METADATA_BYTES,
    MAX_DAG_NAME_BYTES,
    MAX_DAG_TENSORS,
)
from tuc.compiler.bounded_model_artifacts import (
    MODEL_ARTIFACT_CONTRACT,
    BoundedModelArtifactError,
    compile_bounded_model_artifacts,
    validate_bounded_model_artifacts,
)
from tuc.compiler.bounded_source import BoundedBackendBinding

MODEL_ARTIFACT_BUNDLE_CONTRACT = "tuc.bounded_model_artifact_bundle.v0"
MAX_MODEL_ARTIFACT_BUNDLE_BYTES = 4 * 1024 * 1024
_FILES = frozenset({"generated.c", "generated.h", "kernels.cuh", "manifest.json", "schedule.h"})
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_HEX = re.compile(r"[0-9a-f]+\Z")


class BoundedModelArtifactBundleError(ValueError):
    """Closed diagnostic for malformed or drifted portable bundles."""

    def __init__(self) -> None:
        super().__init__("model_artifact_bundle_rejected")

    @property
    def reason(self) -> str:
        return "model_artifact_bundle_rejected"


@dataclass(frozen=True, slots=True)
class BoundedModelArtifactBundleBinding:
    """One public-to-artifact tensor binding in the portable envelope."""

    public_name: str
    tensor_name: str
    tensor_index: int
    shape: tuple[int, ...]
    dtype: str = "float32"
    value_bits: str | None = None


@dataclass(frozen=True, slots=True)
class BoundedModelArtifactBundleFile:
    """One inert artifact file and its content digest."""

    name: str
    sha256: str
    text: str


@dataclass(frozen=True, slots=True)
class BoundedModelArtifactBundle:
    """Validated in-memory bundle; this is not execution authority."""

    bundle_digest: str
    model_digest: str
    model_compilation_digest: str
    source_intent_digest: str
    backend_bindings_digest: str
    decision_report: str
    parameter_bindings: tuple[BoundedModelArtifactBundleBinding, ...]
    variable_input_bindings: tuple[BoundedModelArtifactBundleBinding, ...]
    output_bindings: tuple[BoundedModelArtifactBundleBinding, ...]
    artifacts: tuple[BoundedModelArtifactBundleFile, ...]

    def files(self) -> dict[str, str]:
        """Return fresh in-memory file data without touching a filesystem."""

        return {item.name: item.text for item in self.artifacts}


def _reject() -> NoReturn:
    raise BoundedModelArtifactBundleError()


def _canonical(value: object) -> bytes:
    data = (
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        + b"\n"
    )
    if len(data) > MAX_MODEL_ARTIFACT_BUNDLE_BYTES:
        _reject()
    return data


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _reject()
        result[key] = value
    return result


def _constant(_: str) -> NoReturn:
    _reject()


def _object(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[object, object], value)) != keys:
        _reject()
    return cast(dict[str, object], value)


def _list(value: object, minimum: int, maximum: int) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _reject()
    return cast(list[object], value)


def _text(value: object, maximum: int, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value) or len(value.encode("utf-8")) > maximum:
        _reject()
    return value


def _digest(value: object, *, prefixed: bool = False) -> str:
    text = _text(value, 71 if prefixed else 64)
    if prefixed:
        if not text.startswith("sha256:"):
            _reject()
        text = text[7:]
    if len(text) != 64 or _HEX.fullmatch(text) is None:
        _reject()
    return ("sha256:" if prefixed else "") + text


def _binding(value: object, *, parameter: bool) -> BoundedModelArtifactBundleBinding:
    keys = {"dtype", "public_name", "shape", "tensor_index", "tensor_name"}
    if parameter:
        keys.add("value_bits")
    item = _object(value, frozenset(keys))
    public_name = _text(item["public_name"], MAX_DAG_NAME_BYTES)
    tensor_name = _text(item["tensor_name"], MAX_DAG_NAME_BYTES)
    if _NAME.fullmatch(public_name) is None or _NAME.fullmatch(tensor_name) is None:
        _reject()
    tensor_index = item["tensor_index"]
    if type(tensor_index) is not int or not 0 <= tensor_index < MAX_DAG_TENSORS:
        _reject()
    raw_shape = _list(item["shape"], 1, 2)
    if any(type(d) is not int or not 1 <= d <= MAX_DAG_DIMENSION for d in raw_shape):
        _reject()
    shape = tuple(cast(list[int], raw_shape))
    if item["dtype"] != "float32" or type(item["dtype"]) is not str:
        _reject()
    bits = None
    if parameter:
        bits = _text(item["value_bits"], 8 * prod(shape))
        if len(bits) != 8 * prod(shape) or _HEX.fullmatch(bits) is None:
            _reject()
    return BoundedModelArtifactBundleBinding(
        public_name, tensor_name, tensor_index, shape, "float32", bits
    )


def _payload(bundle: BoundedModelArtifactBundle) -> dict[str, object]:
    def record(item: BoundedModelArtifactBundleBinding) -> dict[str, object]:
        value = {
            "dtype": item.dtype,
            "public_name": item.public_name,
            "shape": list(item.shape),
            "tensor_index": item.tensor_index,
            "tensor_name": item.tensor_name,
        }
        if item.value_bits is not None:
            value["value_bits"] = item.value_bits
        return value

    return {
        "artifacts": [
            {"name": item.name, "sha256": item.sha256, "text": item.text}
            for item in bundle.artifacts
        ],
        "backend_bindings_digest": bundle.backend_bindings_digest,
        "contract": MODEL_ARTIFACT_BUNDLE_CONTRACT,
        "decision_report": bundle.decision_report,
        "model_artifact_contract": MODEL_ARTIFACT_CONTRACT,
        "model_compilation_digest": bundle.model_compilation_digest,
        "model_digest": bundle.model_digest,
        "output_bindings": [record(item) for item in bundle.output_bindings],
        "parameter_bindings": [record(item) for item in bundle.parameter_bindings],
        "source_intent_digest": bundle.source_intent_digest,
        "variable_input_bindings": [record(item) for item in bundle.variable_input_bindings],
    }


def create_bounded_model_artifact_bundle(
    model_data: bytes, backend_bindings: tuple[BoundedBackendBinding, ...]
) -> bytes:
    """Compile and serialize one deterministic, inert portable bundle."""

    try:
        compiled = compile_bounded_model_artifacts(model_data, backend_bindings)
        validate_bounded_model_artifacts(model_data, backend_bindings, compiled)
        parameters = tuple(
            BoundedModelArtifactBundleBinding(
                item.public_name,
                item.tensor_name,
                item.tensor_index,
                item.shape,
                item.dtype,
                b"".join(struct.pack("<f", number) for number in item.values).hex(),
            )
            for item in compiled.parameter_bindings
        )
        variables = tuple(
            BoundedModelArtifactBundleBinding(
                item.public_name, item.tensor_name, item.tensor_index, item.shape, item.dtype
            )
            for item in compiled.variable_input_bindings
        )
        outputs = tuple(
            BoundedModelArtifactBundleBinding(
                item.public_name, item.tensor_name, item.tensor_index, item.shape, item.dtype
            )
            for item in compiled.source_compilation.output_bindings
        )
        artifacts = tuple(
            BoundedModelArtifactBundleFile(name, sha256(text.encode("utf-8")).hexdigest(), text)
            for name, text in sorted(compiled.source_compilation.artifacts.files().items())
        )
        bundle = BoundedModelArtifactBundle(
            "",
            compiled.model_digest,
            compiled.model_compilation_digest,
            compiled.source_compilation.source_intent_digest,
            compiled.source_compilation.backend_bindings_digest,
            compiled.source_compilation.compilation.dump_decision_report(),
            parameters,
            variables,
            outputs,
            artifacts,
        )
        payload = _payload(bundle)
        digest = sha256(_canonical(payload)).hexdigest()
        return _canonical({**payload, "bundle_digest": digest})
    except BoundedModelArtifactBundleError:
        raise
    except (BoundedModelArtifactError, ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedModelArtifactBundleError() from None


def inspect_bounded_model_artifact_bundle(data: bytes) -> BoundedModelArtifactBundle:
    """Parse and verify one untrusted bundle without executing or writing it."""

    try:
        if type(data) is not bytes or not 1 <= len(data) <= MAX_MODEL_ARTIFACT_BUNDLE_BYTES:
            _reject()
        decoded = json.loads(
            data.decode("ascii"), object_pairs_hook=_pairs, parse_constant=_constant
        )
        root = _object(
            decoded,
            frozenset(
                {
                    "artifacts",
                    "backend_bindings_digest",
                    "bundle_digest",
                    "contract",
                    "decision_report",
                    "model_artifact_contract",
                    "model_compilation_digest",
                    "model_digest",
                    "output_bindings",
                    "parameter_bindings",
                    "source_intent_digest",
                    "variable_input_bindings",
                }
            ),
        )
        if (
            root["contract"] != MODEL_ARTIFACT_BUNDLE_CONTRACT
            or type(root["contract"]) is not str
            or root["model_artifact_contract"] != MODEL_ARTIFACT_CONTRACT
            or type(root["model_artifact_contract"]) is not str
        ):
            _reject()
        parameters = tuple(
            _binding(item, parameter=True)
            for item in _list(root["parameter_bindings"], 1, MAX_DAG_TENSORS)
        )
        variables = tuple(
            _binding(item, parameter=False)
            for item in _list(root["variable_input_bindings"], 1, MAX_DAG_TENSORS)
        )
        outputs = tuple(
            _binding(item, parameter=False)
            for item in _list(root["output_bindings"], 1, MAX_DAG_TENSORS)
        )
        inputs = parameters + variables
        if (
            len({item.tensor_index for item in inputs}) != len(inputs)
            or len({item.tensor_name for item in inputs}) != len(inputs)
            or len({item.public_name for item in inputs}) != len(inputs)
            or len({item.tensor_index for item in outputs}) != len(outputs)
            or len({item.tensor_name for item in outputs}) != len(outputs)
            or len({item.public_name for item in outputs}) != len(outputs)
        ):
            _reject()
        raw_files = _list(root["artifacts"], len(_FILES), len(_FILES))
        files = []
        total = 0
        for value in raw_files:
            item = _object(value, frozenset({"name", "sha256", "text"}))
            name = _text(item["name"], MAX_DAG_NAME_BYTES)
            text = _text(item["text"], MAX_DAG_ARTIFACT_BYTES)
            total += len(text.encode("utf-8"))
            digest = _digest(item["sha256"])
            if digest != sha256(text.encode("utf-8")).hexdigest():
                _reject()
            files.append(BoundedModelArtifactBundleFile(name, digest, text))
        if {item.name for item in files} != _FILES or total > MAX_DAG_ARTIFACT_BYTES:
            _reject()
        if tuple(item.name for item in files) != tuple(sorted(_FILES)):
            _reject()
        bundle = BoundedModelArtifactBundle(
            _digest(root["bundle_digest"]),
            _digest(root["model_digest"]),
            _digest(root["model_compilation_digest"]),
            _digest(root["source_intent_digest"], prefixed=True),
            _digest(root["backend_bindings_digest"], prefixed=True),
            _text(root["decision_report"], MAX_DAG_METADATA_BYTES),
            parameters,
            variables,
            outputs,
            tuple(files),
        )
        payload = _payload(bundle)
        if bundle.bundle_digest != sha256(_canonical(payload)).hexdigest():
            _reject()
        if data != _canonical({**payload, "bundle_digest": bundle.bundle_digest}):
            _reject()
        return bundle
    except BoundedModelArtifactBundleError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ):
        raise BoundedModelArtifactBundleError() from None


def validate_bounded_model_artifact_bundle(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    data: bytes,
) -> BoundedModelArtifactBundle:
    """Bind an untrusted bundle back to its original model and capabilities."""

    value = inspect_bounded_model_artifact_bundle(data)
    try:
        expected = create_bounded_model_artifact_bundle(model_data, backend_bindings)
        if not hmac.compare_digest(data, expected):
            _reject()
        return value
    except BoundedModelArtifactBundleError:
        raise
    except (BoundedModelArtifactError, ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedModelArtifactBundleError() from None


__all__ = [
    "MODEL_ARTIFACT_BUNDLE_CONTRACT",
    "MAX_MODEL_ARTIFACT_BUNDLE_BYTES",
    "BoundedModelArtifactBundle",
    "BoundedModelArtifactBundleBinding",
    "BoundedModelArtifactBundleError",
    "BoundedModelArtifactBundleFile",
    "create_bounded_model_artifact_bundle",
    "inspect_bounded_model_artifact_bundle",
    "validate_bounded_model_artifact_bundle",
]
