"""Explicit source-to-JSON conversion in the fixed isolated parser container."""

from __future__ import annotations

import sys
from pathlib import Path

from tuc.bounded_cpu_application_cli import (
    _CLIError,
    _read_file,
    _require_platform,
    _silence_broken_stdout,
)
from tuc.compiler.bounded_cpu_json import MAX_GRAPH_JSON_BYTES, source_intent_from_json
from tuc.compiler.bounded_cpu_source import (
    MAX_SIGNATURE_BYTES,
    MAX_SOURCE_BYTES,
    BoundedCPUSourceError,
    prepare_source_request,
)

_HELP = (
    "Usage: tuc-source-to-json SOURCE.py --signature SIGNATURE.json --workspace DIR\n"
    "       tuc-source-to-json --help\n\n"
    "Explicit bounded research conversion on Linux x86_64 using local Docker.\n"
    "Source is parsed as data in the isolated worker; it is never executed.\n"
    "Graph JSON is written to stdout after validation and cleanup.\n"
)
_REASONS = frozenset({
    "source_rejected", "signature_rejected", "protocol_rejected", "graph_rejected",
    "unsupported_platform", "workspace_rejected", "context_drift", "build_failed",
    "image_rejected", "process_error", "timeout", "output_limit", "cleanup_failed",
    "environment_rejection", "input_rejection", "worker_rejected", "bundle_rejected",
})


def _arguments(argv: list[str]) -> tuple[str, str, str] | None:
    if (type(argv) is not list or len(argv) > 5 or
            any(type(value) is not str or not value or len(value) > 4096 or
                "\x00" in value for value in argv)):
        raise _CLIError("arguments_rejected")
    if argv in (["--help"], ["-h"]):
        return None
    if len(argv) != 5 or argv[0].startswith("-"):
        raise _CLIError("arguments_rejected")
    options: dict[str, str] = {}
    for index in (1, 3):
        key, value = argv[index:index + 2]
        if (key not in {"--signature", "--workspace"} or key in options or
                value.startswith("-")):
            raise _CLIError("arguments_rejected")
        options[key] = value
    if set(options) != {"--signature", "--workspace"}:
        raise _CLIError("arguments_rejected")
    return argv[0], options["--signature"], options["--workspace"]


def _execute(source_path: str, signature_path: str, workspace: str) -> bytes:
    _require_platform()
    source = _read_file(source_path, MAX_SOURCE_BYTES)
    signature = _read_file(signature_path, MAX_SIGNATURE_BYTES)
    prepare_source_request(source, signature)
    # The process-owning runtime is loaded only after both file boundaries pass.
    from tuc.runtime.bounded_cpu_source import convert_bounded_cpu_source

    result = convert_bounded_cpu_source(source, signature, workspace=Path(workspace))
    if type(result) is not bytes or len(result) > MAX_GRAPH_JSON_BYTES:
        raise _CLIError("output_rejected", 1)
    try:
        source_intent_from_json(result)
        if not result.endswith(b"\n") or result.count(b"\n") != 1:
            raise ValueError("output framing")
        result.decode("ascii")
    except (ValueError, TypeError, UnicodeError):
        raise _CLIError("output_rejected", 1) from None
    return result


def _diagnostic(reason: str) -> None:
    try:
        sys.stderr.write("tuc-source-to-json: " + reason + "\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    """Publish one complete graph, or a closed diagnostic and no graph."""
    try:
        arguments = _arguments(sys.argv[1:] if argv is None else argv)
        payload = _HELP.encode("ascii") if arguments is None else _execute(*arguments)
        sys.stdout.write(payload.decode("ascii"))
        sys.stdout.flush()
        return 0
    except _CLIError as error:
        _diagnostic(error.reason)
        return error.exit_code
    except BoundedCPUSourceError as error:
        reason = error.reason if error.reason in _REASONS else "source_rejected"
        _diagnostic(reason)
        return 2
    except BrokenPipeError:
        _silence_broken_stdout()
        _diagnostic("output_unavailable")
        return 1
    except KeyboardInterrupt:
        _diagnostic("interrupted")
        return 1
    except Exception as error:
        # Runtime reasons are considered only for the exact fixed runtime error class.
        # This import happens on the failure path, never when displaying help.
        from tuc.runtime.bounded_cpu_source import BoundedCPUSourceRuntimeError

        if type(error) is BoundedCPUSourceRuntimeError:
            reason = error.reason if error.reason in _REASONS else "worker_rejected"
            _diagnostic(reason)
        else:
            _diagnostic("internal_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
