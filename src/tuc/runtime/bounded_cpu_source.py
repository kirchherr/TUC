"""Explicit OCI conversion of bounded source data to validated graph JSON.

The original research parser runs only inside the fixed worker image. User
source is never imported, executed, written into a build context, or parsed on
the host by this runtime. The installed parser implementation is trusted code.
"""

from __future__ import annotations

import ast
import json
import os
import re
import stat
import subprocess
import uuid
from contextlib import suppress
from hashlib import sha256
from pathlib import Path

from tuc.compiler.bounded_cpu_source import (
    BoundedCPUSourceError,
    decode_source_response,
    prepare_source_request,
)
from tuc.runtime import bounded_c11_application as isolated

_MODULES = (
    "source_intent", "source_intent_intake", "triton_source",
    "source_to_intent_research_parser", "source_to_intent_research_kernel_ingress",
    "_isolated_source_ingestion_worker",
)
_STDLIB_IMPORTS = frozenset({
    "__future__", "ast", "json", "os", "resource", "sys", "hashlib", "pathlib", "typing",
    "re", "collections.abc", "dataclasses", "math", "types",
})
_PACKAGE_ROOT = Path(__file__).parent.parent
_MAX_MODULE_BYTES = 65536
_MAX_BUNDLE_BYTES = 524288
_MAX_REQUEST_BYTES = 96 * 1024
_MAX_RESPONSE_BYTES = 256 * 1024
_WORKER = "/opt/tuc/src/tuc/frontend/_isolated_source_ingestion_worker.py"
_PYTHON_IMAGE = (
    "python:3.12-slim-bookworm@sha256:"
    "4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
)
_FRONTEND = (
    "docker/dockerfile:1.7@sha256:"
    "a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e"
)
_RUN = tuple("--entrypoint=/usr/local/bin/python" if value.startswith("--entrypoint=") else value
             for value in isolated._RUN_ARGUMENTS)
_REASONS = frozenset({
    "unsupported_platform", "bundle_rejected", "workspace_rejected", "build_failed",
    "image_rejected", "context_drift", "process_error", "timeout", "output_limit",
    "protocol_rejected", "cleanup_failed",
})
_CONTAINER_NAME = re.compile(r"tuc-source-worker-[0-9a-f]{32}\Z")


class BoundedCPUSourceRuntimeError(ValueError):
    """A closed source-free runtime error, distinct from a checked source rejection."""

    def __init__(self, reason: str) -> None:
        if type(reason) is not str or reason not in _REASONS:
            raise ValueError("invalid bounded CPU source runtime diagnostic")
        self._reason = reason
        super().__init__(reason)

    @property
    def reason(self) -> str:
        return self._reason


