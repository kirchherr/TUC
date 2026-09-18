"""Mocked explicit-runtime contracts; synthetic records are not native evidence."""

import io
import json
import os
import stat
import struct
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.runtime import bounded_c11_application as runtime


def source():
    return SourceIntentModule(
        "explicit_runtime_test",
        tuple(SourceIntentTensor(name, shape) for name, shape in (
            ("a", (1, 2)), ("b", (2, 1)), ("p", (1, 1)), ("sum", (1,)),
        )),
        (SourceIntentOperation("dot", "matmul", ("a", "b"), ("p",)),
         SourceIntentOperation("reduce", "reduction", ("p",), ("sum",),
                               attributes={"axis": 1})),
        returns=(SourceIntentReturn("answer", "sum"),),
    )


def bindings():
    return (BoundedBackendBinding(BackendCapability(
        "cpu", frozenset({OperationKind.MATMUL, OperationKind.REDUCTION}),
        memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11),)


def inputs():
    return {"a": (1.0, 2.0), "b": (3.0, 4.0)}


def synthetic_response(request, status=0, payload=None):
    """Host-authored bytes, never evidence that a native worker executed."""
    if payload is None:
        payload = struct.pack("<f", 11.0) if status == 0 else b""
    return b"TUCOUT01" + request[8:72] + struct.pack("<I", status) + payload


@pytest.fixture
def host(tmp_path, monkeypatch):
    """Simulate Docker and Linux-only filesystem primitives on every test host."""
    monkeypatch.setattr(runtime, "_require_platform", lambda: None)
    monkeypatch.setattr(runtime, "_docker", lambda: (Path("/usr/bin/docker"), (1, 2, 3, 4)))

    def owned(path):
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("test boundary rejected")
        if not path.is_dir():
            raise ValueError("test directory required")
        return runtime._identity(path)

    def write(context):
        runtime._verify_context(context, contents=False)
        for name, value in context.files:
            with (context.source / name).open("xb") as stream:
                stream.write(value)

    def remove(context):
        assert context.directory.parent == context.workspace
        assert context.directory.is_relative_to(tmp_path)
        assert owned(context.workspace) == context.identities[0]
        assert owned(context.directory) == context.identities[1]

        def clear(path):
            for item in path.iterdir():
                if item.is_symlink():
                    raise ValueError("test cleanup rejects links")
                if item.is_dir():
                    clear(item)
                else:
                    item.unlink()
            path.rmdir()

        clear(context.directory)

    monkeypatch.setattr(runtime, "_owned_directory", owned)
    monkeypatch.setattr(runtime, "_write_context", write)
    monkeypatch.setattr(runtime, "_remove_files", remove)
    state = SimpleNamespace(calls=[], result=None, build_result=None, inspect_result=None,
                            remove_result=None, list_result=None, input_requests=[],
                            workspace=tmp_path, contexts=[], configs=[], fail=None)

    def process(arguments, **kwargs):
        state.calls.append((arguments, kwargs))
        assert arguments[1] == "--host=unix:///var/run/docker.sock"
        assert arguments[2] == "--config"
        config = Path(arguments[3])
        assert config.is_dir() and not list(config.iterdir())
        assert kwargs["environment"] == {
            "PATH": runtime.TRUSTED_PATH, "HOME": str(config), "LANG": "C", "LC_ALL": "C",
            "DOCKER_BUILDKIT": "1",
        }
        state.configs.append(config)
        command = arguments[4:]
        if command[0] == "build":
            state.contexts.append(kwargs["cwd"])
            return state.build_result or runtime._ProcessResult(0, b"", b"")
        if command[:2] == ("image", "inspect"):
            return state.inspect_result or runtime._ProcessResult(
                0, b"sha256:" + b"a" * 64 + b"\n", b"")
        if command[0] == "run":
            state.input_requests.append(kwargs["input_bytes"])
            if state.fail is not None:
                raise state.fail
            if state.result is not None:
                return state.result(kwargs["input_bytes"])
            return runtime._ProcessResult(0, synthetic_response(kwargs["input_bytes"]), b"")
        if command[:2] == ("image", "rm"):
            return state.remove_result or runtime._ProcessResult(0, b"", b"")
        if command[:2] == ("image", "ls"):
            return state.list_result or runtime._ProcessResult(0, b"", b"")
        assert command[:2] == ("rm", "--force")
        return runtime._ProcessResult(0, b"", b"")

    monkeypatch.setattr(runtime, "_bounded_process", process)
    yield state
    # An unexpected native subprocess is never a permissible fallback.
    assert all(not config.exists() for config in state.configs)


def build(host, module=None, backends=None):
    return runtime.build_bounded_c11_application(
        source() if module is None else module,
        bindings() if backends is None else backends, workspace=host.workspace,
    )


def commands(host, name):
    return [(argv[4:], options) for argv, options in host.calls if argv[4] == name]


def test_build_and_replay_use_only_fixed_isolation_and_private_state(host, monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "tcp://untrusted:2375")
    monkeypatch.setenv("DOCKER_CONFIG", "secret-credentials")
    monkeypatch.setenv("SECRET_TOKEN", "must-not-leak")
    with build(host) as application:
        assert application.run(inputs()) == {"answer": (11.0,)}
        assert application.run(inputs()) == {"answer": (11.0,)}
        assert len(application.program_digest) == 64
        record = runtime._lookup(application)
        assert record.module is not record.original_module
        assert record.bindings is not record.original_bindings
        assert not list(record.context.config.iterdir())
        runs = commands(host, "run")
        assert len(runs) == 2
        assert host.input_requests[0] == host.input_requests[1]
        assert runs[0][0][-1] == "sha256:" + "a" * 64
        assert runs[0][0][:-3] == runtime._RUN_ARGUMENTS
        assert runs[0][0][-3] == "--name"
        assert runs[0][0][-2] != runs[1][0][-2]
        for arguments, options in runs:
            assert options["stdout_limit"] == 80
            assert options["stderr_limit"] == 4096
            assert options["timeout"] == 30.0
            for flag in ("--network=none", "--read-only", "--user=10001:10001",
                         "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
                         "--pids-limit=32", "--memory=1g", "--cpus=1", "--log-driver=none",
                         "--entrypoint=/opt/tuc/application", "--pull=never"):
                assert flag in arguments
            assert not any(token.startswith(("--privileged", "--gpus", "--volume", "--mount",
                                              "--env", "--device", "--security-opt=seccomp"))
                           for token in arguments)
    assert not record.context.directory.exists()
    removals = [args for args, _ in commands(host, "image") if args[1] == "rm"]
    assert removals == [("image", "rm", "--no-prune", record.context.tag)]
    assert len(host.configs) == len(set(host.configs))


def test_build_tar_is_bounded_deterministic_and_contains_exact_revalidated_files(host):
    first = build(host)
    second = build(host)
    builds = commands(host, "build")
    assert builds[0][1]["input_bytes"] == builds[1][1]["input_bytes"]
    assert builds[0][0] != builds[1][0]
    for arguments, options in builds:
        assert arguments[-3:] == ("--file", "Dockerfile", "-")
        assert "--network=none" in arguments
        assert "--no-cache" in arguments
        assert arguments[arguments.index("--target") + 1] == "static"
        assert options["stdout_limit"] == options["stderr_limit"] == 2 * 1024 * 1024
        assert options["timeout"] == 600.0
        assert len(options["input_bytes"]) <= 1048576
        with tarfile.open(fileobj=io.BytesIO(options["input_bytes"]), mode="r:") as archive:
            members = archive.getmembers()
            assert {item.name for item in members} == runtime._FILES
            expected = dict(runtime._lookup(first).context.files)
            for member in members:
                assert member.isfile() and member.mode == 0o600
                assert member.uid == member.gid == member.mtime == 0
                assert archive.extractfile(member).read() == expected[member.name]
    first.close()
    second.close()


@pytest.mark.parametrize("status,reason", [(1, "argument_rejection"),
                                          (2, "numeric_rejection"),
                                          (3, "environment_rejection")])
def test_only_fully_validated_native_error_has_its_closed_reason(host, status, reason):
    host.result = lambda request: runtime._ProcessResult(
        1, synthetic_response(request, status=status), b"")
    with build(host) as application:
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(inputs())
        assert error.value.reason == reason
        assert isinstance(error.value, ValueError)
        with pytest.raises(AttributeError):
            error.value.reason = "numeric_rejection"
        run_name = commands(host, "run")[-1][0][-2]
        assert commands(host, "rm")[-1][0] == ("rm", "--force", run_name)


@pytest.mark.parametrize("variant", ["wrong_exit", "wrong_magic", "wrong_program",
                                     "wrong_request", "truncated", "extra", "wrong_status",
                                     "nonfinite", "empty", "boolean_exit"])
def test_protocol_damage_never_becomes_numeric_rejection(host, variant):
    def response(request):
        data = synthetic_response(request, status=2)
        code = 1
        if variant == "wrong_exit":
            code = 0
        elif variant == "wrong_magic":
            data = b"X" + data[1:]
        elif variant == "wrong_program":
            data = data[:8] + bytes([data[8] ^ 1]) + data[9:]
        elif variant == "wrong_request":
            data = data[:40] + bytes([data[40] ^ 1]) + data[41:]
        elif variant == "truncated":
            data = data[:-1]
        elif variant == "extra":
            data += b"x"
        elif variant == "wrong_status":
            data = synthetic_response(request, status=4)
        elif variant == "nonfinite":
            data, code = synthetic_response(request, payload=struct.pack("<I", 0x7FC00000)), 0
        elif variant == "empty":
            data, code = b"", 2
        elif variant == "boolean_exit":
            code = True
        return runtime._ProcessResult(code, data, b"")

    host.result = response
    with build(host) as application:
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(inputs())
        assert error.value.reason == "protocol_rejection"
        assert len(commands(host, "rm")) == 1


@pytest.mark.parametrize("failure,reason", [
    (runtime._ProcessFailure("timeout"), "timeout"),
    (runtime._ProcessFailure("output_limit"), "output_limit"),
    (OSError("secret host diagnostics"), "process_error"),
    (subprocess.TimeoutExpired("secret argv", 30), "timeout"),
])
def test_runtime_failures_clean_owned_container_without_exposing_logs(host, failure, reason):
    host.fail = failure
    with build(host) as application:
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(inputs())
        assert error.value.reason == reason
        assert "secret" not in str(error.value)
        assert len(commands(host, "rm")) == 1


def test_stderr_is_rejected_even_with_a_valid_synthetic_output(host):
    host.result = lambda request: runtime._ProcessResult(
        0, synthetic_response(request), b"secret stderr")
    with build(host) as application:
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(inputs())
        assert error.value.reason == "process_error"
        assert "secret" not in str(error.value)


@pytest.mark.parametrize("bad", [{}, {"a": [1.0, 2.0], "b": (3.0, 4.0)},
                                 {"a": (True, 2.0), "b": (3.0, 4.0)},
                                 {"a": (float("nan"), 2.0), "b": (3.0, 4.0)},
                                 {"a": (1.0, 2.0), "b": (3.0, 4.0), "extra": (1.0,)}])
def test_input_validation_precedes_any_container_execution(host, bad):
    with build(host) as application:
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(bad)
        assert error.value.reason == "input_rejection"
        assert not commands(host, "run")
        assert not commands(host, "rm")


@pytest.mark.parametrize("kind", ["source", "extra_file", "config", "module", "bindings",
                                  "docker"])
def test_source_graph_tool_and_configuration_drift_fail_closed(host, monkeypatch, kind):
    module, backends = source(), bindings()
    with build(host, module, backends) as application:
        record = runtime._lookup(application)
        if kind == "source":
            path = record.context.source / "application.c"
            path.write_bytes(path.read_bytes() + b"changed")
        elif kind == "extra_file":
            (record.context.source / "injected.c").write_text("extra")
        elif kind == "config":
            (record.context.config / "config.json").write_text("{}")
        elif kind == "module":
            object.__setattr__(module, "name", "changed")
        elif kind == "bindings":
            object.__setattr__(backends[0], "target", DAGTarget.CUDA_SM86)
        else:
            monkeypatch.setattr(runtime, "_docker", lambda: (Path("/usr/bin/docker"), (9, 2, 3, 4)))
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
            application.run(inputs())
        assert error.value.reason == ("graph_drift" if kind in {"module", "bindings"}
                                     else "context_drift")
        assert not commands(host, "run")


def test_handles_cannot_be_constructed_subclassed_or_forged(host):
    with pytest.raises(TypeError):
        runtime.BuiltBoundedC11Application()
    with pytest.raises(TypeError):
        type("Injected", (runtime.BuiltBoundedC11Application,), {})
    forged = object.__new__(runtime.BuiltBoundedC11Application)
    for action in (lambda: forged.run(inputs()), forged.close, forged.__enter__,
                   lambda: forged.program_digest):
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="handle_rejected"):
            action()
    with build(host) as application:
        with pytest.raises(AttributeError):
            application.image_id = "untrusted"
        with pytest.raises(AttributeError):
            application.program_digest = "untrusted"


