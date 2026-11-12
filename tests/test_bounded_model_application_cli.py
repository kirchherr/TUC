"""CLI admission/publication checks; synthetic native hosts prove no execution."""

import builtins
import io
import json
from dataclasses import replace

import pytest

from integration.bounded_model_artifact_bundle.consumer import _OPS, _binding
from tests.test_bounded_model_application import context
from tests.test_bounded_model_application_session import host as host
from tuc import bounded_model_application_cli as cli
from tuc.backends.bounded_dag import DAGTarget
from tuc.bounded_cpu_application_cli import platform
from tuc.compiler import backend_bindings_to_json
from tuc.compiler import bounded_cpu_batch as batch_api
from tuc.compiler.bounded_model_artifact_request import create_bounded_model_artifact_request
from tuc.ir.model import OperationKind


@pytest.fixture
def files(host, monkeypatch, tmp_path):
    model, bindings, bundle, inputs, request = host.ctx
    data = {
        "model": model, "backends": backend_bindings_to_json(bindings), "bundle": bundle,
        "inputs": inputs, "request": request,
        "batch": json.dumps({
            "schema_version": "tuc.bounded_cpu_batch.v0",
            "requests": [
                {"id": "first", "inputs": {"x": [1.0, -0.0, 3.0, 4.0]}},
                {"id": "last", "inputs": {"x": [5.0, 6.0, 7.0, 8.0]}},
            ],
        }).encode(),
    }
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    monkeypatch.setattr(cli, "_read_file", lambda name, limit: data[name])
    data["workspace"] = str(tmp_path)
    return data


def command(files, action="run"):
    argv = [action, "model", "--backends", "backends"]
    if action != "plan":
        argv += ["--bundle", "bundle"]
    if action in {"request", "run"}:
        argv += ["--inputs", "inputs"]
    if action == "run":
        argv += ["--request", "request"]
    if action == "run-batch":
        argv += ["--batch", "batch"]
    if action in {"run", "run-batch"}:
        argv += ["--workspace", files["workspace"]]
    return argv


@pytest.mark.parametrize("action", ["plan", "inspect", "request"])
def test_pure_commands_preserve_portable_data_without_runtime_import(files, host, monkeypatch,
                                                                   capsys, action):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name in {"tuc.runtime.bounded_model_application_session",
                    "tuc.runtime.bounded_c11_application"}:
            pytest.fail("execution runtime imported by inert command")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    assert cli.main(command(files, action)) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and not host.events
    if action == "plan":
        assert captured.out.encode() == files["bundle"]
    elif action == "request":
        assert captured.out.encode() == files["request"]
    else:
        result = json.loads(captured.out)
        assert result["bundle_digest"] == json.loads(files["bundle"])["bundle_digest"]
        assert result["native_execution_observed"] is False
        assert [item["tensor_name"] for item in result["inputs"]] == ["x"]
        assert [item["tensor_name"] for item in result["parameters"]] == ["w"]
        assert all("value_bits" not in item for item in result["parameters"])


