"""Lazy, bounded reuse of the existing explicit CPU model application runtime."""

from __future__ import annotations

import hmac
import json
import threading
import weakref
from _thread import LockType
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Self

from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.compiler.bounded_cpu_model import model_from_json
from tuc.compiler.bounded_model_application import (
    BoundedModelApplication,
    BoundedModelApplicationError,
    BoundedModelApplicationResult,
    decode_bounded_model_application_response,
    prepare_bounded_model_application,
)
from tuc.compiler.bounded_model_artifact_bundle import validate_bounded_model_artifact_bundle
from tuc.compiler.bounded_source import BoundedBackendBinding

if TYPE_CHECKING:
    from tuc.runtime.bounded_c11_application import BuiltBoundedC11Application

MAX_SESSION_REQUESTS = 16
MAX_SESSION_ELEMENTS = 65536
_REASONS = frozenset({
    "session_busy", "session_limit", "closed", "handle_rejected", "workspace_rejection",
    "context_drift", "graph_drift", "cleanup_failed", "response_rejected", "runtime_rejected",
    "unsupported_platform", "application_rejection", "input_rejection", "build_failed",
    "image_rejected", "argument_rejection", "numeric_rejection", "environment_rejection",
    "protocol_rejection", "process_error", "timeout", "output_limit",
})


class BoundedModelApplicationSessionError(ValueError):
    """Closed diagnostics; never forwards process logs or caller-controlled text."""

    def __init__(self, reason: str) -> None:
        self.reason = reason if reason in _REASONS else "runtime_rejected"
        super().__init__(self.reason)


@dataclass(frozen=True, slots=True)
class BoundedModelApplicationSessionResult:
    """One checked result and its local sequence; neither is runtime authority."""

    sequence: int
    result: BoundedModelApplicationResult


@dataclass(frozen=True, slots=True)
class _Context:
    model: str
    bundle: str
    compilation: str
    bindings: str
    program: str
    output_elements: int