def test_close_is_idempotent_and_permanently_blocks_run(host):
    application = build(host)
    application.close()
    count = len(host.calls)
    application.close()
    assert len(host.calls) == count
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="closed"):
        application.run(inputs())
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="closed"):
        application.__enter__()


def test_failed_tag_cleanup_remains_retryable_and_blocks_run(host):
    application = build(host)
    context = runtime._lookup(application).context
    host.remove_result = runtime._ProcessResult(1, b"", b"secret")
    host.list_result = runtime._ProcessResult(0, b"sha256:" + b"a" * 64, b"")
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="cleanup_failed"):
        application.close()
    assert context.directory.exists()
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="closed"):
        application.run(inputs())
    host.remove_result = None
    application.close()
    assert not context.directory.exists()


def test_failed_file_cleanup_retries_without_removing_image_again(host, monkeypatch):
    application = build(host)
    context = runtime._lookup(application).context
    real_remove = runtime._remove_files

    def fail(context_to_remove):
        if context_to_remove.directory == context.directory:
            raise OSError("test locked file")
        real_remove(context_to_remove)

    monkeypatch.setattr(runtime, "_remove_files", fail)
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="cleanup_failed"):
        application.close()
    monkeypatch.setattr(runtime, "_remove_files", real_remove)
    application.close()
    assert len([args for args, _ in commands(host, "image") if args[1] == "rm"]) == 1
    assert not context.directory.exists()


