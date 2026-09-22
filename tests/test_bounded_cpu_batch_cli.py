"""Batch CLI boundary tests with synthetic runtime results, never native evidence."""

import builtins
import io
import json
import struct
from hashlib import sha256
from types import SimpleNamespace

import pytest

from tuc import bounded_cpu_application_cli as cli
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_batch import (
    BATCH_SCHEMA_VERSION,
    MAX_BATCH_JSON_BYTES,
    batch_from_json,
)
from tuc.compiler.bounded_cpu_json import source_intent_from_json


def graph_bytes():
    return json.dumps({
        "schema_version": "source_intent.v0", "name": "batch_graph",
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


def requests():
    return [
        {"id": "z_first", "inputs": {"a": [2, -3], "b": [4, 5]}},
        {"id": "a_middle", "inputs": {"a": [-0.0, -0.0], "b": [1, 1]}},
        {"id": "m_last", "inputs": {"a": [1, 2], "b": [3, 4]}},
    ]


def envelope(values=None):
    return json.dumps({"schema_version": BATCH_SCHEMA_VERSION,
                       "requests": requests() if values is None else values}).encode()


@pytest.fixture
def host(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    state = SimpleNamespace(graph=graph_bytes(), batch=envelope(), workspace=tmp_path,
                            events=[], reads=[], builds=[], inputs=[], run_error=None,
                            fail_index=1, close_error=None, build_error=None,
                            outputs=[{"z_positive": (0.0,), "a_total": (-7.0,)},
                                     {"z_positive": (-0.0,), "a_total": (-0.0,)},
                                     {"z_positive": (11.0,), "a_total": (11.0,)}])

    def read(path, limit):
        state.reads.append((path, limit))
        assert path in {"graph.json", "batch.json"}
        return state.graph if path == "graph.json" else state.batch

    monkeypatch.setattr(cli, "_read_file", read)
    from tuc.runtime import bounded_c11_application as runtime

    class Application:
        def __enter__(self):
            state.events.append("enter")
            return self

        def run(self, values):
            index = len(state.inputs)
            state.events.append(f"run{index}")
            state.inputs.append(values)
            if index == state.fail_index and state.run_error is not None:
                raise state.run_error
            return state.outputs[index]

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


def args(host):
    return ["run-batch", "graph.json", "--batch", "batch.json", "--workspace", str(host.workspace)]


def test_one_build_order_digests_signed_zero_and_cleanup_before_serialization(host, monkeypatch,
                                                                           capsys):
    original = cli._json_bytes
    checked = cli._checked_outputs

    def serialize(value):
        assert host.events == ["build", "enter", "run0", "check", "run1", "check",
                               "run2", "check", "close"]
        return original(value)

    def check(value, manifest):
        assert "close" not in host.events
        host.events.append("check")
        return checked(value, manifest)

    monkeypatch.setattr(cli, "_json_bytes", serialize)
    monkeypatch.setattr(cli, "_checked_outputs", check)
    assert cli.main(args(host)) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and captured.out.count("\n") == 1
    value = json.loads(captured.out)
    assert set(value) == {"schema_version", "action", "program_digest", "batch_digest",
                          "results", "native_execution_observed"}
    assert value["schema_version"] == "tuc.bounded_cpu_batch_cli.v0"
    assert value["action"] == "run-batch" and value["native_execution_observed"] is True
    assert [item["id"] for item in value["results"]] == [item["id"] for item in requests()]
    assert len(host.builds) == 1 and len(host.inputs) == 3
    assert host.reads == [("graph.json", 65536), ("batch.json", MAX_BATCH_JSON_BYTES)]
    assert host.builds[0][2] == host.workspace and host.builds[0][1] == cli.cpu_bindings()
    module = source_intent_from_json(host.graph)
    application = prepare_bounded_c11_application(module, cli.cpu_bindings())
    batch = batch_from_json(module, cli.cpu_bindings(), application, host.batch)
    assert value["batch_digest"] == batch.batch_digest
    assert value["program_digest"] == application.program_digest
    for index, result in enumerate(value["results"]):
        assert set(result) == {"id", "request_digest", "outputs"}
        assert list(result["outputs"]) == ["z_positive", "a_total"]
        numbers = (*host.inputs[index]["a"], *host.inputs[index]["b"])
        assert all(type(n) is float for n in numbers)
        assert result["request_digest"] == sha256(
            bytes.fromhex(value["program_digest"]) + struct.pack("<ffff", *numbers)).hexdigest()
        assert result["outputs"] == {name: list(values)
                                      for name, values in host.outputs[index].items()}
    assert struct.pack("<f", host.inputs[1]["a"][0]) == struct.pack("<I", 0x80000000)
    assert struct.pack("<f", value["results"][1]["outputs"]["a_total"][0]) == struct.pack(
        "<I", 0x80000000)


@pytest.mark.parametrize("bad", [b"{}", b"[]", b"NaN", b"\xff", b"\xef\xbb\xbf{}",
    b'{"schema_version":"a","schema_version":"b"}', b"["*1000+b"0"+b"]"*1000,
    b" "*(MAX_BATCH_JSON_BYTES+1)], ids=range(8))
def test_bad_batch_rejected_before_runtime_import_or_build(host, monkeypatch, capsys, bad):
    original = builtins.__import__

    def guarded(name, *a, **kw):
        if name.startswith("tuc.runtime"):
            pytest.fail("runtime imported before complete preflight")
        return original(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", guarded)
    host.batch = bad
    assert cli.main(args(host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: batch_json_rejected\n"
    assert not host.builds


@pytest.mark.parametrize("change", ["last_extent", "last_bool", "last_overflow", "last_underflow",
                                    "duplicate_id", "missing_id", "extra", "empty", "too_many"])
def test_all_requests_preflight_including_last_before_import(host, monkeypatch, capsys, change):
    values = requests()
    if change == "last_extent":
        values[-1]["inputs"]["a"] = [1]
    elif change == "last_bool":
        values[-1]["inputs"]["b"][1] = True
    elif change == "last_overflow":
        values[-1]["inputs"]["b"][1] = 1e100
    elif change == "last_underflow":
        values[-1]["inputs"]["b"][1] = 1e-100
    elif change == "duplicate_id":
        values[-1]["id"] = values[0]["id"]
    elif change == "missing_id":
        del values[-1]["id"]
    elif change == "extra":
        values[-1]["secret"] = "private host path"
    elif change == "empty":
        values = []
    else:
        values = [{"id": f"r{i}", "inputs": requests()[0]["inputs"]} for i in range(17)]
    host.batch = envelope(values)
    original = builtins.__import__

    def guarded(name, *a, **kw):
        if name.startswith("tuc.runtime"):
            pytest.fail("runtime imported before last request was checked")
        return original(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert cli.main(args(host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: batch_json_rejected\n"
    assert host.events == []


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("reason", ["numeric_rejection", "timeout", "protocol_rejection"])
def test_failure_stops_closes_and_never_publishes_partial_results(host, capsys, index, reason):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    host.fail_index = index
    host.run_error = BoundedC11ApplicationRuntimeError(reason)
    assert cli.main(args(host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == f"tuc-cpu-app: {reason}\n"
    assert len(host.inputs) == index+1 and len(host.builds) == 1
    assert host.events[-1] == "close"


@pytest.mark.parametrize("outputs", [{}, {"a_total": (-7.0,), "z_positive": (0.0,)},
    {"z_positive": (float("nan"),), "a_total": (-7.0,)},
    {"z_positive": [0.0], "a_total": (-7.0,)},
    {"z_positive": (0.0, 1.0), "a_total": (-7.0,)},
    {"z_positive": (False,), "a_total": (-7.0,)}], ids=range(6))
def test_malformed_middle_output_closes_before_failure_and_stops_next_run(host, capsys, outputs):
    host.outputs[1] = outputs
    assert cli.main(args(host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: output_rejected\n"
    assert host.events == ["build", "enter", "run0", "run1", "close"]


@pytest.mark.parametrize("stage,reason", [("build", "build_failed"), ("close", "cleanup_failed"),
                                         ("run", "private untrusted reason")])
def test_build_close_and_untrusted_errors_have_closed_diagnostics(host, capsys, stage, reason):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    setattr(host, stage+"_error", BoundedC11ApplicationRuntimeError(reason))
    assert cli.main(args(host)) == 1
    captured = capsys.readouterr()
    expected = "runtime_rejected" if stage == "run" else reason
    assert captured.out == "" and captured.err == f"tuc-cpu-app: {expected}\n"
    if stage == "close":
        assert len(host.inputs) == 3 and host.events[-1] == "close"


@pytest.mark.parametrize("error,reason", [(OSError("private path"), "runtime_rejected"),
    (ValueError("private data"), "runtime_rejected"), (KeyboardInterrupt(), "interrupted"),
    (RuntimeError("private text"), "internal_error")], ids=range(4))
def test_unexpected_run_failure_also_closes_without_outputs(host, capsys, error, reason):
    host.run_error = error
    assert cli.main(args(host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == f"tuc-cpu-app: {reason}\n"
    assert host.events[-1] == "close" and len(host.inputs) == 2


def test_flags_reorder_and_output_limit_failure_after_cleanup(host, monkeypatch, capsys):
    assert cli.main(["run-batch", "graph.json", "--workspace", str(host.workspace),
                     "--batch", "batch.json"]) == 0
    assert capsys.readouterr().err == ""
    host.events.clear()
    host.inputs.clear()
    monkeypatch.setattr(cli, "MAX_OUTPUT_JSON_BYTES", 8)
    assert cli.main(args(host)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: output_rejected\n"
    assert host.events[-1] == "close"


@pytest.mark.parametrize("argv", [["run-batch"], ["run-batch", "x"],
    ["run-batch", "x", "--inputs", "y", "--workspace", "z"],
    ["run-batch", "x", "--batch", "y", "--batch", "z"],
    ["run-batch", "x", "--workspace", "y", "--workspace", "z"],
    ["run-batch", "x", "--batch=y", "--workspace", "z"],
    ["run-batch", "x", "--batch", "--secret", "--workspace", "z"],
    ["run-batch", "-", "--batch", "y", "--workspace", "z"],
    ["run-batch", "x", "--batch", "y", "--workspace", "z", "--help"],
    ["run", "x", "--batch", "y", "--workspace", "z"],
    ["run-batch", "x\x00private", "--batch", "y", "--workspace", "z"]], ids=range(11))
def test_argument_grammar_never_reads_or_builds(host, capsys, argv):
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: arguments_rejected\n"
    assert host.reads == host.builds == []


def test_batch_help_is_inert_on_unsupported_platform(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_require_platform", lambda: pytest.fail("platform read"))
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(["run-batch", "--help"]) == 0
    captured = capsys.readouterr()
    assert "run-batch GRAPH.json --batch BATCH.json --workspace DIR" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("system,machine", [("win32", "AMD64"), ("linux", "aarch64")])
def test_batch_platform_rejection_before_file_read(monkeypatch, capsys, system, machine):
    monkeypatch.setattr(cli.sys, "platform", system)
    monkeypatch.setattr(cli.platform, "machine", lambda: machine)
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(["run-batch", "graph", "--batch", "batch", "--workspace", "work"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: unsupported_platform\n"


def test_graph_rejection_precedes_batch_read_and_build(host, capsys):
    host.graph = b"{}"
    assert cli.main(args(host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: graph_json_rejected\n"
    assert host.reads == [("graph.json", 65536)] and not host.builds


def test_batch_file_limit_passed_to_hardened_reader_and_failures_closed(host, monkeypatch, capsys):
    def read(path, limit):
        if path == "graph.json":
            return host.graph
        assert path == "batch.json" and limit == MAX_BATCH_JSON_BYTES == 2097152
        raise cli._CLIError("file_rejected")

    monkeypatch.setattr(cli, "_read_file", read)
    assert cli.main(args(host)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-cpu-app: file_rejected\n"
    assert not host.builds


def test_shared_weights_merge_into_each_fresh_request_without_changing_order(host, capsys):
    host.batch = json.dumps({"schema_version": BATCH_SCHEMA_VERSION,
        "shared_inputs": {"b": [4, 5]}, "requests": [
            {"id": "second", "inputs": {"a": [2, -3]}},
            {"id": "first", "inputs": {"a": [-0.0, 1]}},
        ]}).encode()
    assert cli.main(args(host)) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert [value["id"] for value in result["results"]] == ["second", "first"]
    assert host.inputs == [{"a": (2.0, -3.0), "b": (4.0, 5.0)},
                           {"a": (-0.0, 1.0), "b": (4.0, 5.0)}]
    assert host.inputs[0] is not host.inputs[1] and len(host.builds) == 1
    assert host.events == ["build", "enter", "run0", "run1", "close"]


def test_stdout_failure_occurs_only_after_cleanup(host, monkeypatch):
    class Broken(io.StringIO):
        def write(self, value):
            assert host.events[-1] == "close" and len(host.inputs) == 3
            raise BrokenPipeError("private pipe")

    errors = io.StringIO()
    monkeypatch.setattr(cli.sys, "stdout", Broken())
    monkeypatch.setattr(cli.sys, "stderr", errors)
    monkeypatch.setattr(cli, "_silence_broken_stdout", lambda: None)
    assert cli.main(args(host)) == 1
    assert errors.getvalue() == "tuc-cpu-app: output_unavailable\n"