def _context(
    model_data: bytes, bindings: tuple[BoundedBackendBinding, ...], bundle_data: bytes,
) -> _Context:
    try:
        bundle = validate_bounded_model_artifact_bundle(model_data, bindings, bundle_data)
        if any(binding.target is not DAGTarget.C11 for binding in bindings):
            raise BoundedModelApplicationError()
        model = model_from_json(model_data)
        module = source_intent_from_json(model.graph_json)
        application = prepare_bounded_c11_application(module, bindings)
        sizes = json.loads(application.application_json)["output_elements"]
        return _Context(
            bundle.model_digest, bundle.bundle_digest, bundle.model_compilation_digest,
            bundle.backend_bindings_digest, application.program_digest, sum(sizes),
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedModelApplicationError() from None


def _matches(prepared: BoundedModelApplication, context: _Context) -> bool:
    return (
        prepared.model_digest == context.model and prepared.bundle_digest == context.bundle
        and prepared.model_compilation_digest == context.compilation
        and prepared.backend_bindings_digest == context.bindings
        and prepared.application.program_digest == context.program
    )


@dataclass
class _Session:
    model_data: bytes
    bindings: tuple[BoundedBackendBinding, ...]
    bundle_data: bytes
    workspace: Path
    context: _Context
    built: BuiltBoundedC11Application | None = None
    closed: bool = False
    requests: int = 0
    inputs_used: int = 0
    outputs_used: int = 0
    lock: LockType = field(default_factory=threading.Lock)


def _close(record: _Session) -> None:
    record.closed = True
    if record.built is not None:
        try:
            record.built.close()
        except Exception:
            # Keep the handle so explicit close() can retry cleanup.
            raise BoundedModelApplicationSessionError("cleanup_failed") from None
        record.built = None


class BoundedModelApplicationSession:
    """Factory-only session. Open/enter/close-before-run are inert."""

    __slots__ = ("__weakref__",)

    def __new__(cls) -> Self:
        raise TypeError("use open_bounded_model_application")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("model application sessions cannot be subclassed")

    def __enter__(self) -> Self:
        if _lookup(self).closed:
            raise BoundedModelApplicationSessionError("closed")
        return self

    def __exit__(
        self, exception_type: type[BaseException] | None, exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        record = _lookup(self)
        if not record.lock.acquire(blocking=False):
            raise BoundedModelApplicationSessionError("session_busy")
        try:
            _close(record)
        finally:
            record.lock.release()

    def run(self, input_data: bytes, request_data: bytes) -> BoundedModelApplicationSessionResult:
        """Validate each request, lazily build once, and bind each checked response."""
        record = _lookup(self)
        if not record.lock.acquire(blocking=False):
            raise BoundedModelApplicationSessionError("session_busy")
        try:
            if record.closed:
                raise BoundedModelApplicationSessionError("closed")
            if record.requests >= MAX_SESSION_REQUESTS:
                raise BoundedModelApplicationSessionError("session_limit")
            try:
                fresh_context = _context(record.model_data, record.bindings, record.bundle_data)
                if fresh_context != record.context:
                    raise BoundedModelApplicationError()
            except BoundedModelApplicationError:
                _close(record)
                raise BoundedModelApplicationSessionError("context_drift") from None
            # Invalid input or a substituted request cannot trigger a build/run.
            prepared = prepare_bounded_model_application(
                record.model_data, record.bindings, record.bundle_data, input_data, request_data,
            )
            if not _matches(prepared, record.context):
                _close(record)
                raise BoundedModelApplicationSessionError("context_drift")
            input_elements = sum(len(values) for _, values in prepared.input_values)
            output_elements = record.context.output_elements
            if (
                record.inputs_used + input_elements > MAX_SESSION_ELEMENTS
                or record.outputs_used + output_elements > MAX_SESSION_ELEMENTS
            ):
                raise BoundedModelApplicationSessionError("session_limit")
            from tuc.runtime.bounded_c11_application import (
                BoundedC11ApplicationRuntimeError,
                build_bounded_c11_application,
            )

            try:
                if record.built is None:
                    record.built = build_bounded_c11_application(
                        prepared.module, record.bindings, workspace=record.workspace,
                    )
                if not hmac.compare_digest(record.built.program_digest, record.context.program):
                    raise BoundedModelApplicationSessionError("graph_drift")
                response = record.built.run_frame(prepared.request_frame)
                result = decode_bounded_model_application_response(
                    record.model_data, record.bindings, record.bundle_data,
                    input_data, request_data, response, 0,
                )
            except BaseException as error:
                _close(record)
                if isinstance(error, BoundedModelApplicationSessionError):
                    raise
                if isinstance(error, BoundedC11ApplicationRuntimeError):
                    raise BoundedModelApplicationSessionError(error.reason) from None
                if isinstance(error, BoundedModelApplicationError):
                    raise BoundedModelApplicationSessionError("response_rejected") from None
                if isinstance(error, Exception):
                    raise BoundedModelApplicationSessionError("runtime_rejected") from None
                raise
            record.requests += 1
            record.inputs_used += input_elements
            record.outputs_used += output_elements
            return BoundedModelApplicationSessionResult(record.requests, result)
        finally:
            record.lock.release()


_REGISTRY: weakref.WeakKeyDictionary[BoundedModelApplicationSession, _Session] = (
    weakref.WeakKeyDictionary()
)


def _lookup(handle: BoundedModelApplicationSession) -> _Session:
    if type(handle) is not BoundedModelApplicationSession or handle not in _REGISTRY:
        raise BoundedModelApplicationSessionError("handle_rejected")
    return _REGISTRY[handle]


def open_bounded_model_application(
    model_data: bytes, backend_bindings: tuple[BoundedBackendBinding, ...], bundle_data: bytes,
    *, workspace: Path,
) -> BoundedModelApplicationSession:
    """Validate fixed CPU context without I/O; only run() can build or execute."""
    if (
        type(workspace) is not type(Path()) or not workspace.is_absolute()
        or ".." in workspace.parts
    ):
        raise BoundedModelApplicationSessionError("workspace_rejection")
    context = _context(model_data, backend_bindings, bundle_data)
    handle = object.__new__(BoundedModelApplicationSession)
    _REGISTRY[handle] = _Session(model_data, backend_bindings, bundle_data, workspace, context)
    return handle


__all__ = [
    "MAX_SESSION_REQUESTS", "MAX_SESSION_ELEMENTS", "BoundedModelApplicationSessionError",
    "BoundedModelApplicationSessionResult", "BoundedModelApplicationSession",
    "open_bounded_model_application",
]
