"""CLI boundary tests. Mock runtime outputs are synthetic, not native evidence."""

import builtins
import io
import json
import os
import stat
import struct
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from tuc import bounded_cpu_application_cli as cli
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_json import INPUT_SCHEMA_VERSION, source_intent_from_json


def graph_bytes():
    return json.dumps({
        "schema_version": "source_intent.v0", "name": "cli_graph",
        "tensors": [{"name": name, "shape": shape} for name, shape in (
            ("a", [1, 2]), ("b", [2, 1]), ("product", [1, 1]),
            ("positive", [1, 1]), ("total", [1]),
        )],
        "operations": [
            {"name": "dot", "family": "matmul", "inputs": ["a", "b"],
             "outputs": ["product"]},
            {"name": "relu", "family": "elementwise", "inputs": ["product"],
             "outputs": ["positive"], "attributes": {"elementwise_kind": "relu"}},
            {"name": "sum", "family": "reduction", "inputs": ["product"],
             "outputs": ["total"], "attributes": {"axis": 1}},
        ],
        "returns": [{"public_name": "z_positive", "tensor_name": "positive"},
                    {"public_name": "a_total", "tensor_name": "total"}],
    }).encode()


def input_bytes():
    return input_envelope(b'{"a":[2,-3],"b":[4,5]}')


def input_envelope(payload):
    return (b'{"schema_version":' + json.dumps(INPUT_SCHEMA_VERSION).encode() +
            b',"inputs":' + payload + b'}')


@pytest.fixture
def cli_host(monkeypatch, tmp_path):
    """The tests bypass only OS reading and the explicit native-runtime call."""
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    state = SimpleNamespace(graph=graph_bytes(), inputs=input_bytes(), reads=[], builds=[],
                            events=[], outputs={"z_positive": (0.0,), "a_total": (-7.0,)},
                            run_error=None, close_error=None, build_error=None,
                            workspace=tmp_path)

    def read(path, limit):
        state.reads.append((path, limit))
        assert path in {"graph.json", "inputs.json"}
        return state.graph if path == "graph.json" else state.inputs

    monkeypatch.setattr(cli, "_read_file", read)
    from tuc.runtime import bounded_c11_application as runtime

    class Application:
        def __enter__(self):
            state.events.append("enter")
            return self

        def run(self, inputs):
            state.events.append("run")
            state.actual_inputs = inputs
            if state.run_error is not None:
                raise state.run_error
            return state.outputs

        def __exit__(self, *args):
            state.events.append("close")
            if state.close_error is not None:
                raise state.close_error

    def build(module, bindings, *, workspace):
        state.events.append("build")
        state.builds.append((module, bindings, workspace))
        if state.build_error is not None:
            raise state.build_error
        return Application()

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    return state


def run_args(state):
    return ["run", "graph.json", "--inputs", "inputs.json", "--workspace", str(state.workspace)]


def test_inspect_is_deterministic_preserves_bindings_and_never_imports_runtime(cli_host,
                                                                             monkeypatch, capsys):
    original_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("tuc.runtime"):
            pytest.fail("inspect imported the execution runtime")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert cli.main(["inspect", "graph.json"]) == 0
    first = capsys.readouterr()
    assert cli.main(["inspect", "graph.json"]) == 0
    second = capsys.readouterr()
    assert first == second
    assert first.err == "" and first.out.endswith("\n") and first.out.count("\n") == 1
    value = json.loads(first.out)
    assert set(value) == {"schema_version", "action", "program_digest", "inputs", "outputs",
                          "native_execution_observed"}
    assert value["schema_version"] == "tuc.bounded_cpu_cli.v0"
    assert value["action"] == "inspect" and value["native_execution_observed"] is False
    assert [item["public_name"] for item in value["inputs"]] == ["a", "b"]
    assert [item["public_name"] for item in value["outputs"]] == ["z_positive", "a_total"]
    assert not cli_host.builds
    assert all(limit == 65536 for _, limit in cli_host.reads)


