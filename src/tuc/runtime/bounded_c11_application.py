"""Explicit, isolated Linux CPU execution of a freshly prepared C11 application.

Importing this module never starts a process. Build/run/close are explicit caller
actions, separate from normal backend discovery and runtime admission. Callers
must close handles, preferably by using the context manager.
"""

from __future__ import annotations

import io
import json
import os
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
import weakref
from _thread import LockType
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Self, cast

from tuc.compiler.bounded_c11_application import (
    MAX_FRAME_BYTES,
    BoundedC11Application,
    BoundedC11ApplicationExecutionError,
    decode_bounded_c11_outputs,
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
    validate_bounded_c11_application,
)
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    _checked_bindings,
    _checked_module,
)
from tuc.frontend.source_intent import SourceIntentModule

TRUSTED_PATH = "/usr/local/bin:/usr/bin:/bin"
DOCKER_ENDPOINT = "unix:///var/run/docker.sock"
BUILD_TIMEOUT = 600.0
RUN_TIMEOUT = 30.0
CONTROL_TIMEOUT = 10.0
BUILD_LOG_LIMIT = 2 * 1024 * 1024
STDERR_LIMIT = 4096
_FILES = frozenset({"entrypoint.h", "entrypoint.c", "entrypoint.json", "application.h",
                    "application.c", "application.json", "Dockerfile", "Dockerfile.dockerignore",
                    "build.sh"})
_CONTEXT_LIMIT = 524288
_TREE_LIMIT = 256
_TREE_DEPTH = 8


class BoundedC11ApplicationRuntimeError(ValueError):
    """Closed runtime diagnostic; process logs and host paths are never included."""

    def __init__(self, reason: str) -> None:
        self._reason = reason
        super().__init__("bounded C11 runtime rejected: " + reason)

    @property
    def reason(self) -> str:
        return self._reason


