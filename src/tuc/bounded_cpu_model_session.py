"""Explicit, bounded Python sessions over the existing isolated CPU runtime.

Import and open are inert. Only run() may build or execute; callers must close
the session, preferably with a context manager. No native weights stay resident.
"""

from __future__ import annotations

import json
import math
import struct
import threading
import weakref
from _thread import LockType
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Self

from tuc.bounded_cpu_application_cli import cpu_bindings
from tuc.compiler.bounded_c11_application import (
    BoundedC11Application,
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_cpu_json import inputs_from_json, source_intent_from_json
from tuc.compiler.bounded_cpu_model import expand_model_inputs, model_from_json
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import SourceIntentModule

if TYPE_CHECKING:
    from tuc.runtime.bounded_c11_application import BuiltBoundedC11Application

MAX_SESSION_REQUESTS = 16
MAX_SESSION_ELEMENTS = 65536
_RUNTIME_REASONS = frozenset(
    {
        "argument_rejection",
        "numeric_rejection",
        "environment_rejection",
        "protocol_rejection",
        "process_error",
        "timeout",
        "output_limit",
        "build_failed",
        "image_rejected",
        "cleanup_failed",
        "workspace_rejection",
        "context_drift",
        "graph_drift",
        "application_rejection",
        "input_rejection",
        "unsupported_platform",
        "closed",
        "handle_rejected",
    }
)


class CPUModelSessionError(ValueError):
    """Closed session diagnostic; never includes caller data or process logs."""

    def __init__(self, reason: str) -> None:
        allowed = _RUNTIME_REASONS | {
            "session_busy",
            "session_limit",
            "output_rejected",
            "runtime_rejected",
        }
        self.reason = reason if reason in allowed else "runtime_rejected"
        super().__init__(self.reason)


@dataclass(frozen=True, slots=True)
class CPUModelResult:
    """One completed request; data only, not session or execution authority."""

    model_digest: str
    program_digest: str
    request_digest: str
    sequence: int
    outputs: tuple[tuple[str, tuple[float, ...]], ...]


@dataclass
class _Session:
    model_data: bytes
    model_digest: str
    module: SourceIntentModule
    bindings: tuple[BoundedBackendBinding, ...]
    application: BoundedC11Application
    workspace: Path
    output_sizes: tuple[tuple[str, int], ...]
    built: BuiltBoundedC11Application | None = None
    closed: bool = False
    requests: int = 0
    inputs_used: int = 0
    outputs_used: int = 0
    lock: LockType = field(default_factory=threading.Lock)


def _checked_outputs(
    value: object, sizes: tuple[tuple[str, int], ...]
) -> tuple[tuple[str, tuple[float, ...]], ...]:
    if type(value) is not dict or list(value) != [name for name, _ in sizes]:
        raise CPUModelSessionError("output_rejected")
    result = []
    for name, size in sizes:
        numbers = value[name]
        if type(numbers) is not tuple or len(numbers) != size:
            raise CPUModelSessionError("output_rejected")
        for number in numbers:
            if type(number) is not float or not math.isfinite(number):
                raise CPUModelSessionError("output_rejected")
            try:
                encoded = struct.pack("<f", number)
                bits = struct.unpack("<I", encoded)[0] & 0x7FFFFFFF
                if (bits != 0 and bits < 0x00800000) or struct.unpack("<f", encoded)[0] != number:
                    raise CPUModelSessionError("output_rejected")
            except (OverflowError, struct.error):
                raise CPUModelSessionError("output_rejected") from None
        result.append((name, numbers))
    return tuple(result)


def _close(record: _Session) -> None:
    record.closed = True
    if record.built is not None:
        try:
            record.built.close()
        except Exception:
            # Retain the handle so explicit close() can retry failed cleanup.
            raise CPUModelSessionError("cleanup_failed") from None
        record.built = None


class CPUModelSession:
    """Factory-only handle. Concurrent operations reject instead of overlapping."""

    __slots__ = ("__weakref__",)

    def __new__(cls) -> Self:
        raise TypeError("use open_cpu_model")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("CPU model sessions cannot be subclassed")

    @property
    def model_digest(self) -> str:
        return _lookup(self).model_digest

    @property
    def program_digest(self) -> str:
        return _lookup(self).application.program_digest

    def __enter__(self) -> Self:
        if _lookup(self).closed:
            raise CPUModelSessionError("closed")
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        record = _lookup(self)
        if not record.lock.acquire(blocking=False):
            raise CPUModelSessionError("session_busy")
        try:
            _close(record)
        finally:
            record.lock.release()

    def run(self, input_data: bytes) -> CPUModelResult:
        """Validate, lazily build once, then execute one independently isolated run.

        Invalid input and budget rejections leave the session usable. Once native
        work starts, any failure closes it. Earlier results remain valid. Unlike
        the batch CLI, results are published per call, before session cleanup.
        """
        record = _lookup(self)
        if not record.lock.acquire(blocking=False):
            raise CPUModelSessionError("session_busy")
        try:
            if record.closed:
                raise CPUModelSessionError("closed")
            if record.requests >= MAX_SESSION_REQUESTS:
                raise CPUModelSessionError("session_limit")
            data = expand_model_inputs(record.model_data, input_data)
            values = inputs_from_json(record.module, record.bindings, record.application, data)
            request = encode_bounded_c11_inputs(
                record.module, record.bindings, record.application, values
            )
            input_count = sum(len(v) for v in values.values())
            output_count = sum(size for _, size in record.output_sizes)
            if (
                record.inputs_used + input_count > MAX_SESSION_ELEMENTS
                or record.outputs_used + output_count > MAX_SESSION_ELEMENTS
            ):
                raise CPUModelSessionError("session_limit")
            # Complete pure validation precedes even importing the opt-in runtime.
            from tuc.runtime.bounded_c11_application import (
                BoundedC11ApplicationRuntimeError,
                build_bounded_c11_application,
            )

            try:
                if record.built is None:
                    record.built = build_bounded_c11_application(
                        record.module, record.bindings, workspace=record.workspace
                    )
                    if record.built.program_digest != record.application.program_digest:
                        raise CPUModelSessionError("graph_drift")
                outputs = _checked_outputs(record.built.run(values), record.output_sizes)
                record.requests += 1
                record.inputs_used += input_count
                record.outputs_used += output_count
                return CPUModelResult(
                    record.model_digest,
                    record.application.program_digest,
                    request[40:72].hex(),
                    record.requests,
                    outputs,
                )
            except BaseException as error:
                _close(record)
                if isinstance(error, CPUModelSessionError):
                    raise
                if isinstance(error, BoundedC11ApplicationRuntimeError):
                    raise CPUModelSessionError(error.reason) from None
                if isinstance(error, Exception):
                    raise CPUModelSessionError("runtime_rejected") from None
                raise
        finally:
            record.lock.release()


_REGISTRY: weakref.WeakKeyDictionary[CPUModelSession, _Session] = weakref.WeakKeyDictionary()


def _lookup(handle: CPUModelSession) -> _Session:
    if type(handle) is not CPUModelSession or handle not in _REGISTRY:
        raise CPUModelSessionError("handle_rejected")
    return _REGISTRY[handle]


def open_cpu_model(model_data: bytes, *, workspace: Path) -> CPUModelSession:
    """Validate inert model bytes; defer workspace access and build until run()."""
    if type(workspace) is not type(Path()):
        raise CPUModelSessionError("workspace_rejection")
    model = model_from_json(model_data)
    module = source_intent_from_json(model.graph_json)
    bindings = cpu_bindings(softmax=any(op.family == "softmax" for op in module.operations))
    application = prepare_bounded_c11_application(module, bindings)
    manifest = json.loads(application.application_json)
    sizes = tuple(
        (item["public_name"], size)
        for item, size in zip(manifest["outputs"], manifest["output_elements"], strict=True)
    )
    handle = object.__new__(CPUModelSession)
    _REGISTRY[handle] = _Session(
        model.model_json, model.model_digest, module, bindings, application, workspace, sizes
    )
    return handle


__all__ = ["CPUModelSession", "CPUModelResult", "CPUModelSessionError", "open_cpu_model"]