def test_run_validates_both_inputs_then_closes_before_publishing(cli_host, monkeypatch, capsys):
    json_bytes = cli._json_bytes

    def serialize(value):
        assert cli_host.events == ["build", "enter", "run", "close"]
        return json_bytes(value)

    monkeypatch.setattr(cli, "_json_bytes", serialize)
    assert cli.main(run_args(cli_host)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    value = json.loads(captured.out)
    assert value["outputs"] == {"z_positive": [0.0], "a_total": [-7.0]}
    assert list(value["outputs"]) == ["z_positive", "a_total"]
    assert value["action"] == "run" and value["native_execution_observed"] is True
    assert value["request_digest"] == sha256(
        bytes.fromhex(value["program_digest"]) + struct.pack("<ffff", 2.0, -3.0, 4.0, 5.0)
    ).hexdigest()
    assert cli_host.actual_inputs == {"a": (2.0, -3.0), "b": (4.0, 5.0)}
    assert all(type(number) is float for values in cli_host.actual_inputs.values()
               for number in values)
    assert cli_host.reads == [("graph.json", 65536), ("inputs.json", 2097152)]
    module, bindings, workspace = cli_host.builds[0]
    assert module.name == "cli_graph" and workspace == cli_host.workspace
    assert bindings == cli.cpu_bindings()
    assert bindings[0].capability.name == "json_cpu"


@pytest.mark.parametrize("argv", [[], ["unknown"], ["inspect"], ["inspect", "x", "y"],
    ["run", "graph.json"], ["inspect", "--secret-path"], ["inspect", "-"],
    ["run", "x", "--inputs", "y", "--inputs", "z"],
    ["run", "x", "--workspace", "y", "--workspace", "z"],
    ["run", "x", "--in", "y", "--workspace", "z"],
    ["run", "x", "--inputs=y", "--workspace", "z"],
    ["run", "x", "--inputs", "--workspace", "--workspace", "z"],
    ["run", "x", "--inputs", "y", "--workspace", "z", "--help"],
    ["inspect", "x\x00secret"], ["@secret-options"],
    ["inspect", "x" * 4097]], ids=lambda argv: str(len(argv)))
def test_argument_rejections_do_not_echo_values_or_read_files(cli_host, capsys, argv):
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "tuc-cpu-app: arguments_rejected\n"
    assert not cli_host.reads and not cli_host.builds


def test_flags_can_be_reordered_without_expanding_the_grammar(cli_host, capsys):
    assert cli.main(["run", "graph.json", "--workspace", str(cli_host.workspace),
                     "--inputs", "inputs.json"]) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("bad", [b'{"name":"a","name":"b"}', b"[]", b"NaN", b"\xff",
                                  b"[" * 1000 + b"0" + b"]" * 1000,
                                  b" " * 65537], ids=["duplicate", "array", "nan", "utf8",
                                                                     "deep", "oversized"])
def test_graph_rejection_never_builds(cli_host, capsys, bad):
    cli_host.graph = bad
    assert cli.main(run_args(cli_host)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "tuc-cpu-app: graph_json_rejected\n"
    assert not cli_host.builds


@pytest.mark.parametrize("bad", [b'{}', b'{"a":[2,-3],"b":[4,true]}',
    b'{"a":[2,-3],"b":[4,1e999]}', b'{"a":[2,-3],"b":[4,1e-999]}',
    b'{"a":[2,-3],"b":[4,5],"b":[4,5]}', b'{"a":[2],"b":[4,5]}',
    b'{"a":[2,-3],"b":[4,5],"extra":[]}'],
    ids=["missing", "bool", "overflow", "underflow", "duplicate", "extent", "extra"])
def test_input_rejection_precedes_runtime_build(cli_host, capsys, bad):
    cli_host.inputs = input_envelope(bad)
    assert cli.main(run_args(cli_host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: input_json_rejected\n"
    assert not cli_host.builds


def test_graph_outside_cpu_subset_is_rejected_before_build(cli_host, capsys):
    value = json.loads(cli_host.graph)
    value["operations"][1]["attributes"]["elementwise_kind"] = "gelu"
    cli_host.graph = json.dumps(value).encode()
    assert cli.main(run_args(cli_host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: graph_json_rejected\n"
    assert not cli_host.builds


@pytest.mark.parametrize("stage,reason", [("run", "numeric_rejection"),
    ("run", "protocol_rejection"), ("run", "timeout"), ("close", "cleanup_failed"),
    ("build", "build_failed"), ("run", "untrusted secret output")])
def test_runtime_errors_emit_one_closed_line_and_no_claim(cli_host, capsys, stage, reason):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    setattr(cli_host, stage + "_error", BoundedC11ApplicationRuntimeError(reason))
    assert cli.main(run_args(cli_host)) == 1
    captured = capsys.readouterr()
    expected = "runtime_rejected" if "secret" in reason else reason
    assert captured.out == "" and captured.err == f"tuc-cpu-app: {expected}\n"
    assert len(captured.err.encode()) <= 256
    if stage == "run":
        assert cli_host.events[-1] == "close"


@pytest.mark.parametrize("outputs", [{}, {"a_total": (-7.0,), "z_positive": (0.0,)},
    {"z_positive": (float("nan"),), "a_total": (-7.0,)},
    {"z_positive": [0.0], "a_total": (-7.0,)},
    {"z_positive": (0.0, 1.0), "a_total": (-7.0,)},
    {"z_positive": (False,), "a_total": (-7.0,)}],
    ids=["missing", "order", "nan", "list", "extent", "bool"])
def test_output_boundary_rejects_malformed_runtime_results_after_cleanup(cli_host, capsys, outputs):
    cli_host.outputs = outputs
    assert cli.main(run_args(cli_host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: output_rejected\n"
    assert cli_host.events[-1] == "close"


def test_output_size_rejection_does_not_publish_partial_json(cli_host, monkeypatch, capsys):
    monkeypatch.setattr(cli, "MAX_OUTPUT_JSON_BYTES", 8)
    assert cli.main(run_args(cli_host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: output_rejected\n"
    assert cli_host.events[-1] == "close"


@pytest.mark.parametrize("argv", [["--help"], ["-h"], ["inspect", "--help"],
                                   ["run", "--help"]])
def test_help_does_not_check_platform_or_read_files(monkeypatch, capsys, argv):
    monkeypatch.setattr(cli, "_require_platform", lambda: pytest.fail("platform checked"))
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Usage: tuc-cpu-app inspect GRAPH.json\n")
    assert captured.err == ""


@pytest.mark.parametrize("system,machine", [("win32", "AMD64"), ("linux", "aarch64"),
                                           ("darwin", "x86_64")])
def test_unsupported_platform_rejects_before_read(monkeypatch, capsys, system, machine):
    monkeypatch.setattr(cli.sys, "platform", system)
    monkeypatch.setattr(cli.platform, "machine", lambda: machine)
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(["inspect", "secret-path"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: unsupported_platform\n"


def test_file_errors_do_not_include_host_paths(cli_host, monkeypatch, capsys):
    def fail(*args):
        raise cli._CLIError("file_rejected")

    monkeypatch.setattr(cli, "_read_file", fail)
    assert cli.main(["inspect", "secret-path"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: file_rejected\n"
    assert not cli_host.builds


def test_broken_pipe_has_a_closed_diagnostic_and_shutdown_is_silenced(cli_host, monkeypatch):
    class Broken(io.StringIO):
        def write(self, value):
            raise BrokenPipeError("secret pipe name")

    stderr = io.StringIO()
    silenced = []
    monkeypatch.setattr(cli.sys, "stdout", Broken())
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    monkeypatch.setattr(cli, "_silence_broken_stdout", lambda: silenced.append(True))
    assert cli.main(["inspect", "graph.json"]) == 1
    assert stderr.getvalue() == "tuc-cpu-app: output_unavailable\n"
    assert silenced == [True]


def test_unexpected_failure_and_interrupt_never_print_tracebacks(cli_host, monkeypatch, capsys):
    for exception, reason in ((RuntimeError("secret"), "internal_error"),
                              (KeyboardInterrupt(), "interrupted")):
        def fail(*args, exception=exception):
            raise exception

        monkeypatch.setattr(cli, "_execute", fail)
        assert cli.main(["inspect", "graph.json"]) == 1
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"tuc-cpu-app: {reason}\n"


def test_main_uses_sys_argv_only_when_not_explicit(cli_host, monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["ignored-binary", "inspect", "graph.json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["action"] == "inspect"


@pytest.mark.skipif(sys.platform != "linux", reason="hardened file CLI requires Linux")
def test_actual_file_reader_exact_limit_oversize_and_metadata(tmp_path):
    path = tmp_path / "graph.json"
    path.write_bytes(b"1234")
    assert cli._read_file(str(path), 4) == b"1234"
    with pytest.raises(cli._CLIError, match="file_rejected"):
        cli._read_file(str(path), 3)
    with pytest.raises(cli._CLIError, match="file_rejected"):
        cli._read_file(str(tmp_path), 10)


@pytest.mark.skipif(sys.platform != "linux", reason="hardened file CLI requires Linux")
def test_actual_reader_rejects_symlinks_and_fifo_without_reading(tmp_path, monkeypatch):
    path = tmp_path / "graph.json"
    path.write_bytes(b"{}")
    leaf = tmp_path / "leaf-link"
    leaf.symlink_to(path)
    directory = tmp_path / "directory-link"
    directory.symlink_to(tmp_path, target_is_directory=True)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    monkeypatch.setattr(cli.os, "read", lambda *args: pytest.fail("non-regular read"))
    for value in (leaf, directory / "graph.json", fifo, Path("/dev/null")):
        with pytest.raises(cli._CLIError, match="file_rejected"):
            cli._read_file(str(value), 1024)


@pytest.mark.skipif(sys.platform != "linux", reason="hardened file CLI requires Linux")
def test_actual_reader_rejects_parent_traversal_and_closes_on_growth(tmp_path, monkeypatch):
    path = tmp_path / "graph.json"
    path.write_bytes(b"1234")
    with pytest.raises(cli._CLIError, match="file_rejected"):
        cli._read_file(str(tmp_path / ".." / tmp_path.name / "graph.json"), 4)
    read = os.read
    requested = []

    def grow(descriptor, size):
        requested.append(size)
        if len(requested) == 1:
            with path.open("ab") as stream:
                stream.write(b"x" * 1000)
        return read(descriptor, size)

    monkeypatch.setattr(cli.os, "read", grow)
    with pytest.raises(cli._CLIError, match="file_rejected"):
        cli._read_file(str(path), 4)
    assert requested == [5]


def test_reader_model_checks_regular_fd_and_closes_every_descriptor(monkeypatch):
    """Exercise Linux flags and fd transitions portably without opening a real file."""
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    monkeypatch.setattr(cli, "Path", lambda value: SimpleNamespace(
        parts=("/", "data", "graph.json"), absolute=lambda: SimpleNamespace(
            anchor="/", parts=("/", "data", "graph.json"), name="graph.json")))
    state = SimpleNamespace(opened=[], closed=[], reads=[], data=bytearray(b"1234"))

    def open_fd(path, flags, **kwargs):
        state.opened.append((path, flags, kwargs))
        return 100 + len(state.opened)

    def read_fd(descriptor, size):
        state.reads.append((descriptor, size))
        value = bytes(state.data[:size])
        del state.data[:size]
        return value

    flags = dict(O_RDONLY=1, O_DIRECTORY=2, O_NOFOLLOW=4, O_CLOEXEC=8, O_NONBLOCK=16)
    record = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=1, st_ino=2,
                             st_size=4, st_mtime_ns=3, st_ctime_ns=4)
    monkeypatch.setattr(cli, "os", SimpleNamespace(
        **flags, open=open_fd, close=state.closed.append, read=read_fd, fstat=lambda fd: record))
    assert cli._read_file("graph.json", 4) == b"1234"
    assert state.opened == [("/", 15, {}), ("data", 15, {"dir_fd": 101}),
                            ("graph.json", 29, {"dir_fd": 102})]
    assert state.closed == [101, 103, 102]
    assert max(size for _, size in state.reads) == 5


def test_manifest_inspection_returns_only_public_metadata(cli_host, monkeypatch, capsys):
    module = source_intent_from_json(cli_host.graph)
    application = prepare_bounded_c11_application(module, cli.cpu_bindings())
    metadata = json.loads(application.application_json)
    metadata["secret_host_path"] = "/private/secret"
    application = replace(application, application_json=json.dumps(metadata))
    monkeypatch.setattr(cli, "prepare_bounded_c11_application", lambda *args: application)
    assert cli.main(["inspect", "graph.json"]) == 0
    captured = capsys.readouterr()
    assert "secret" not in captured.out
    assert "entrypoint" not in captured.out and "Dockerfile" not in captured.out