class _ProcessFailure(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class _ProcessResult:
    exit_code: int
    stdout: bytes
    stderr: bytes


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        with suppress(OSError):
            process.kill()
    with suppress(OSError, subprocess.TimeoutExpired):
        process.wait(timeout=1.0)


def _bounded_process(
    arguments: tuple[str, ...], *, cwd: Path, environment: dict[str, str],
    input_bytes: bytes | None = None, timeout: float,
    stdout_limit: int, stderr_limit: int,
) -> _ProcessResult:
    """Multiplex bounded pipes; never buffer arbitrary output with communicate()."""
    if (type(input_bytes) not in (bytes, type(None)) or
            (input_bytes is not None and len(input_bytes) > 1048576)):
        raise _ProcessFailure("input_rejection")
    process = subprocess.Popen(
        arguments, cwd=cwd, env=environment, close_fds=True, start_new_session=True,
        stdin=subprocess.DEVNULL if input_bytes is None else subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    selector: selectors.BaseSelector | None = None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    streams: list[BinaryIO] = []
    offset = 0
    deadline = time.monotonic() + timeout
    try:
        selector = selectors.DefaultSelector()
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            if stream is None:
                raise _ProcessFailure("process_error")
            streams.append(cast(BinaryIO, stream))
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if process.stdin is not None:
            streams.append(cast(BinaryIO, process.stdin))
            os.set_blocking(process.stdin.fileno(), False)
            if input_bytes:
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _ProcessFailure("timeout")
            for key, _ in selector.select(min(remaining, 0.1)):
                stream = cast(BinaryIO, key.fileobj)
                if key.data == "stdin":
                    assert input_bytes is not None
                    try:
                        offset += os.write(stream.fileno(), input_bytes[offset:offset + 65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    if offset == len(input_bytes):
                        selector.unregister(stream)
                        stream.close()
                    continue
                name = cast(str, key.data)
                try:
                    read_size = min(65536, limits[name] - len(buffers[name]) + 1)
                    chunk = os.read(stream.fileno(), read_size)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                elif len(buffers[name]) + len(chunk) > limits[name]:
                    raise _ProcessFailure("output_limit")
                else:
                    buffers[name].extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _ProcessFailure("timeout")
        exit_code = process.wait(timeout=remaining)
        return _ProcessResult(exit_code, bytes(buffers["stdout"]), bytes(buffers["stderr"]))
    except BaseException:
        _terminate(process)
        raise
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and stream not in streams:
                stream.close()
        for stream in streams:
            stream.close()


def _require_platform() -> None:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise BoundedC11ApplicationRuntimeError("unsupported_platform")


def _uid() -> int:
    return os.getuid()


def _identity(path: Path) -> tuple[int, int]:
    value = path.lstat()
    return value.st_dev, value.st_ino


def _owned_directory(path: Path) -> tuple[int, int]:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("directory boundary rejected")
    value = path.lstat()
    if (not stat.S_ISDIR(value.st_mode) or value.st_uid != _uid() or
            value.st_mode & 0o022):
        raise ValueError("owned private directory required")
    return value.st_dev, value.st_ino


def _workspace(value: Path) -> Path:
    if type(value) is not type(Path()) or ".." in value.parts:
        raise ValueError("workspace rejected")
    path = value.absolute()
    _owned_directory(path)
    if path.resolve() != path:
        raise ValueError("workspace boundary rejected")
    return path


def _docker() -> tuple[Path, tuple[int, int, int, int]]:
    found = shutil.which("docker", path=TRUSTED_PATH)
    if found is None:
        raise ValueError("Docker executable unavailable")
    path = Path(found).resolve(strict=True)
    value = path.stat()
    if (not stat.S_ISREG(value.st_mode) or value.st_uid != 0 or
            value.st_mode & 0o022 or not os.access(path, os.X_OK)):
        raise ValueError("trusted Docker executable required")
    for parent in path.parents:
        metadata = parent.stat()
        if metadata.st_uid != 0 or metadata.st_mode & 0o022:
            raise ValueError("trusted Docker path required")
    return path, (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


@dataclass(frozen=True)
class _Context:
    workspace: Path
    directory: Path
    source: Path
    config: Path
    identities: tuple[tuple[int, int], ...]
    docker: Path
    docker_identity: tuple[int, int, int, int]
    files: tuple[tuple[str, bytes], ...]
    tag: str


@dataclass
class _Lifecycle:
    lock: LockType = field(default_factory=threading.Lock)
    closed: bool = False
    image_removed: bool = False
    files_removed: bool = False


@dataclass(frozen=True)
class _Record:
    context: _Context
    image_id: str
    module: SourceIntentModule
    bindings: tuple[BoundedBackendBinding, ...]
    original_module: SourceIntentModule
    original_bindings: tuple[BoundedBackendBinding, ...]
    application: BoundedC11Application
    response_bytes: int
    lifecycle: _Lifecycle = field(default_factory=_Lifecycle)


def _prefix(context: _Context) -> tuple[str, ...]:
    return (str(context.docker), f"--host={DOCKER_ENDPOINT}", "--config", str(context.config))


def _environment(context: _Context) -> dict[str, str]:
    return {"PATH": TRUSTED_PATH, "HOME": str(context.config), "LANG": "C", "LC_ALL": "C",
            "DOCKER_BUILDKIT": "1"}


def _command(
    context: _Context, arguments: tuple[str, ...], *, timeout: float = CONTROL_TIMEOUT,
    stdout_limit: int = 1024, stderr_limit: int = STDERR_LIMIT, input_bytes: bytes | None = None,
) -> _ProcessResult:
    # Every invocation has an empty credential/config home, including cleanup.
    # Docker/buildx may write its own metadata; it is discarded after that call.
    parent_id = _owned_directory(context.config)
    config = Path(tempfile.mkdtemp(prefix="invoke.", dir=context.config))
    invocation = replace(context, config=config)
    cleanup = replace(context, workspace=context.config, directory=config,
                      identities=(parent_id, _owned_directory(config), (0, 0), (0, 0)))
    try:
        result = _bounded_process(
            _prefix(invocation) + arguments, cwd=context.directory,
            environment=_environment(invocation), input_bytes=input_bytes,
            timeout=timeout, stdout_limit=stdout_limit, stderr_limit=stderr_limit,
        )
    except BaseException:
        with suppress(OSError, ValueError):
            _remove_files(cleanup)
        raise
    else:
        _remove_files(cleanup)
        return result


def _checked_files(application: BoundedC11Application) -> tuple[tuple[str, bytes], ...]:
    files = application.files()
    if (type(files) is not dict or any(type(name) is not str for name in files) or
            set(files) != _FILES or any(type(text) is not str for text in files.values())):
        raise ValueError("application file set rejected")
    result = tuple((name, files[name].encode("utf-8")) for name in sorted(files))
    if sum(len(value) for _, value in result) > _CONTEXT_LIMIT:
        raise ValueError("application file budget rejected")
    return result


def _make_context(workspace: Path, files: tuple[tuple[str, bytes], ...]) -> _Context:
    docker, docker_identity = _docker()
    directory = Path(tempfile.mkdtemp(prefix="tuc-c11-application.", dir=workspace))
    source, config = directory / "source", directory / "docker-config"
    context = _Context(workspace, directory, source, config,
                       (_owned_directory(workspace), _owned_directory(directory), (0, 0), (0, 0)),
                       docker, docker_identity, files, "tuc-c11-application:" + uuid.uuid4().hex)
    try:
        source.mkdir(mode=0o700)
        config.mkdir(mode=0o700)
        return replace(context, identities=(*context.identities[:2], _owned_directory(source),
                                            _owned_directory(config)))
    except BaseException:
        with suppress(OSError, ValueError):
            _remove_files(context)
        raise


def _build_archive(files: tuple[tuple[str, bytes], ...]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, value in files:
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(value), 0o600
            archive.addfile(info, io.BytesIO(value))
    result = output.getvalue()
    if len(result) > 1048576:
        raise ValueError("build context budget rejected")
    return result


def _verify_context(context: _Context, *, contents: bool = True) -> None:
    paths = (context.workspace, context.directory, context.source, context.config)
    if tuple(_owned_directory(path) for path in paths) != context.identities:
        raise ValueError("application directory changed")
    if _docker() != (context.docker, context.docker_identity):
        raise ValueError("Docker executable changed")
    if any(context.config.iterdir()):
        raise ValueError("Docker config directory changed")
    if contents:
        names: set[str] = set()
        for item in context.source.iterdir():
            if len(names) >= len(context.files) or item.is_symlink() or not item.is_file():
                raise ValueError("application file coverage changed")
            names.add(item.name)
        if names != {name for name, _ in context.files}:
            raise ValueError("application file coverage changed")
        for name, expected in context.files:
            path = context.source / name
            if path.stat().st_size != len(expected):
                raise ValueError("application source changed")
            with path.open("rb") as stream:
                if stream.read(len(expected) + 1) != expected:
                    raise ValueError("application source changed")


def _write_context(context: _Context) -> None:
    _verify_context(context, contents=False)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    directory = os.open(context.source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, value in context.files:
            descriptor = os.open(name, flags, 0o600, dir_fd=directory)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(value)
    finally:
        os.close(directory)


def _remove_files(context: _Context) -> None:
    """Bounded descriptor-relative cleanup cannot follow replaced path components."""
    if (_owned_directory(context.workspace) != context.identities[0] or
            _owned_directory(context.directory) != context.identities[1]):
        raise ValueError("cleanup boundary changed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    workspace_fd = os.open(context.workspace, flags)
    try:
        workspace_stat = os.fstat(workspace_fd)
        if (workspace_stat.st_dev, workspace_stat.st_ino) != context.identities[0]:
            raise ValueError("cleanup workspace changed")
        root_fd = os.open(context.directory.name, flags, dir_fd=workspace_fd)
    except BaseException:
        os.close(workspace_fd)
        raise
    budget = [_TREE_LIMIT]

    def clear(directory_fd: int, depth: int) -> None:
        if depth > _TREE_DEPTH:
            raise ValueError("cleanup depth exceeded")
        with os.scandir(directory_fd) as iterator:
            for item in iterator:
                budget[0] -= 1
                if budget[0] < 0:
                    raise ValueError("cleanup file count exceeded")
                metadata = os.stat(item.name, dir_fd=directory_fd, follow_symlinks=False)
                if metadata.st_uid != _uid() or stat.S_ISLNK(metadata.st_mode):
                    raise ValueError("cleanup file ownership rejected")
                if stat.S_ISDIR(metadata.st_mode):
                    child_fd = os.open(item.name, flags, dir_fd=directory_fd)
                    try:
                        current = os.fstat(child_fd)
                        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
                            raise ValueError("cleanup directory changed")
                        clear(child_fd, depth + 1)
                    finally:
                        os.close(child_fd)
                    current = os.stat(item.name, dir_fd=directory_fd, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
                        raise ValueError("cleanup directory changed")
                    os.rmdir(item.name, dir_fd=directory_fd)
                elif stat.S_ISREG(metadata.st_mode):
                    os.unlink(item.name, dir_fd=directory_fd)
                else:
                    raise ValueError("cleanup file type rejected")
    try:
        root = os.fstat(root_fd)
        if (root.st_dev, root.st_ino) != context.identities[1]:
            raise ValueError("cleanup root changed")
        clear(root_fd, 0)
        current = os.stat(context.directory.name, dir_fd=workspace_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != context.identities[1]:
            raise ValueError("cleanup root changed")
        os.rmdir(context.directory.name, dir_fd=workspace_fd)
    finally:
        os.close(root_fd)
        os.close(workspace_fd)


def _remove_container(context: _Context, name: str) -> None:
    with suppress(OSError, ValueError, _ProcessFailure, subprocess.SubprocessError):
        _command(context, ("rm", "--force", name))


def _cleanup(context: _Context, lifecycle: _Lifecycle | None = None) -> bool:
    state = lifecycle if lifecycle is not None else _Lifecycle()
    if not state.image_removed:
        try:
            result = _command(context, ("image", "rm", "--no-prune", context.tag))
            if result.exit_code != 0:
                # A previous interrupted cleanup may already have removed this tag.
                listed = _command(context, ("image", "ls", "--quiet", "--no-trunc",
                                            "--filter", "reference=" + context.tag))
                if listed.exit_code != 0 or listed.stdout or listed.stderr:
                    return False
            state.image_removed = True
        except (OSError, ValueError, _ProcessFailure, subprocess.SubprocessError):
            return False
    if not state.files_removed:
        try:
            if _owned_directory(context.workspace) != context.identities[0]:
                return False
            if context.directory.exists() or context.directory.is_symlink():
                _remove_files(context)
            state.files_removed = True
        except (OSError, ValueError):
            return False
    return True


def _image_id(value: bytes) -> str:
    if re.fullmatch(rb"sha256:[0-9a-f]{64}\n?", value) is None:
        raise ValueError("image identity rejected")
    return value.decode("ascii").removesuffix("\n")


_RUN_ARGUMENTS = (
    "run", "--rm", "--pull=never", "--network=none", "--read-only", "--user=10001:10001",
    "--workdir=/run/tuc", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
    "--pids-limit=32", "--memory=1g", "--memory-swap=1g", "--cpus=1", "--ipc=private",
    "--shm-size=16m", "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m", "--ulimit=core=0",
    "--ulimit=nofile=64:64", "--ulimit=fsize=1048576:1048576", "--log-driver=none",
    "--entrypoint=/opt/tuc/application", "-i",
)


class BuiltBoundedC11Application:
    """An identity-checked explicit runtime handle; use build(), then close()."""

    __slots__ = ("__weakref__",)

    def __new__(cls) -> Self:
        raise TypeError("bounded C11 handles require the build function")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("bounded C11 runtime handles cannot be subclassed")

    @property
    def program_digest(self) -> str:
        return _lookup(self).application.program_digest

    def __enter__(self) -> Self:
        record = _lookup(self)
        if record.lifecycle.closed:
            raise BoundedC11ApplicationRuntimeError("closed")
        return self

    def __exit__(
        self, exception_type: type[BaseException] | None, exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def run(self, inputs: dict[str, tuple[float, ...]]) -> dict[str, tuple[float, ...]]:
        record = _lookup(self)
        with record.lifecycle.lock:
            if record.lifecycle.closed:
                raise BoundedC11ApplicationRuntimeError("closed")
            container = "tuc-c11-application-" + uuid.uuid4().hex
            started = False
            phase = "context_drift"
            try:
                _require_platform()
                _verify_context(record.context)
                # Reconstruct again: the original objects are never trusted after
                # build, and mutations cannot select another program/image.
                phase = "graph_drift"
                module = _checked_module(record.original_module)
                bindings = _checked_bindings(record.original_bindings)
                validate_bounded_c11_application(module, bindings, record.application)
                phase = "input_rejection"
                request = encode_bounded_c11_inputs(record.module, record.bindings,
                                                    record.application, inputs)
                started = True
                phase = "process_error"
                result = _command(record.context,
                                  (*_RUN_ARGUMENTS, "--name", container, record.image_id),
                                  timeout=RUN_TIMEOUT, stdout_limit=record.response_bytes,
                                  stderr_limit=STDERR_LIMIT, input_bytes=request)
                if result.stderr:
                    raise ValueError("unexpected execution diagnostics")
                phase = "protocol_rejection"
                return decode_bounded_c11_outputs(record.module, record.bindings,
                                                  record.application, request, result.stdout,
                                                  result.exit_code)
            except BaseException as error:
                if started:
                    _remove_container(record.context, container)
                if isinstance(error, BoundedC11ApplicationRuntimeError):
                    raise
                if type(error) is BoundedC11ApplicationExecutionError:
                    phase = {1: "argument_rejection", 2: "numeric_rejection",
                             3: "environment_rejection"}[error.status]
                elif isinstance(error, _ProcessFailure):
                    phase = error.reason
                elif isinstance(error, subprocess.TimeoutExpired):
                    phase = "timeout"
                if isinstance(error, (OSError, ValueError, _ProcessFailure,
                                      subprocess.SubprocessError)):
                    raise BoundedC11ApplicationRuntimeError(
                        phase,
                    ) from None
                raise

    def close(self) -> None:
        record = _lookup(self)
        with record.lifecycle.lock:
            if record.lifecycle.files_removed and record.lifecycle.image_removed:
                return
            record.lifecycle.closed = True
            if not _cleanup(record.context, record.lifecycle):
                raise BoundedC11ApplicationRuntimeError("cleanup_failed")


_REGISTRY: weakref.WeakKeyDictionary[BuiltBoundedC11Application, _Record] = (
    weakref.WeakKeyDictionary()
)


def _lookup(handle: BuiltBoundedC11Application) -> _Record:
    if type(handle) is not BuiltBoundedC11Application or handle not in _REGISTRY:
        raise BoundedC11ApplicationRuntimeError("handle_rejected")
    return _REGISTRY[handle]


def build_bounded_c11_application(
    module: SourceIntentModule, backend_bindings: tuple[BoundedBackendBinding, ...], *,
    workspace: Path,
) -> BuiltBoundedC11Application:
    """Explicitly build one fresh static CPU image with the fixed local Docker daemon.

    The caller owns an existing directory without symlink ancestors or group/other
    write permission. No tool, source, Docker endpoint, command or image parameter
    is accepted. A context manager or explicit close() releases the owned tag and
    temporary directory. This does not register a generally executable backend.
    """
    context: _Context | None = None
    phase = "application_rejection"
    try:
        _require_platform()
        clean_module, clean_bindings = _checked_module(module), _checked_bindings(backend_bindings)
        application = prepare_bounded_c11_application(clean_module, clean_bindings)
        validate_bounded_c11_application(clean_module, clean_bindings, application)
        files = _checked_files(application)
        phase = "workspace_rejection"
        context = _make_context(_workspace(workspace), files)
        _write_context(context)
        phase = "build_failed"
        build = _command(context, ("build", "--network=none", "--pull=false", "--no-cache",
                                   "--target", "static", "--tag", context.tag,
                                   "--file", "Dockerfile", "-"),
                         timeout=BUILD_TIMEOUT, stdout_limit=BUILD_LOG_LIMIT,
                         stderr_limit=BUILD_LOG_LIMIT, input_bytes=_build_archive(files))
        if build.exit_code != 0:
            raise ValueError("build failed")
        phase = "image_rejected"
        inspected = _command(context, ("image", "inspect", "--format", "{{.Id}}", context.tag),
                             stdout_limit=80)
        if inspected.exit_code != 0 or inspected.stderr:
            raise ValueError("image inspection failed")
        image_id = _image_id(inspected.stdout)
        _verify_context(context)
        # Manifest comes only from the revalidated private reconstructed artifact.
        response_bytes = cast(int, json.loads(application.application_json)["response_bytes"])
        if type(response_bytes) is not int or not 76 <= response_bytes <= MAX_FRAME_BYTES:
            raise ValueError("response budget rejected")
        record = _Record(context, image_id, clean_module, clean_bindings, module, backend_bindings,
                         application, response_bytes)
        handle = object.__new__(BuiltBoundedC11Application)
        _REGISTRY[handle] = record
        return handle
    except BaseException as error:
        if context is not None:
            _cleanup(context)
        if isinstance(error, BoundedC11ApplicationRuntimeError):
            raise
        if isinstance(error, _ProcessFailure):
            phase = error.reason
        elif isinstance(error, subprocess.TimeoutExpired):
            phase = "timeout"
        if isinstance(error, (OSError, ValueError, _ProcessFailure, subprocess.SubprocessError)):
            raise BoundedC11ApplicationRuntimeError(phase) from None
        raise
