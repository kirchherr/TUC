"""Explicit Linux file CLI for the bounded CPU application; imports are inert."""

from __future__ import annotations

import json
import math
import os
import platform
import stat
import sys
from pathlib import Path
from typing import cast

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import (
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_cpu_batch import (
    MAX_BATCH_JSON_BYTES,
    BoundedCPUBatchError,
    batch_from_json,
)
from tuc.compiler.bounded_cpu_json import (
    MAX_GRAPH_JSON_BYTES,
    MAX_INPUT_JSON_BYTES,
    BoundedCPUJSONError,
    inputs_from_json,
    source_intent_from_json,
)
from tuc.compiler.bounded_cpu_model import (
    MAX_MODEL_JSON_BYTES,
    BoundedCPUModelError,
    expand_model_batch,
    expand_model_inputs,
    model_from_json,
    pack_model,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

MAX_OUTPUT_JSON_BYTES = 2 * 1024 * 1024
_MAX_PATH_BYTES = 4096
_SCHEMA = "tuc.bounded_cpu_cli.v0"
_HELP = (
    "Usage: tuc-cpu-app inspect GRAPH.json\n"
    "       tuc-cpu-app run GRAPH.json --inputs INPUTS.json --workspace DIR\n"
    "       tuc-cpu-app run-batch GRAPH.json --batch BATCH.json --workspace DIR\n"
    "       tuc-cpu-app pack-model GRAPH.json --parameters INPUTS.json\n"
    "       tuc-cpu-app inspect-model MODEL.json\n"
    "       tuc-cpu-app run-model MODEL.json --inputs INPUTS.json --workspace DIR\n"
    "       tuc-cpu-app run-model-batch MODEL.json --batch BATCH.json --workspace DIR\n"
    "       tuc-cpu-app --help\n\n"
    "File commands require Linux x86_64. inspect is execution-free.\n"
    "run explicitly builds and executes an isolated local CPU application.\n"
    "run-batch validates all requests, builds once, and executes them sequentially.\n"
)
_RUNTIME_REASONS = frozenset({
    "argument_rejection", "numeric_rejection", "environment_rejection", "protocol_rejection",
    "process_error", "timeout", "output_limit", "build_failed", "image_rejected",
    "cleanup_failed", "workspace_rejection", "context_drift", "graph_drift",
    "application_rejection", "input_rejection", "unsupported_platform", "closed",
    "handle_rejected",
})


class _CLIError(ValueError):
    def __init__(self, reason: str, exit_code: int = 2) -> None:
        self.reason, self.exit_code = reason, exit_code
        super().__init__(reason)


def cpu_bindings(*, softmax: bool = False) -> tuple[BoundedBackendBinding, ...]:
    """Return the fixed CPU capability, retaining legacy bindings without Softmax."""
    if type(softmax) is not bool:
        raise ValueError("bounded CPU capability rejected")
    operations = {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    if softmax:
        operations.add(OperationKind.SOFTMAX)
    return (BoundedBackendBinding(BackendCapability(
        "json_cpu", frozenset(operations),
        memory_domain=MemoryDomainKind.HOST_RAM,
    ), DAGTarget.C11),)


def _arguments(argv: list[str]) -> tuple[str, str, str | None, str | None]:
    if (type(argv) is not list or len(argv) > 6 or
            any(type(value) is not str or not value or len(value) > _MAX_PATH_BYTES or
                "\x00" in value for value in argv)):
        raise _CLIError("arguments_rejected")
    if argv in (["--help"], ["-h"], ["inspect", "--help"], ["run", "--help"],
                ["run-batch", "--help"], ["pack-model", "--help"],
                ["inspect-model", "--help"], ["run-model", "--help"],
                ["run-model-batch", "--help"]):
        return "help", "", None, None
    if len(argv) == 2 and argv[0] in {"inspect", "inspect-model"} and not argv[1].startswith("-"):
        return argv[0], argv[1], None, None
    if (len(argv) == 4 and argv[0] == "pack-model" and argv[2] == "--parameters" and
            not argv[1].startswith("-") and not argv[3].startswith("-")):
        return argv[0], argv[1], argv[3], None
    if (len(argv) == 6 and argv[0] in {"run", "run-batch", "run-model", "run-model-batch"}
            and not argv[1].startswith("-")):
        input_flag = "--batch" if argv[0] in {"run-batch", "run-model-batch"} else "--inputs"
        options: dict[str, str] = {}
        for index in (2, 4):
            key, value = argv[index:index + 2]
            if key not in {input_flag, "--workspace"} or key in options or value.startswith("-"):
                raise _CLIError("arguments_rejected")
            options[key] = value
        if set(options) == {input_flag, "--workspace"}:
            return argv[0], argv[1], options[input_flag], options["--workspace"]
    raise _CLIError("arguments_rejected")


def _require_platform() -> None:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise _CLIError("unsupported_platform")


def _metadata(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _read_file(value: str, limit: int) -> bytes:
    """Open each path component without following links; read only a bounded regular fd."""
    _require_platform()
    path = Path(value)
    if ".." in path.parts or len(value.encode("utf-8")) > _MAX_PATH_BYTES:
        raise _CLIError("file_rejected")
    path = path.absolute()
    if path.anchor != "/" or len(path.parts) < 2:
        raise _CLIError("file_rejected")
    directory = descriptor = -1
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open("/", directory_flags)
        for component in path.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                             os.O_CLOEXEC, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= limit:
            raise _CLIError("file_rejected")
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
        if (len(data) > limit or len(data) != before.st_size or
                not stat.S_ISREG(after.st_mode) or _metadata(before) != _metadata(after)):
            raise _CLIError("file_rejected")
        return bytes(data)
    except (OSError, ValueError, UnicodeError):
        raise _CLIError("file_rejected") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory >= 0:
            os.close(directory)


def _json_bytes(value: dict[str, object]) -> bytes:
    text = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n"
    if len(text) > MAX_OUTPUT_JSON_BYTES:
        raise _CLIError("output_rejected", 1)
    return text.encode("ascii")


def _checked_outputs(value: object, manifest: dict[str, object]) -> dict[str, list[float]]:
    bindings = cast(list[dict[str, object]], manifest["outputs"])
    sizes = cast(list[int], manifest["output_elements"])
    if type(value) is not dict or list(value) != [item["public_name"] for item in bindings]:
        raise _CLIError("output_rejected", 1)
    result: dict[str, list[float]] = {}
    for item, count in zip(bindings, sizes, strict=True):
        name = cast(str, item["public_name"])
        values = value[name]
        if (type(values) is not tuple or len(values) != count or
                any(type(number) is not float or not math.isfinite(number) for number in values)):
            raise _CLIError("output_rejected", 1)
        result[name] = list(values)
    return result


def _execute(action: str, graph_path: str, input_path: str | None,
             workspace: str | None) -> bytes:
    _require_platform()
    if action == "pack-model":
        assert input_path is not None
        return pack_model(_read_file(graph_path, MAX_GRAPH_JSON_BYTES),
                          _read_file(input_path, MAX_INPUT_JSON_BYTES))
    model_data = None
    model = None
    identity: dict[str, object] = {}
    if action in {"inspect-model", "run-model", "run-model-batch"}:
        model_data = _read_file(graph_path, MAX_MODEL_JSON_BYTES)
        model = model_from_json(model_data)
        module = source_intent_from_json(model.graph_json)
        identity = {"model_digest": model.model_digest}
    else:
        module = source_intent_from_json(_read_file(graph_path, MAX_GRAPH_JSON_BYTES))
    bindings = cpu_bindings(softmax=any(op.family == "softmax" for op in module.operations))
    try:
        application = prepare_bounded_c11_application(module, bindings)
    except (ValueError, TypeError, OverflowError):
        raise _CLIError("graph_rejected") from None
    manifest = cast(dict[str, object], json.loads(application.application_json))
    if action in {"inspect", "inspect-model"}:
        input_bindings = cast(list[dict[str, object]], manifest["inputs"])
        if model is not None:
            fixed = dict(model.parameters)
            identity["parameters"] = [item for item in input_bindings
                                      if item["public_name"] in fixed]
            input_bindings = [item for item in input_bindings if item["public_name"] not in fixed]
        return _json_bytes({
            "schema_version": "tuc.bounded_cpu_model_cli.v0" if model else _SCHEMA,
            "action": action, **identity,
            "program_digest": application.program_digest,
            "inputs": input_bindings, "outputs": manifest["outputs"],
            "native_execution_observed": False,
        })
    assert input_path is not None and workspace is not None
    if action in {"run-batch", "run-model-batch"}:
        batch_data = _read_file(input_path, MAX_BATCH_JSON_BYTES)
        if model_data is not None:
            batch_data = expand_model_batch(model_data, batch_data)
        batch = batch_from_json(module, bindings, application, batch_data)
        # Every request passes pure validation before importing the opt-in runtime.
        from tuc.runtime.bounded_c11_application import (
            BoundedC11ApplicationRuntimeError,
            build_bounded_c11_application,
        )
        try:
            results: list[dict[str, object]] = []
            with build_bounded_c11_application(
                    module, bindings, workspace=Path(workspace)) as built:
                for item in batch.requests:
                    checked = _checked_outputs(built.run(item.values()), manifest)
                    results.append({"id": item.request_id, "request_digest": item.request_digest,
                                    "outputs": checked})
            return _json_bytes({
                "schema_version": ("tuc.bounded_cpu_model_batch_cli.v0" if model else
                                   "tuc.bounded_cpu_batch_cli.v0"),
                "action": action, **identity,
                "program_digest": batch.program_digest, "batch_digest": batch.batch_digest,
                "results": results, "native_execution_observed": True,
            })
        except BoundedC11ApplicationRuntimeError as error:
            reason = error.reason if error.reason in _RUNTIME_REASONS else "runtime_rejected"
            raise _CLIError(reason, 1) from None
        except _CLIError:
            raise
        except (OSError, ValueError, TypeError, OverflowError):
            raise _CLIError("runtime_rejected", 1) from None
    input_data = _read_file(input_path, MAX_INPUT_JSON_BYTES)
    if model_data is not None:
        input_data = expand_model_inputs(model_data, input_data)
    inputs = inputs_from_json(module, bindings, application, input_data)
    request = encode_bounded_c11_inputs(module, bindings, application, inputs)
    # Import the opt-in runtime only after both data boundaries have passed.
    from tuc.runtime.bounded_c11_application import (
        BoundedC11ApplicationRuntimeError,
        build_bounded_c11_application,
    )
    try:
        with build_bounded_c11_application(module, bindings, workspace=Path(workspace)) as built:
            outputs = built.run(inputs)
        checked = _checked_outputs(outputs, manifest)
        return _json_bytes({
            "schema_version": "tuc.bounded_cpu_model_cli.v0" if model else _SCHEMA,
            "action": action, **identity,
            "program_digest": application.program_digest,
            "request_digest": request[40:72].hex(), "outputs": checked,
            "native_execution_observed": True,
        })
    except BoundedC11ApplicationRuntimeError as error:
        reason = error.reason if error.reason in _RUNTIME_REASONS else "runtime_rejected"
        raise _CLIError(reason, 1) from None
    except _CLIError:
        raise
    except (OSError, ValueError, TypeError, OverflowError):
        raise _CLIError("runtime_rejected", 1) from None


def _diagnostic(reason: str) -> None:
    # Only closed constant reasons reach here, never exception text or argv.
    try:
        sys.stderr.write("tuc-cpu-app: " + reason + "\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def _silence_broken_stdout() -> None:
    # Prevent Python's shutdown flush from printing a second broken-pipe traceback.
    descriptor = -1
    try:
        descriptor = os.open(os.devnull, os.O_WRONLY)
        os.dup2(descriptor, sys.stdout.fileno())
    except (OSError, ValueError):
        pass
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    """Run the explicit command and return its closed exit code."""
    try:
        arguments = _arguments(sys.argv[1:] if argv is None else argv)
        payload = _HELP.encode("ascii") if arguments[0] == "help" else _execute(*arguments)
        sys.stdout.write(payload.decode("ascii"))
        sys.stdout.flush()
        return 0
    except _CLIError as error:
        _diagnostic(error.reason)
        return error.exit_code
    except BoundedCPUJSONError as error:
        reason = (error.reason if error.reason in {"graph_json_rejected", "input_json_rejected"}
                  else "json_rejected")
        _diagnostic(reason)
        return 2
    except BoundedCPUBatchError:
        _diagnostic("batch_json_rejected")
        return 2
    except BoundedCPUModelError:
        _diagnostic("model_json_rejected")
        return 2
    except BrokenPipeError:
        _silence_broken_stdout()
        _diagnostic("output_unavailable")
        return 1
    except (OSError, ValueError, TypeError, OverflowError):
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