@pytest.mark.parametrize("action", ["run", "run-batch"])
def test_execution_reuses_build_and_binds_each_ordered_request(files, host, capsys, action):
    assert cli.main(command(files, action)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["native_execution_observed"] is True
    count = 2 if action == "run-batch" else 1
    assert host.events == ["build"] + ["run"] * count + ["close"]
    assert [item["sequence"] for item in report["results"]] == list(range(1, count + 1))
    expected = ["first", "last"] if count == 2 else ["single"]
    assert [item["id"] for item in report["results"]] == expected
    digests = []
    for item in report["results"]:
        receipt = item["receipt"]
        assert receipt["bundle_digest"] == report["bundle_digest"]
        assert receipt["model_digest"] == report["model_digest"]
        assert receipt["native_execution_observed"] is False
        assert receipt["protocol_validated"] is True
        digests.append(receipt["request_digest"])
    assert len(set(digests)) == count


@pytest.mark.parametrize("argv", [
    [], ["unknown"], ["plan"], ["plan", "--model", "--backends", "caps"],
    ["plan", "model", "--backends", "caps", "extra"],
    ["inspect", "model", "--backends", "caps", "--backends", "other"],
    ["plan", "model", "--backend", "caps"], ["plan", "model", "--backends=caps"],
    ["plan", "model", "--backends", "--private"], ["@private/options"],
    ["plan", "private\x00value", "--backends", "caps"],
    ["plan", "a" * 4097, "--backends", "caps"],
])
def test_invalid_arguments_never_read_or_execute(monkeypatch, capsys, argv):
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: arguments_rejected\n"


@pytest.mark.parametrize("argv", [["--help"], ["-h"], ["plan", "--help"],
                                 ["run-batch", "--help"]])
def test_help_is_inert_on_every_platform(monkeypatch, capsys, argv):
    monkeypatch.setattr(cli, "_require_platform", lambda: pytest.fail("platform checked"))
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Usage: tuc-model-app plan") and captured.err == ""


@pytest.mark.parametrize("name,bad", [
    ("model", b"{}"), ("backends", b"{}"), ("bundle", b"{}"),
    ("inputs", b"{}"), ("request", b"{}"),
])
def test_original_context_and_request_all_pass_before_execution(files, host, capsys, name, bad):
    files[name] = bad
    assert cli.main(command(files)) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("tuc-model-app: ")
    assert not host.events


def test_replayed_request_and_fixed_parameter_override_never_build(files, host, capsys):
    files["inputs"] = context(values=(5.0, 6.0, 7.0, 8.0))[3]
    assert cli.main(command(files)) == 2
    assert not host.events and capsys.readouterr().out == ""
    files["inputs"] = json.dumps({
        "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [1.0] * 4, "w": [1.0] * 4},
    }).encode()
    assert cli.main(command(files, "request")) == 2
    assert not host.events and capsys.readouterr().out == ""


@pytest.mark.parametrize("change", ["last_extent", "fixed_override", "duplicate_id", "overlap",
                                    "nonfinite", "input_budget", "output_budget", "count"])
def test_whole_batch_rejects_before_first_native_action(files, host, monkeypatch, capsys, change):
    batch = json.loads(files["batch"])
    if change == "last_extent":
        batch["requests"][-1]["inputs"]["x"] = [1.0]
    elif change == "fixed_override":
        batch["requests"][-1]["inputs"]["w"] = [1.0] * 4
    elif change == "duplicate_id":
        batch["requests"][-1]["id"] = "first"
    elif change == "overlap":
        batch["shared_inputs"] = {"x": [1.0] * 4}
    elif change == "nonfinite":
        batch["requests"][-1]["inputs"]["x"][0] = float("inf")
    elif change == "input_budget":
        # Variable values alone fit; expanded fixed parameters exceed the limit.
        monkeypatch.setattr(batch_api, "MAX_BATCH_INPUT_ELEMENTS", 15)
    elif change == "output_budget":
        monkeypatch.setattr(batch_api, "MAX_BATCH_OUTPUT_ELEMENTS", 7)
    else:
        monkeypatch.setattr(batch_api, "MAX_BATCH_REQUESTS", 1)
    files["batch"] = json.dumps(batch).encode()
    assert cli.main(command(files, "run-batch")) == 2
    assert not host.events
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: input_rejected\n"


@pytest.mark.parametrize("reason", ["numeric_rejection", "timeout", "private host log"])
def test_later_native_failure_discards_every_result_and_closes(files, host, monkeypatch,
                                                           capsys, reason):
    from tuc.runtime import bounded_c11_application as runtime

    original = runtime.build_bounded_c11_application

    def build(*args, **kwargs):
        built = original(*args, **kwargs)
        run = built.run_frame

        def later(frame):
            assert capsys.readouterr().out == ""
            if host.frames:
                raise runtime.BoundedC11ApplicationRuntimeError(reason)
            return run(frame)

        built.run_frame = later
        return built

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    assert cli.main(command(files, "run-batch")) == 1
    captured = capsys.readouterr()
    expected = reason if "private" not in reason else "runtime_rejected"
    assert captured.out == "" and captured.err == f"tuc-model-app: {expected}\n"
    assert host.events[-1] == "close"


def test_cleanup_failure_does_not_publish_results(files, host, capsys):
    host.close_failure = True
    assert cli.main(command(files, "run-batch")) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: cleanup_failed\n"


def test_output_limit_is_checked_after_cleanup(files, host, monkeypatch, capsys):
    monkeypatch.setattr(cli, "MAX_MODEL_CLI_OUTPUT_BYTES", 512)
    assert cli.main(command(files, "run-batch")) == 1
    assert host.events[-1] == "close"
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: output_rejected\n"


def test_interrupt_cleans_up_and_sanitizes(files, host, capsys):
    host.failure = KeyboardInterrupt()
    assert cli.main(command(files)) == 1
    assert host.events[-1] == "close"
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: interrupted\n"


@pytest.mark.parametrize("workspace", ["relative", "../private", "/tmp/private/../other"])
def test_workspace_must_be_explicit_and_absolute(files, host, capsys, workspace):
    files["workspace"] = workspace
    assert cli.main(command(files)) == 2
    assert not host.events and capsys.readouterr().out == ""


def test_generated_request_is_exactly_the_existing_contract(files, host, capsys):
    assert cli.main(command(files, "request")) == 0
    assert capsys.readouterr().out.encode() == create_bounded_model_artifact_request(
        host.ctx[0], host.ctx[1], files["bundle"], files["inputs"],
    )


@pytest.mark.parametrize("mixed", [False, True])
def test_cuda_and_mixed_plans_remain_inert_and_never_gain_cpu_authority(
    files, host, monkeypatch, capsys, mixed,
):
    gpu = _binding("declared_device", DAGTarget.CUDA_SM86, _OPS)
    if mixed:
        gpu = replace(gpu, capability=replace(
            gpu.capability, supported_ops=frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
        ))
    bindings = (*host.ctx[1], gpu) if mixed else (gpu,)
    files["backends"] = backend_bindings_to_json(bindings)
    assert cli.main(command(files, "plan")) == 0
    files["bundle"] = capsys.readouterr().out.encode()
    assert cli.main(command(files, "inspect")) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["native_execution_observed"] is False
    assert "declared_device" in inspected["decision_report"]
    assert cli.main(command(files, "request")) == 0
    files["request"] = capsys.readouterr().out.encode()
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "tuc.runtime.bounded_model_application_session":
            pytest.fail("inadmissible declaration reached runtime import")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    for action in ("run", "run-batch"):
        assert cli.main(command(files, action)) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("tuc-model-app: ")
    assert not host.events


@pytest.mark.parametrize("system,machine", [("win32", "AMD64"), ("linux", "aarch64"),
                                           ("darwin", "x86_64")])
def test_file_commands_reject_unsupported_platform_before_read(
    monkeypatch, capsys, system, machine,
):
    monkeypatch.setattr(cli.sys, "platform", system)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(cli, "_read_file", lambda *args: pytest.fail("file read"))
    assert cli.main(["plan", "private-path", "--backends", "private-capabilities"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: unsupported_platform\n"


def test_unavailable_output_is_one_closed_error(monkeypatch, capsys):
    class Broken(io.StringIO):
        def write(self, text):
            raise BrokenPipeError("private descriptor")

    silenced = []
    with monkeypatch.context() as patch:
        patch.setattr(cli.sys, "stdout", Broken())
        patch.setattr(cli, "_silence_broken_stdout", lambda: silenced.append(True))
        assert cli.main(["--help"]) == 1
    assert silenced == [True]
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "tuc-model-app: output_unavailable\n"
