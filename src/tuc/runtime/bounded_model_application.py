"""Explicit execution adapter using only the existing isolated Linux C11 runtime."""

from __future__ import annotations

import hmac
from pathlib import Path

from tuc.compiler.bounded_model_application import (
    BoundedModelApplicationResult,
    decode_bounded_model_application_response,
    prepare_bounded_model_application,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.runtime.bounded_c11_application import (
    BoundedC11ApplicationRuntimeError,
    build_bounded_c11_application,
)


def run_bounded_model_application(
    model_data: bytes,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    bundle_data: bytes,
    input_data: bytes,
    request_data: bytes,
    *,
    workspace: Path,
) -> BoundedModelApplicationResult:
    """Validate before building, run the exact frame, decode and release resources.

    This call explicitly authorizes the existing fixed Linux CPU build/run
    boundary. No source, command, endpoint or image override is accepted.
    Protocol receipts retain their conservative non-provenance flag; only the
    trusted runtime call observes process execution, not arbitrary receipt bytes.
    """
    prepared = prepare_bounded_model_application(
        model_data, backend_bindings, bundle_data, input_data, request_data
    )
    with build_bounded_c11_application(
        prepared.module, backend_bindings, workspace=workspace
    ) as handle:
        if not hmac.compare_digest(handle.program_digest, prepared.application.program_digest):
            raise BoundedC11ApplicationRuntimeError("graph_drift")
        response = handle.run_frame(prepared.request_frame)
        return decode_bounded_model_application_response(
            model_data, backend_bindings, bundle_data, input_data, request_data, response, 0
        )


__all__ = ["run_bounded_model_application"]