def test_already_removed_tag_is_recognized_without_removing_an_image_digest(host):
    application = build(host)
    host.remove_result = runtime._ProcessResult(1, b"", b"no such image")
    application.close()
    listed = [args for args, _ in commands(host, "image") if args[1] == "ls"]
    assert len(listed) == 1
    assert listed[0][-1].startswith("reference=tuc-c11-application:")


@pytest.mark.parametrize("kind", ["build", "inspect", "identity"])
def test_build_failure_releases_owned_tag_context_and_hides_output(host, kind):
    if kind == "build":
        host.build_result = runtime._ProcessResult(9, b"secret stdout", b"secret stderr")
    elif kind == "inspect":
        host.inspect_result = runtime._ProcessResult(1, b"secret stdout", b"secret stderr")
    else:
        host.inspect_result = runtime._ProcessResult(0, b"sha256:" + b"A" * 64, b"")
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError) as error:
        build(host)
    assert error.value.reason == ("build_failed" if kind == "build" else "image_rejected")
    assert "secret" not in str(error.value)
    assert host.contexts and all(not path.exists() for path in host.contexts)


@pytest.mark.parametrize("value", [b"", b"a" * 64, b"sha256:" + b"a" * 63,
                                  b"sha256:" + b"A" * 64, b"sha256:" + b"a" * 64 + b"\n\n",
                                  b" sha256:" + b"a" * 64, b"sha256:" + b"a" * 64 + b"\r\n"])
