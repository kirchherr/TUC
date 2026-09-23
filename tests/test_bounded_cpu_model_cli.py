"""Synthetic CLI lifecycle checks; installed observations are separate."""

import builtins
import json
from types import SimpleNamespace

import pytest

from tests.test_bounded_cpu_model import encode, graph, inputs, model
from tuc import bounded_cpu_application_cli as cli
from tuc.compiler.bounded_cpu_model import model_from_json, pack_model


@pytest.fixture
def host(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    state = SimpleNamespace(
        files={
            "graph": encode(graph()),
            "model": encode(model()),
            "params": inputs(model()["parameters"]),
            "input": inputs({"x": [2, 3]}),
            "batch": encode(
                {
                    "schema_version": "tuc.bounded_cpu_batch.v0",
                    "requests": [
                        {"id": "first", "inputs": {"x": [2, 3]}},
                        {"id": "last", "inputs": {"x": [0, 0]}},
                    ],
                }
            ),
        },
        events=[],
        received=[],
        run_error=None,
        close_error=None,
        workspace=str(tmp_path),
    )
    monkeypatch.setattr(cli, "_read_file", lambda name, limit: state.files[name])
    from tuc.runtime import bounded_c11_application as runtime

    class Built:
        def __enter__(self):
            state.events.append("enter")
            return self

        def run(self, values):
            state.events.append("run")
            state.received.append(values)
            if len(state.received) == 2 and state.run_error:
                raise state.run_error
            return {"scores": (1.5, 10.0)}

        def __exit__(self, *args):
            state.events.append("close")
            if state.close_error:
                raise state.close_error

    def build(*args, **kwargs):
        state.events.append("build")
        return Built()

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    return state


def command(host, batch=False):
    return [
        "run-model-batch" if batch else "run-model",
        "model",
        "--batch" if batch else "--inputs",
        "batch" if batch else "input",
        "--workspace",
        host.workspace,
    ]


def test_pack_and_inspect_are_inert_and_hide_parameter_values(host, monkeypatch, capsys):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name.startswith("tuc.runtime"):
            pytest.fail("inert command imported runtime")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    assert cli.main(["pack-model", "graph", "--parameters", "params"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode() == pack_model(host.files["graph"], host.files["params"])
    assert cli.main(["inspect-model", "model"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["native_execution_observed"] is False
    assert report["model_digest"] == model_from_json(host.files["model"]).model_digest
    assert [item["public_name"] for item in report["inputs"]] == ["x"]
    assert {item["public_name"] for item in report["parameters"]} == {"b", "w"}
    assert all("values" not in item for item in report["parameters"])
    assert not host.events


@pytest.mark.parametrize("batch", [False, True])
def test_expanded_model_runs_once_per_request_and_publishes_after_cleanup(
    host, monkeypatch, capsys, batch
):
    serialize = cli._json_bytes

    def output(value):
        assert host.events[-1] == "close"
        return serialize(value)

    monkeypatch.setattr(cli, "_json_bytes", output)
    assert cli.main(command(host, batch)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == (
        "tuc.bounded_cpu_model_batch_cli.v0" if batch else "tuc.bounded_cpu_model_cli.v0"
    )
    assert report["model_digest"] == model_from_json(host.files["model"]).model_digest
    assert report["native_execution_observed"] is True
    assert host.events == ["build", "enter", "run"] + (["run"] if batch else []) + ["close"]
    assert all(set(values) == {"x", "w", "b"} for values in host.received)
    assert all(values["w"] == (2.0, -1.0, 1.0, 3.0) for values in host.received)


@pytest.mark.parametrize(
    "change",
    [
        "model",
        "override",
        "last_override",
        "last_extent",
        "last_missing",
        "duplicate_id",
        "shared_overlap",
    ],
)
def test_all_data_rejects_before_runtime_import_or_build(host, monkeypatch, capsys, change):
    batch = json.loads(host.files["batch"])
    if change == "model":
        host.files["model"] = b"{}"
    elif change == "override":
        batch["shared_inputs"] = {"w": [2, -1, 1, 3]}
    elif change == "last_override":
        batch["requests"][-1]["inputs"]["b"] = [0.5, 0]
    elif change == "last_extent":
        batch["requests"][-1]["inputs"]["x"] = [1]
    elif change == "last_missing":
        batch["requests"][-1]["inputs"] = {}
    elif change == "duplicate_id":
        batch["requests"][-1]["id"] = "first"
    else:
        batch["shared_inputs"] = {"x": [1, 2]}
    host.files["batch"] = encode(batch)
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name.startswith("tuc.runtime"):
            pytest.fail("runtime imported before complete preflight")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    assert cli.main(command(host, True)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err in {
        "tuc-cpu-app: model_json_rejected\n",
        "tuc-cpu-app: batch_json_rejected\n",
    }
    assert not host.events


@pytest.mark.parametrize("error", ["numeric_rejection", "cleanup_failed"])
def test_late_failure_or_cleanup_failure_never_publishes_partial_results(host, capsys, error):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    if error == "cleanup_failed":
        host.close_error = BoundedC11ApplicationRuntimeError(error)
    else:
        host.run_error = BoundedC11ApplicationRuntimeError(error)
    assert cli.main(command(host, True)) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == f"tuc-cpu-app: {error}\n"
    assert host.events == ["build", "enter", "run", "run", "close"]


@pytest.mark.parametrize(
    "args",
    [
        ["pack-model", "graph"],
        ["pack-model", "graph", "--inputs", "params"],
        ["inspect-model", "model", "--execute"],
        ["run-model", "model", "--batch", "batch", "--workspace", "work"],
        ["run-model-batch", "model", "--inputs", "input", "--workspace", "work"],
    ],
)
def test_closed_model_command_syntax(capsys, args):
    assert cli.main(args) == 2
    assert capsys.readouterr().err == "tuc-cpu-app: arguments_rejected\n"
