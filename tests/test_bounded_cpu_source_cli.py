"""CLI ordering and publication checks; mocked outputs are not native evidence."""

import builtins
import io
import json
from types import SimpleNamespace

import pytest

from tuc import bounded_cpu_source_cli as cli

SOURCE = b'''import triton
import triton.language as tl
@triton.jit
def project(x, y):
    p = tl.where(x > 0.0, x, 0.0)
    tl.store(y, p)
'''
SIGNATURE = json.dumps({
    "schema_version": "tuc.bounded_cpu_source.v0", "source_name": "projection",
    "kernel_name": "project", "tensor_shapes": {"x": [2, 2], "y": [2, 2]},
}).encode()
GRAPH = json.dumps({
    "schema_version": "source_intent.v0", "name": "projection",
    "tensors": [{"name": name, "shape": [2, 2], "dtype": "float32"} for name in ("x", "p")],
    "operations": [{"name": "p", "family": "elementwise", "inputs": ["x"],
                    "outputs": ["p"], "hints": {}, "attributes": {"elementwise_kind": "relu"}}],
    "returns": [{"public_name": "y", "tensor_name": "p", "required": True}],
}, sort_keys=True, separators=(",", ":")).encode() + b"\n"
ARGS = ["source.py", "--signature", "signature.json", "--workspace", "work"]


@pytest.fixture
def host(monkeypatch):
    from tuc.runtime import bounded_cpu_source as runtime

    state = SimpleNamespace(source=SOURCE, signature=SIGNATURE, result=GRAPH,
                            error=None, calls=[], reads=[])
    monkeypatch.setattr(cli, "_require_platform", lambda: None)

    def read(path, limit):
        state.reads.append((path, limit))
        return state.source if path == "source.py" else state.signature

    def convert(source, signature, *, workspace):
        state.calls.append((source, signature, workspace))
        if state.error:
            raise state.error
        return state.result

    monkeypatch.setattr(cli, "_read_file", read)
    monkeypatch.setattr(runtime, "convert_bounded_cpu_source", convert)
    return state


def test_help_is_portable_reads_nothing_and_does_not_import_runtime(monkeypatch, capsys):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("tuc.runtime"):
            pytest.fail("help imported runtime")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(cli, "_read_file", lambda *a: pytest.fail("help read file"))
    for args in (["--help"], ["-h"]):
        assert cli.main(args) == 0
        output = capsys.readouterr()
        assert output.out.startswith("Usage: tuc-source-to-json") and not output.err


@pytest.mark.parametrize("args", [[], ["run"], ["@options"], ARGS + ["extra"],
    ["-source.py", *ARGS[1:]], ["source.py", "--signature", "x", "--signature", "y"],
    ["source.py", "--sig", "x", "--workspace", "w"],
    ["source.py", "--signature", "-x", "--workspace", "w"],
    ["source.py", "--signature", "x", "--workspace", "w\x00"],
    ["x" * 4097, *ARGS[1:]], tuple(ARGS), [True]])
def test_closed_argument_grammar_rejects_before_any_read(args, host, capsys):
    assert cli.main(args) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "tuc-source-to-json: arguments_rejected\n"
    assert not host.calls and not host.reads


def test_emits_revalidated_graph_only_after_runtime_returns(host, monkeypatch, capsys):
    original = cli.source_intent_from_json

    def validate(data):
        assert len(host.calls) == 1
        return original(data)

    monkeypatch.setattr(cli, "source_intent_from_json", validate)
    assert cli.main(ARGS) == 0
    output = capsys.readouterr()
    assert output.out.encode() == GRAPH and output.err == ""
    assert host.reads == [("source.py", 65536), ("signature.json", 16384)]
    assert host.calls[0][:2] == (SOURCE, SIGNATURE)


def test_options_can_change_order(host, capsys):
    assert cli.main(["source.py", "--workspace", "work", "--signature", "signature.json"]) == 0
    assert capsys.readouterr().out.encode() == GRAPH


@pytest.mark.parametrize("field,value,reason", [
    ("source", b"\xff", "source_rejected"), ("source", b"", "source_rejected"),
    ("source", b"x" * 65537, "source_rejected"),
    ("signature", b"{}", "signature_rejected"),
    ("signature", b'{"schema_version":1,"schema_version":2}', "signature_rejected"),
], ids=["invalid-utf8", "empty-source", "large-source", "empty-signature", "duplicate-key"])
def test_input_preflight_precedes_runtime_import(field, value, reason, host, monkeypatch, capsys):
    setattr(host, field, value)
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("tuc.runtime"):
            pytest.fail("invalid request imported runtime")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert cli.main(ARGS) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == f"tuc-source-to-json: {reason}\n"
    assert not host.calls


@pytest.mark.parametrize("reason", ["timeout", "cleanup_failed", "build_failed", "image_rejected",
                                   "workspace_rejected"])
def test_runtime_failures_never_publish_graph(reason, host, capsys):
    from tuc.runtime.bounded_cpu_source import BoundedCPUSourceRuntimeError

    host.error = BoundedCPUSourceRuntimeError(reason)
    assert cli.main(ARGS) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == f"tuc-source-to-json: {reason}\n"


@pytest.mark.parametrize("result", [b"{}\n", GRAPH[:-1], GRAPH + b"\n", GRAPH.decode(),
                                  b"x" * 65537, b"\xff\n"],
                         ids=["empty-object", "no-newline", "extra-newline", "string",
                              "large-output", "invalid-utf8"])
def test_invalid_runtime_output_never_published(result, host, capsys):
    host.result = result
    assert cli.main(ARGS) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "tuc-source-to-json: output_rejected\n"


def test_internal_exception_does_not_echo_source_path_or_details(host, capsys):
    host.error = RuntimeError("/private/path token=do-not-echo")
    assert cli.main(ARGS) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "tuc-source-to-json: internal_error\n"


def test_keyboard_interrupt_is_closed(host, capsys):
    host.error = KeyboardInterrupt()
    assert cli.main(ARGS) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "tuc-source-to-json: interrupted\n"


def test_broken_stdout_is_closed_without_traceback(host, monkeypatch, capsys):
    class Broken(io.StringIO):
        def write(self, value):
            raise BrokenPipeError("/private/path")

    calls = []
    monkeypatch.setattr(cli.sys, "stdout", Broken())
    monkeypatch.setattr(cli, "_silence_broken_stdout", lambda: calls.append("silenced"))
    assert cli.main(ARGS) == 1
    assert capsys.readouterr().err == "tuc-source-to-json: output_unavailable\n"
    assert calls == ["silenced"]