def _read_module(path: Path) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("installed parser boundary rejected")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= _MAX_MODULE_BYTES:
            raise ValueError("installed parser file rejected")
        content = bytearray()
        while len(content) <= _MAX_MODULE_BYTES:
            block = os.read(descriptor, min(65536, _MAX_MODULE_BYTES + 1 - len(content)))
            if not block:
                break
            content.extend(block)
        after = os.fstat(descriptor)
        if (len(content) != before.st_size or len(content) > _MAX_MODULE_BYTES or
                (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("installed parser file changed")
        return bytes(content)
    finally:
        os.close(descriptor)


def _verify_imports(name: str, content: bytes) -> None:
    # Only installed, bounded implementation bytes reach ast.parse here.
    tree = ast.parse(content, filename=name + ".py")
    allowed = _STDLIB_IMPORTS | {"tuc.frontend." + item for item in _MODULES}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(item.name not in allowed for item in node.names):
                raise ValueError("installed parser import closure changed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed:
                raise ValueError("installed parser import closure changed")
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
              node.func.id in {"__import__", "eval", "exec", "compile"}):
            raise ValueError("installed parser dynamic code boundary changed")


def _fixed_files() -> tuple[tuple[str, bytes], ...]:
    """Snapshot the six installed modules unchanged with a closed import closure."""
    files: dict[str, bytes] = {}
    for name in _MODULES:
        content = _read_module(_PACKAGE_ROOT / "frontend" / (name + ".py"))
        _verify_imports(name, content)
        files[name + ".py"] = content
    files["tuc-init.py"] = files["frontend-init.py"] = b""
    dockerfile = [
        "# syntax=" + _FRONTEND,
        "FROM --platform=linux/amd64 " + _PYTHON_IMAGE,
        "COPY --chmod=0444 tuc-init.py /opt/tuc/src/tuc/__init__.py",
        "COPY --chmod=0444 frontend-init.py /opt/tuc/src/tuc/frontend/__init__.py",
        *("COPY --chmod=0444 " + name + ".py /opt/tuc/src/tuc/frontend/" + name + ".py"
          for name in _MODULES),
        "USER 10001:10001", "WORKDIR /run/tuc",
        'ENTRYPOINT ["/usr/local/bin/python", "-I", "' + _WORKER + '", "--oci"]',
    ]
    files["Dockerfile"] = ("\n".join(dockerfile) + "\n").encode("ascii")
    files["Dockerfile.dockerignore"] = (
        "**\n!Dockerfile\n!Dockerfile.dockerignore\n!tuc-init.py\n!frontend-init.py\n" +
        "".join("!" + name + ".py\n" for name in _MODULES)
    ).encode("ascii")
    files["bundle.json"] = (json.dumps({
        "schema_version": "tuc.bounded_cpu_source_bundle.v0",
        "python_image": _PYTHON_IMAGE, "dockerfile_frontend": _FRONTEND,
        "sources": {name: sha256(value).hexdigest() for name, value in sorted(files.items())},
        "user_source_included": False,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if sum(map(len, files.values())) > _MAX_BUNDLE_BYTES:
        raise ValueError("installed parser bundle budget rejected")
    return tuple(sorted(files.items()))


def _container_absent(context: isolated._Context, name: str) -> bool:
    """Confirm absence of this exact owned name, never enumerate unrelated runs."""
    try:
        result = isolated._command(
            context, ("container", "ls", "--all", "--format", "{{.Names}}",
                      "--filter", "name=^/" + name + "$"), stdout_limit=80,
        )
        return result.exit_code == 0 and result.stdout == b"" and result.stderr == b""
    except (OSError, ValueError, isolated._ProcessFailure, subprocess.SubprocessError):
        return False


def _cleanup_container(context: isolated._Context, name: str, *, remove: bool) -> bool:
    """Require a positive absence check even when rm fails or --rm already ran."""
    if type(name) is not str or _CONTAINER_NAME.fullmatch(name) is None:
        return False
    if not remove and _container_absent(context, name):
        return True
    with suppress(OSError, ValueError, isolated._ProcessFailure, subprocess.SubprocessError):
        isolated._command(context, ("rm", "--force", name), stdout_limit=80)
    # A missing container may make rm return nonzero; only this independent,
    # successful exact-name lookup proves that cleanup is complete.
    return _container_absent(context, name)


def convert_bounded_cpu_source(source: bytes, signature: bytes, *, workspace: Path) -> bytes:
    """Explicitly convert one source buffer in a fresh, constrained local OCI worker."""
    # Pure byte/shape validation runs before a workspace is touched or an image built.
    request = prepare_source_request(source, signature)
    if type(request) is not bytes or not 1 <= len(request) <= _MAX_REQUEST_BYTES:
        raise BoundedCPUSourceRuntimeError("protocol_rejected")
    context: isolated._Context | None = None
    container = "tuc-source-worker-" + uuid.uuid4().hex
    started = False
    phase = "unsupported_platform"
    try:
        isolated._require_platform()
        phase = "bundle_rejected"
        files = _fixed_files()
        phase = "workspace_rejected"
        context = isolated._make_context(isolated._workspace(workspace), files)
        isolated._write_context(context)
        phase = "build_failed"
        result = isolated._command(
            context, ("build", "--network=none", "--pull=false", "--no-cache", "--tag",
                      context.tag, "--file", "Dockerfile", "-"),
            timeout=isolated.BUILD_TIMEOUT, stdout_limit=isolated.BUILD_LOG_LIMIT,
            stderr_limit=isolated.BUILD_LOG_LIMIT, input_bytes=isolated._build_archive(files),
        )
        if result.exit_code != 0:
            raise ValueError("worker build failed")
        phase = "image_rejected"
        inspected = isolated._command(
            context, ("image", "inspect", "--format", "{{.Id}}", context.tag), stdout_limit=80,
        )
        if inspected.exit_code != 0 or inspected.stderr:
            raise ValueError("worker image inspection rejected")
        image_id = isolated._image_id(inspected.stdout)
        phase = "context_drift"
        isolated._verify_context(context)
        # User input is sent only after the immutable image identity is established.
        started, phase = True, "process_error"
        response = isolated._command(
            context, (*_RUN, "--name", container, image_id, "-I", _WORKER, "--oci"),
            input_bytes=request, timeout=isolated.RUN_TIMEOUT,
            stdout_limit=_MAX_RESPONSE_BYTES, stderr_limit=isolated.STDERR_LIMIT,
        )
        if response.exit_code != 0 or response.stderr:
            raise ValueError("worker diagnostics rejected")
        phase = "protocol_rejected"
        graph = decode_source_response(request, response.stdout)
    except BaseException as error:
        if context is not None:
            container_clean = not started or _cleanup_container(context, container, remove=True)
            context_clean = isolated._cleanup(context)
            if not container_clean or not context_clean:
                raise BoundedCPUSourceRuntimeError("cleanup_failed") from None
        if isinstance(error, BoundedCPUSourceError):
            raise
        if isinstance(error, isolated._ProcessFailure):
            phase = error.reason if error.reason in _REASONS else "process_error"
        elif isinstance(error, subprocess.TimeoutExpired):
            phase = "timeout"
        if isinstance(error, (OSError, ValueError, TypeError, SyntaxError, RecursionError,
                              subprocess.SubprocessError, isolated._ProcessFailure)):
            raise BoundedCPUSourceRuntimeError(phase) from None
        raise
    container_clean = _cleanup_container(context, container, remove=False)
    context_clean = isolated._cleanup(context)
    if not container_clean or not context_clean:
        raise BoundedCPUSourceRuntimeError("cleanup_failed")
    return graph


__all__ = ["BoundedCPUSourceRuntimeError", "convert_bounded_cpu_source"]