def test_image_identity_is_strict(value):
    with pytest.raises(ValueError):
        runtime._image_id(value)


@pytest.mark.parametrize("system,machine", [("win32", "AMD64"), ("linux", "aarch64"),
                                           ("darwin", "x86_64")])
def test_unsupported_platform_never_creates_context_or_process(tmp_path, monkeypatch,
                                                             system, machine):
    monkeypatch.setattr(runtime.sys, "platform", system)
    monkeypatch.setattr(runtime.platform, "machine", lambda: machine)
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("native"))
    with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="unsupported_platform"):
        runtime.build_bounded_c11_application(source(), bindings(), workspace=tmp_path)
    assert not list(tmp_path.iterdir())


def test_workspace_requires_path_and_rejects_parent_traversal(host):
    for workspace in (str(host.workspace), host.workspace / ".." / host.workspace.name):
        with pytest.raises(runtime.BoundedC11ApplicationRuntimeError, match="workspace_rejection"):
            runtime.build_bounded_c11_application(source(), bindings(), workspace=workspace)
    assert not host.calls


@pytest.mark.parametrize("mode,uid", [(stat.S_IFREG | 0o700, 1000),
                                     (stat.S_IFDIR | 0o777, 1000),
                                     (stat.S_IFDIR | 0o700, 1001)])
