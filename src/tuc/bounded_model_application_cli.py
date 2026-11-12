"""Explicit portable-model file interface; planning never executes native code."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tuc.backends.bounded_dag import DAGTarget
from tuc.bounded_cpu_application_cli import (
    _RUNTIME_REASONS,
    _CLIError,
    _read_file,
    _require_platform,
    _silence_broken_stdout,
)
from tuc.compiler.bounded_backend_bindings import (
    MAX_BACKEND_BINDINGS_JSON_BYTES,
    BoundedBackendBindingsError,
    backend_bindings_from_json,
)
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_batch import MAX_BATCH_JSON_BYTES, batch_from_json
from tuc.compiler.bounded_cpu_json import MAX_INPUT_JSON_BYTES, source_intent_from_json
from tuc.compiler.bounded_cpu_model import (
    MAX_MODEL_JSON_BYTES,
    expand_model_batch,
    model_from_json,
)
from tuc.compiler.bounded_model_application import prepare_bounded_model_application
from tuc.compiler.bounded_model_artifact_bundle import (
    MAX_MODEL_ARTIFACT_BUNDLE_BYTES,
    BoundedModelArtifactBundleBinding,
    create_bounded_model_artifact_bundle,
    validate_bounded_model_artifact_bundle,
)
from tuc.compiler.bounded_model_artifact_request import (
    MAX_MODEL_ARTIFACT_REQUEST_BYTES,
    create_bounded_model_artifact_request,
)
from tuc.compiler.bounded_source import BoundedBackendBinding

MAX_MODEL_CLI_OUTPUT_BYTES = 4 * 1024 * 1024
_SCHEMA = "tuc.bounded_model_application_cli.v0"
_OPTIONS = {
    "plan": frozenset({"--backends"}),
    "inspect": frozenset({"--backends", "--bundle"}),
    "request": frozenset({"--backends", "--bundle", "--inputs"}),
    "run": frozenset({"--backends", "--bundle", "--inputs", "--request", "--workspace"}),
    "run-batch": frozenset({"--backends", "--bundle", "--batch", "--workspace"}),
}
_HELP = (
    "Usage: tuc-model-app plan MODEL.json --backends BACKENDS.json\n"
    "       tuc-model-app inspect MODEL.json --backends BACKENDS.json --bundle BUNDLE.json\n"
    "       tuc-model-app request MODEL.json --backends BACKENDS.json --bundle BUNDLE.json\n"
    "                     --inputs INPUTS.json\n"
    "       tuc-model-app run MODEL.json --backends BACKENDS.json --bundle BUNDLE.json\n"
    "                     --inputs INPUTS.json --request REQUEST.json --workspace DIR\n"
    "       tuc-model-app run-batch MODEL.json --backends BACKENDS.json --bundle BUNDLE.json\n"
    "                           --batch BATCH.json --workspace DIR\n\n"
    "File commands require Linux x86_64 and bounded regular files.\n"
    "plan, inspect and request never build or execute native code.\n"
    "run and run-batch explicitly authorize the existing isolated C11 runtime.\n"
    "All batch inputs are validated before one build; results publish after cleanup.\n"
)


def _json(value: object) -> bytes:
    data = (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                       separators=(",", ":")).encode("ascii") + b"\n")
    if len(data) > MAX_MODEL_CLI_OUTPUT_BYTES:
        raise _CLIError("output_rejected", 1)
    return data


def _arguments(argv: list[str]) -> tuple[str, str, dict[str, str]] | None:
    if (type(argv) is not list or len(argv) > 12 or
            any(type(value) is not str or not value or "\x00" in value or
                len(value.encode("utf-8")) > 4096 for value in argv)):
        raise _CLIError("arguments_rejected")
    if argv in (["--help"], ["-h"]) or (
        len(argv) == 2 and argv[0] in _OPTIONS and argv[1] == "--help"
    ):
        return None
    if (len(argv) < 2 or argv[0] not in _OPTIONS or argv[1].startswith("-")
            or len(argv) != 2 + 2 * len(_OPTIONS[argv[0]])):
        raise _CLIError("arguments_rejected")
    action, model_path = argv[:2]
    options: dict[str, str] = {}
    for index in range(2, len(argv), 2):
        key, value = argv[index:index + 2]
        if key not in _OPTIONS[action] or key in options or value.startswith("-"):
            raise _CLIError("arguments_rejected")
        options[key] = value
    if set(options) != _OPTIONS[action]:
        raise _CLIError("arguments_rejected")
    return action, model_path, options


def _batch_requests(
    model_data: bytes, bindings: tuple[BoundedBackendBinding, ...], bundle_data: bytes,
    batch_data: bytes,
) -> tuple[tuple[str, bytes, bytes], ...]:
    """Use the existing complete batch gate, including expanded fixed parameters."""
    model = model_from_json(model_data)
    module = source_intent_from_json(model.graph_json)
    application = prepare_bounded_c11_application(module, bindings)
    batch = batch_from_json(
        module, bindings, application, expand_model_batch(model_data, batch_data),
    )
    pending = []
    for item in batch.requests:
        values = dict(item.inputs)
        inputs = _json({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {
            name: values[name] for name in model.variable_inputs
        }})
        request = create_bounded_model_artifact_request(model_data, bindings, bundle_data, inputs)
        prepare_bounded_model_application(model_data, bindings, bundle_data, inputs, request)
        pending.append((item.request_id, inputs, request))
    return tuple(pending)


def _execute(action: str, model_path: str, options: dict[str, str]) -> bytes:
    _require_platform()
    if "--workspace" in options:
        workspace = Path(options["--workspace"])
        if not workspace.is_absolute() or ".." in workspace.parts:
            raise _CLIError("workspace_rejection")
    model_data = _read_file(model_path, MAX_MODEL_JSON_BYTES)
    bindings = backend_bindings_from_json(
        _read_file(options["--backends"], MAX_BACKEND_BINDINGS_JSON_BYTES),
    )
    if action == "plan":
        return create_bounded_model_artifact_bundle(model_data, bindings)
    bundle_data = _read_file(options["--bundle"], MAX_MODEL_ARTIFACT_BUNDLE_BYTES)
    bundle = validate_bounded_model_artifact_bundle(model_data, bindings, bundle_data)
    identity = {
        "model_digest": bundle.model_digest, "bundle_digest": bundle.bundle_digest,
        "model_compilation_digest": bundle.model_compilation_digest,
        "backend_bindings_digest": bundle.backend_bindings_digest,
    }
    if action == "inspect":
        def ports(
            items: tuple[BoundedModelArtifactBundleBinding, ...],
        ) -> list[dict[str, object]]:
            # All items come from the fully reconstructed bundle above.
            return [{"public_name": item.public_name, "tensor_name": item.tensor_name,
                     "tensor_index": item.tensor_index, "shape": list(item.shape),
                     "dtype": item.dtype} for item in items]

        return _json({
            "schema_version": _SCHEMA, "action": action, **identity,
            "parameters": ports(bundle.parameter_bindings),
            "inputs": ports(bundle.variable_input_bindings),
            "outputs": ports(bundle.output_bindings),
            "decision_report": bundle.decision_report,
            "native_execution_observed": False,
        })
    pending: tuple[tuple[str, bytes, bytes], ...]
    if action in {"request", "run"}:
        inputs = _read_file(options["--inputs"], MAX_INPUT_JSON_BYTES)
        if action == "request":
            return create_bounded_model_artifact_request(model_data, bindings, bundle_data, inputs)
        request = _read_file(options["--request"], MAX_MODEL_ARTIFACT_REQUEST_BYTES)
        prepare_bounded_model_application(model_data, bindings, bundle_data, inputs, request)
        pending = (("single", inputs, request),)
    else:
        if any(binding.target is not DAGTarget.C11 for binding in bindings):
            raise _CLIError("model_application_rejected")
        pending = _batch_requests(
            model_data, bindings, bundle_data, _read_file(options["--batch"], MAX_BATCH_JSON_BYTES),
        )
    # Every request and both cumulative element budgets pass before runtime import.
    from tuc.runtime.bounded_model_application_session import (
        BoundedModelApplicationSessionError,
        open_bounded_model_application,
    )

    try:
        results: list[dict[str, object]] = []
        with open_bounded_model_application(
            model_data, bindings, bundle_data, workspace=Path(options["--workspace"]),
        ) as session:
            for request_id, inputs, request in pending:
                result = session.run(inputs, request)
                results.append({"id": request_id, "sequence": result.sequence,
                                "receipt": json.loads(result.result.receipt_data)})
        return _json({
            "schema_version": _SCHEMA, "action": action, **identity,
            "native_execution_observed": True, "results": results,
        })
    except BoundedModelApplicationSessionError as error:
        reason = error.reason if error.reason in _RUNTIME_REASONS | {
            "session_busy", "session_limit", "response_rejected", "runtime_rejected",
        } else "runtime_rejected"
        raise _CLIError(reason, 1) from None
    except _CLIError:
        raise
    except Exception:
        raise _CLIError("runtime_rejected", 1) from None


def _diagnostic(reason: str) -> None:
    try:
        sys.stderr.write("tuc-model-app: " + reason + "\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    """Publish one bounded result after cleanup, or one closed diagnostic."""
    try:
        arguments = _arguments(sys.argv[1:] if argv is None else argv)
        payload = _HELP.encode("ascii") if arguments is None else _execute(*arguments)
        if len(payload) > MAX_MODEL_CLI_OUTPUT_BYTES:
            raise _CLIError("output_rejected", 1)
        sys.stdout.write(payload.decode("ascii"))
        sys.stdout.flush()
        return 0
    except _CLIError as error:
        _diagnostic(error.reason)
        return error.exit_code
    except BoundedBackendBindingsError:
        _diagnostic("backend_bindings_json_rejected")
        return 2
    except BrokenPipeError:
        _silence_broken_stdout()
        _diagnostic("output_unavailable")
        return 1
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        _diagnostic("input_rejected")
        return 2
    except KeyboardInterrupt:
        _diagnostic("interrupted")
        return 1
    except Exception:
        _diagnostic("internal_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
