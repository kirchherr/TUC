"""Prepare inert CPU applications and encode/decode their bounded byte protocol.

No subprocess, container, native loader or ordinary runtime admission occurs in
this module. Digests bind bytes and requests; they are not authentication or a
claim that any native execution has taken place.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import NoReturn, cast

from tuc.backends.bounded_c11_application_codegen import (
    BUILD_SH,
    DOCKERFILE,
    DOCKERIGNORE,
    emit_application,
)
from tuc.compiler.bounded_c11 import (
    BoundedC11Entrypoint,
    _artifact_state,
    emit_bounded_c11_entrypoint,
    validate_bounded_c11_entrypoint,
)
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)
from tuc.frontend.source_intent import SourceIntentModule

SCHEMA_VERSION = "tuc.bounded_c11_application.v0"
MAX_APPLICATION_BYTES = 524288
MAX_APPLICATION_MANIFEST_BYTES = 65536
MAX_FRAME_BYTES = 262220
REQUEST_MAGIC = b"TUCIN001"
RESPONSE_MAGIC = b"TUCOUT01"
_TEXT_FIELDS = {"application_c", "application_h", "application_json", "dockerfile",
                "dockerignore", "build_sh", "program_digest"}
_FILE_FIELDS = {"application.c": "application_c", "application.h": "application_h",
                "application.json": "application_json", "Dockerfile": "dockerfile",
                "Dockerfile.dockerignore": "dockerignore", "build.sh": "build_sh"}


class BoundedC11ApplicationExecutionError(ValueError):
    """A validated native error response, distinct from malformed protocol data."""

    __slots__ = ("_status",)
    _status: int

    def __init__(self, status: int) -> None:
        if type(status) is not int or status not in (1, 2, 3):
            raise ValueError("invalid checked C11 application status")
        super().__init__("bounded C11 application returned a checked execution error")
        object.__setattr__(self, "_status", status)

    @property
    def status(self) -> int:
        return self._status

    def __setattr__(self, name: str, value: object) -> None:
        if name in ("status", "_status"):
            raise AttributeError("checked C11 application status is read-only")
        super().__setattr__(name, value)


@dataclass(frozen=True)
class BoundedC11Application:
    """A fixed CPU program described entirely by inspectable bounded text."""

    entrypoint: BoundedC11Entrypoint
    application_c: str
    application_h: str
    application_json: str
    dockerfile: str
    dockerignore: str
    build_sh: str
    program_digest: str

    def files(self) -> dict[str, str]:
        """Return a fresh allowlisted build context, with no execution side effect."""
        return _application_files(self)


def _reject() -> NoReturn:
    raise ValueError("bounded C11 application or protocol rejected")


def _application_files(application: BoundedC11Application) -> dict[str, str]:
    if type(application) is not BoundedC11Application:
        _reject()
    state = object.__getattribute__(application, "__dict__")
    if (type(state) is not dict or len(state) != 8 or
            any(type(key) is not str or len(key) > 32 for key in state) or
            set(state) != _TEXT_FIELDS | {"entrypoint"}):
        _reject()
    for field in _TEXT_FIELDS:
        value = state[field]
        limit = (64 if field == "program_digest" else
                 MAX_APPLICATION_MANIFEST_BYTES if field == "application_json" else
                 MAX_APPLICATION_BYTES)
        if type(value) is not str or len(value) > limit:
            _reject()
        try:
            if len(value.encode("utf-8")) > limit:
                _reject()
        except UnicodeError as error:
            raise ValueError("bounded C11 application text rejected") from error
    program = state["program_digest"]
    if len(program) != 64 or any(char not in "0123456789abcdef" for char in program):
        _reject()
    entrypoint = _artifact_state(state["entrypoint"])
    result = {"entrypoint.h": entrypoint["header"], "entrypoint.c": entrypoint["source"],
              "entrypoint.json": entrypoint["manifest_json"]}
    result.update({name: state[field] for name, field in _FILE_FIELDS.items()})
    if sum(len(value.encode("utf-8")) for value in result.values()) > MAX_APPLICATION_BYTES:
        _reject()
    return result


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False) + "\n"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def prepare_bounded_c11_application(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
) -> BoundedC11Application:
    """Compile and revalidate a supported CPU graph into inert application files."""
    compilation = compile_bounded_source_intent(module, backend_bindings)
    validate_bounded_source_compilation(module, backend_bindings, compilation)
    entrypoint = emit_bounded_c11_entrypoint(module, backend_bindings, compilation)
    validate_bounded_c11_entrypoint(module, backend_bindings, compilation, entrypoint)
    entry_manifest = json.loads(entrypoint.manifest_json)
    inputs = tuple(math.prod(binding.shape) for binding in compilation.input_bindings)
    outputs = tuple(math.prod(binding.shape) for binding in compilation.output_bindings)
    request_bytes, response_bytes = 72 + sum(inputs) * 4, 76 + sum(outputs) * 4
    # Includes main's request/response arrays, process input/output arrays and
    # tensor scratch, with a fixed reserve for bounded bookkeeping. Actual
    # compiler stack frame sizes remain a native toolchain obligation.
    storage_budget = entry_manifest["scratch_bytes"] + 8 * (sum(inputs) + sum(outputs)) + 65536
    if max(request_bytes, response_bytes) > MAX_FRAME_BYTES or storage_budget > 1048576:
        _reject()
    contract = {
        "schema_version": SCHEMA_VERSION,
        "source_intent_digest": compilation.source_intent_digest,
        "backend_bindings_digest": compilation.backend_bindings_digest,
        "entrypoint_symbol": entrypoint.entrypoint_symbol,
        "entrypoint_binding_digest": entry_manifest["binding_digest"],
        "inputs": [asdict(binding) for binding in compilation.input_bindings],
        "outputs": [asdict(binding) for binding in compilation.output_bindings],
        "input_elements": list(inputs), "output_elements": list(outputs),
        "request_bytes": request_bytes, "response_bytes": response_bytes,
        "error_response_bytes": 76,
        "protocol": {
            "request_magic": "TUCIN001", "response_magic": "TUCOUT01",
            "request_layout": "magic8+program32+request32+little-endian-f32-inputs",
            "response_layout": "magic8+program32+request32+little-endian-u32-status+outputs-if-OK",
            "request_digest": "sha256(program_digest_bytes+input_payload)",
            "native_request_digest_validation": "opaque-echo-only; host verifies digest",
            "native_exact_frame_length_before_data": True,
            "native_eof_required_before_execution": True,
            "status_codes": {"OK": 0, "ARGUMENT": 1, "NUMERIC": 2, "ENVIRONMENT": 3},
            "process_exit_codes": {"success": 0, "c11_error": 1, "invalid_protocol": 2},
            "invalid_protocol_response_bytes": 0,
            "digests_are_authentication": False,
        },
        "python_input_type": "exact-dict[str,tuple[float,...]]",
        "numeric_policy": "rounded-binary32-normal-or-signed-zero; nonzero-to-zero rejected",
        "declared_storage_budget_bytes": storage_budget,
        "storage_budget_scope": "fixed arrays plus 64KiB bookkeeping reserve; not measured stack",
        "program_binding": "sha256(canonical-nine-files-with-zero-program-digest)",
        "native_execution_observed": False, "normal_runtime_admission": False,
        "cuda_execution_observed": False, "latency_ns": None, "energy_pj": None,
    }

    def materialize(program_digest: str) -> BoundedC11Application:
        header, source = emit_application(entrypoint.entrypoint_symbol, inputs, outputs,
                                          program_digest)
        contents = {**entrypoint.files(), "application.c": source, "application.h": header,
                    "Dockerfile": DOCKERFILE, "Dockerfile.dockerignore": DOCKERIGNORE,
                    "build.sh": BUILD_SH}
        manifest = {**contract, "program_digest": program_digest,
                    "source_digests": {name: _digest(text) for name, text in contents.items()}}
        return BoundedC11Application(entrypoint, source, header, _json(manifest), DOCKERFILE,
                                      DOCKERIGNORE, BUILD_SH, program_digest)

    template = materialize("0" * 64)
    program_digest = _digest(_json(template.files()))
    application = materialize(program_digest)
    _application_files(application)
    return application


def _validated_manifest(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application,
) -> dict[str, object]:
    actual = _application_files(application)
    fresh = prepare_bounded_c11_application(module, backend_bindings)
    expected = fresh.files()
    for name, text in expected.items():
        if len(actual[name]) != len(text) or actual[name] != text:
            _reject()
    # entrypoint_symbol is not part of entrypoint.files(); compare explicitly.
    supplied_entrypoint = object.__getattribute__(application, "entrypoint")
    supplied_symbol = _artifact_state(supplied_entrypoint)["entrypoint_symbol"]
    if (object.__getattribute__(application, "program_digest") != fresh.program_digest or
            supplied_symbol != fresh.entrypoint.entrypoint_symbol):
        _reject()
    return cast(dict[str, object], json.loads(fresh.application_json))


def validate_bounded_c11_application(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application,
) -> None:
    """Regenerate and compare every bounded field without caller equality hooks."""
    _validated_manifest(module, backend_bindings, application)


def _normal_bits(bits: int) -> bool:
    magnitude = bits & 0x7fffffff
    exponent = magnitude & 0x7f800000
    return magnitude == 0 or exponent not in (0, 0x7f800000)


def _request(
    manifest: dict[str, object], request: bytes,
) -> tuple[bytes, bytes]:
    if type(request) is not bytes or len(request) != manifest["request_bytes"]:
        _reject()
    program = bytes.fromhex(cast(str, manifest["program_digest"]))
    if request[:8] != REQUEST_MAGIC or request[8:40] != program:
        _reject()
    payload = request[72:]
    digest = sha256(program + payload).digest()
    if request[40:72] != digest:
        _reject()
    for (bits,) in struct.iter_unpack("<I", payload):
        if not _normal_bits(bits):
            _reject()
    return program, digest


def encode_bounded_c11_inputs(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application, inputs: dict[str, tuple[float, ...]],
) -> bytes:
    """Encode exact named tensors after full application revalidation.

    Exact Python floats are rounded to binary32; integers, subclasses, NaNs,
    infinities, rounded subnormals and nonzero values rounded to zero reject.
    """
    manifest = _validated_manifest(module, backend_bindings, application)
    expected = cast(list[dict[str, object]], manifest["inputs"])
    sizes = cast(list[int], manifest["input_elements"])
    if (type(inputs) is not dict or len(inputs) != len(expected) or
            any(type(name) is not str or len(name) > 64 for name in inputs) or
            set(inputs) != {item["public_name"] for item in expected}):
        _reject()
    payload = bytearray()
    for item, count in zip(expected, sizes, strict=True):
        values = inputs[cast(str, item["public_name"])]
        if type(values) is not tuple or len(values) != count:
            _reject()
        for value in values:
            if type(value) is not float or not math.isfinite(value):
                _reject()
            try:
                encoded = struct.pack("<f", value)
            except (OverflowError, struct.error) as error:
                raise ValueError("bounded C11 input outside binary32 range") from error
            bits = struct.unpack("<I", encoded)[0]
            if not _normal_bits(bits) or (value != 0.0 and bits & 0x7fffffff == 0):
                _reject()
            payload.extend(encoded)
    program = bytes.fromhex(cast(str, manifest["program_digest"]))
    digest = sha256(program + payload).digest()
    request = REQUEST_MAGIC + program + digest + payload
    _request(manifest, request)
    return request


def decode_bounded_c11_outputs(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...],
    application: BoundedC11Application, request: bytes, response: bytes, exit_code: int,
) -> dict[str, tuple[float, ...]]:
    """Decode only an exact successful response bound to this graph and request.

    A matching response is protocol consistency, not authenticated execution or
    independent numerical correctness evidence. Every native error raises.
    """
    manifest = _validated_manifest(module, backend_bindings, application)
    program, digest = _request(manifest, request)
    if (type(exit_code) is not int or exit_code not in (0, 1, 2) or
            type(response) is not bytes or len(response) not in (76, manifest["response_bytes"])):
        _reject()
    if (response[:8] != RESPONSE_MAGIC or response[8:40] != program or
            response[40:72] != digest):
        _reject()
    status = struct.unpack("<I", response[72:76])[0]
    if status in (1, 2, 3):
        if exit_code != 1 or len(response) != 76:
            _reject()
        raise BoundedC11ApplicationExecutionError(status)
    if status != 0 or exit_code != 0 or len(response) != manifest["response_bytes"]:
        _reject()
    payload = response[76:]
    for (bits,) in struct.iter_unpack("<I", payload):
        if not _normal_bits(bits):
            _reject()
    outputs = cast(list[dict[str, object]], manifest["outputs"])
    sizes = cast(list[int], manifest["output_elements"])
    result = {}
    offset = 0
    for item, count in zip(outputs, sizes, strict=True):
        result[cast(str, item["public_name"])] = tuple(
            value for (value,) in struct.iter_unpack("<f", payload[offset:offset + count * 4]))
        offset += count * 4
    return result


__all__ = ["BoundedC11Application", "BoundedC11ApplicationExecutionError",
           "prepare_bounded_c11_application",
           "validate_bounded_c11_application", "encode_bounded_c11_inputs",
           "decode_bounded_c11_outputs"]