def test_owned_directory_rejects_type_permission_or_owner(monkeypatch, mode, uid):
    path = SimpleNamespace(is_symlink=lambda: False, parents=(), lstat=lambda: SimpleNamespace(
        st_mode=mode, st_uid=uid, st_dev=1, st_ino=2))
    monkeypatch.setattr(runtime, "_uid", lambda: 1000)
    with pytest.raises(ValueError):
        runtime._owned_directory(path)


def test_symlink_ancestor_is_rejected_without_stat(monkeypatch):
    path = SimpleNamespace(is_symlink=lambda: False,
                           parents=(SimpleNamespace(is_symlink=lambda: True),),
                           lstat=lambda: pytest.fail("must not follow link"))
    with pytest.raises(ValueError):
        runtime._owned_directory(path)


class FakeStream:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.closed = False

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed = True


@pytest.fixture
def pipes(monkeypatch):
    """A deterministic selector/Popen model: no native child is launched."""
    state = SimpleNamespace(chunks={10: bytearray(), 11: bytearray()}, writes=bytearray(),
                            read_sizes=[], waits=[], killed=[], clock=0.0, tick=0.01,
                            exit_code=0, created=[], selectors=[])

    class Process:
        pid = 321

        def __init__(self, arguments, **kwargs):
            self.stdout, self.stderr = FakeStream(10), FakeStream(11)
            self.stdin = FakeStream(12) if kwargs["stdin"] == subprocess.PIPE else None
            state.created.append((self, arguments, kwargs))

        def wait(self, timeout):
            state.waits.append(timeout)
            return state.exit_code

        def kill(self):
            state.killed.append(self.pid)

    class Selector:
        def __init__(self):
            self.mapping = {}
            self.closed = False
            state.selectors.append(self)

        def register(self, stream, event, data):
            self.mapping[stream] = SimpleNamespace(fileobj=stream, data=data)

        def unregister(self, stream):
            del self.mapping[stream]

        def get_map(self):
            return self.mapping

        def select(self, timeout):
            return [(item, 1) for item in tuple(self.mapping.values())]

        def close(self):
            self.closed = True

    def read(descriptor, size):
        state.read_sizes.append(size)
        data = bytes(state.chunks[descriptor][:size])
        del state.chunks[descriptor][:size]
        return data

    def write(descriptor, data):
        assert descriptor == 12
        state.writes.extend(data)
        return len(data)

    def clock():
        state.clock += state.tick
        return state.clock

    monkeypatch.setattr(runtime.subprocess, "Popen", Process)
    monkeypatch.setattr(runtime.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(runtime.time, "monotonic", clock)
    monkeypatch.setattr(runtime.os, "set_blocking", lambda descriptor, value: None)
    monkeypatch.setattr(runtime.os, "read", read)
    monkeypatch.setattr(runtime.os, "write", write)
    monkeypatch.setattr(runtime.os, "killpg", lambda pid, sig: state.killed.append(pid),
                        raising=False)
    monkeypatch.setattr(runtime.signal, "SIGKILL", 9, raising=False)
    return state


def process_call(**kwargs):
    return runtime._bounded_process(("/usr/bin/docker", "synthetic"), cwd=Path("."),
                                    environment={"PATH": runtime.TRUSTED_PATH}, timeout=30,
                                    stdout_limit=4, stderr_limit=3, **kwargs)


def test_bounded_pipe_reader_accepts_exact_limits_and_streams_input_to_eof(pipes):
    pipes.chunks[10].extend(b"1234")
    pipes.chunks[11].extend(b"abc")
    request = b"x" * 150000
    result = process_call(input_bytes=request)
    assert result == runtime._ProcessResult(0, b"1234", b"abc")
    assert pipes.writes == request
    process, arguments, options = pipes.created[0]
    assert process.stdin.closed and process.stdout.closed and process.stderr.closed
    assert options["start_new_session"] is options["close_fds"] is True
    assert options["stdout"] == options["stderr"] == subprocess.PIPE
    assert options["env"] == {"PATH": runtime.TRUSTED_PATH}
    assert pipes.selectors[0].closed
    assert not pipes.killed
    assert max(pipes.read_sizes) <= 5


@pytest.mark.parametrize("descriptor,limit", [(10, 4), (11, 3)])
def test_pipe_overflow_reads_only_one_extra_byte_then_kills_group(pipes, descriptor, limit):
    pipes.chunks[descriptor].extend(b"x" * 1000000)
    with pytest.raises(runtime._ProcessFailure, match="output_limit"):
        process_call()
    assert 1000000 - len(pipes.chunks[descriptor]) == limit + 1
    assert pipes.killed == [321]
    assert pipes.selectors[0].closed
    assert pipes.created[0][0].stdout.closed and pipes.created[0][0].stderr.closed


def test_deadline_kills_process_group_and_closes_every_pipe(pipes):
    pipes.tick = 100.0
    with pytest.raises(runtime._ProcessFailure, match="timeout"):
        process_call(input_bytes=b"small")
    assert pipes.killed == [321]
    process = pipes.created[0][0]
    assert process.stdin.closed and process.stdout.closed and process.stderr.closed


def test_selector_creation_failure_still_kills_child_and_closes_pipes(pipes, monkeypatch):
    def fail():
        raise OSError("no selector")

    monkeypatch.setattr(runtime.selectors, "DefaultSelector", fail)
    with pytest.raises(OSError):
        process_call(input_bytes=b"small")
    assert pipes.killed == [321]
    process = pipes.created[0][0]
    assert process.stdin.closed and process.stdout.closed and process.stderr.closed


@pytest.mark.parametrize("payload", [bytearray(b"x"), "x", b"x" * 1048577],
                         ids=["mutable", "text", "over-budget"])
def test_input_budget_rejection_happens_before_process_creation(pipes, payload):
    with pytest.raises(runtime._ProcessFailure, match="input_rejection"):
        process_call(input_bytes=payload)
    assert not pipes.created


def test_zero_length_stdin_is_closed_without_waiting_for_pipe_writability(pipes):
    process_call(input_bytes=b"")
    assert pipes.created[0][0].stdin.closed
    assert not pipes.writes


def test_prepared_file_archive_rejects_oversize_without_native_activity():
    with pytest.raises(ValueError):
        runtime._build_archive((("application.c", b"x" * 1048576),))


def test_declared_response_budget_matches_protocol_not_a_global_capture_limit(host):
    with build(host) as application:
        record = runtime._lookup(application)
        manifest = json.loads(record.application.application_json)
        assert record.response_bytes == manifest["response_bytes"] == 80
        assert record.response_bytes < runtime.MAX_FRAME_BYTES
        application.run(inputs())
        assert commands(host, "run")[0][1]["stdout_limit"] == record.response_bytes


@pytest.mark.skipif(os.name != "posix", reason="actual dir_fd cleanup requires POSIX filesystem")
def test_descriptor_relative_cleanup_refuses_symlink_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_docker", lambda: (Path("/usr/bin/docker"), (1, 2, 3, 4)))
    context = runtime._make_context(tmp_path, ())
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "keep"
    target.write_text("unchanged")
    (context.source / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        runtime._remove_files(context)
    assert target.read_text() == "unchanged"


@pytest.mark.skipif(os.name != "posix", reason="actual dir_fd cleanup requires POSIX filesystem")
def test_descriptor_relative_create_and_cleanup_preserve_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_docker", lambda: (Path("/usr/bin/docker"), (1, 2, 3, 4)))
    context = runtime._make_context(tmp_path, (("application.c", b"fixed source"),))
    runtime._write_context(context)
    assert (context.source / "application.c").read_bytes() == b"fixed source"
    with pytest.raises(FileExistsError):
        runtime._write_context(context)
    runtime._remove_files(context)
    assert tmp_path.is_dir() and not context.directory.exists()
