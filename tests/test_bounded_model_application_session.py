"""Lifecycle and hostile requests; fake hosts are not native execution evidence."""

import builtins
import copy
import json
import struct
import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from integration.bounded_model_artifact_bundle.consumer import _OPS, _binding
from tests.test_bounded_model_application import context
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_model_application import BoundedModelApplicationError
from tuc.compiler.bounded_model_artifact_bundle import create_bounded_model_artifact_bundle
from tuc.compiler.bounded_model_artifact_request import create_bounded_model_artifact_request
from tuc.runtime import bounded_model_application_session as api


@pytest.fixture
def host(monkeypatch, tmp_path):
    from tuc.runtime import bounded_c11_application as runtime

    state = SimpleNamespace(
        events=[], frames=[], failure=None, close_failure=False, wrong_digest=False,
        replay=False, block=None, release=None, built=None,
    )

    class Built:
        def __init__(self, module, bindings):
            app = api.prepare_bounded_c11_application(module, bindings)
            self.program_digest = "0" * 64 if state.wrong_digest else app.program_digest
            self.output_count = sum(json.loads(app.application_json)["output_elements"])

        def run_frame(self, frame):
            state.events.append("run")
            state.frames.append(frame)
            if state.block:
                state.block.set()
                assert state.release.wait(5)
            if state.failure:
                raise state.failure
            original = state.frames[0] if state.replay else frame
            values = (0.0, -0.0, 2.0, 3.0) if self.output_count == 4 else (0.0,) * self.output_count
            return b"TUCOUT01" + original[8:72] + struct.pack("<I", 0) + struct.pack(
                "<" + "f" * len(values), *values
            )

        def close(self):
            state.events.append("close")
            if state.close_failure:
                raise RuntimeError("private host path or log")

    def build(module, bindings, **kwargs):
        state.events.append("build")
        state.built = Built(module, bindings)
        return state.built

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    state.ctx = context()
    state.open = lambda: api.open_bounded_model_application(*state.ctx[:3], workspace=tmp_path)
    return state


def test_open_enter_and_unused_close_are_inert(host, monkeypatch, tmp_path):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "tuc.runtime.bounded_c11_application":
            pytest.fail("runtime imported before run")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    nonexistent = tmp_path / "not-created"
    with api.open_bounded_model_application(*host.ctx[:3], workspace=nonexistent):
        assert not nonexistent.exists()
    assert not nonexistent.exists()
    assert not host.events


def test_one_build_variable_requests_and_replay_keep_their_identities(host):
    changed = context(values=(5.0, 6.0, 7.0, 8.0))
    with host.open() as session:
        first = session.run(*host.ctx[3:])
        second = session.run(*changed[3:])
        replay = session.run(*host.ctx[3:])
        assert [first.sequence, second.sequence, replay.sequence] == [1, 2, 3]
        assert first.result.result_digest == replay.result.result_digest
        assert first.result.result_digest != second.result.result_digest
        receipt = json.loads(first.result.receipt_data)
        assert receipt["native_execution_observed"] is False
        assert receipt["request_digest"] != json.loads(second.result.receipt_data)["request_digest"]
        assert first.result.outputs[0].value_bits == "00000000000000800000004000004040"
        with pytest.raises(FrozenInstanceError):
            first.sequence = 9
    assert host.events == ["build", "run", "run", "run", "close"]
    session.close()
    assert host.events.count("close") == 1
    with pytest.raises(api.BoundedModelApplicationSessionError, match="^closed$"):
        session.run(*host.ctx[3:])


@pytest.mark.parametrize("value", [b"{}", b"", b"NaN", b'{"x":1,"x":2}', None, "secret source"])
def test_malformed_request_never_builds_and_does_not_poison_session(host, value):
    with host.open() as session:
        with pytest.raises(BoundedModelApplicationError, match="^model_application_rejected$"):
            session.run(host.ctx[3], value)
        assert not host.events
        assert session.run(*host.ctx[3:]).sequence == 1


def test_parameter_or_input_request_substitution_never_runs(host):
    changed = context(4.0)
    with host.open() as session:
        session.run(*host.ctx[3:])
        with pytest.raises(BoundedModelApplicationError):
            session.run(host.ctx[3], changed[4])
        assert host.events == ["build", "run"]
        assert session.run(*host.ctx[3:]).sequence == 2


@pytest.mark.parametrize("mixed", [False, True])
def test_non_cpu_context_rejects_before_any_host_action(host, tmp_path, mixed):
    cuda = (_binding("cuda", DAGTarget.CUDA_SM86, _OPS),)
    bindings = (*host.ctx[1], *cuda) if mixed else cuda
    bundle = create_bounded_model_artifact_bundle(host.ctx[0], bindings)
    with pytest.raises(BoundedModelApplicationError):
        api.open_bounded_model_application(host.ctx[0], bindings, bundle, workspace=tmp_path)
    assert not host.events


@pytest.mark.parametrize("maximum,accepted", [(0, 0), (1, 1), (2, 2)])
def test_request_limit_precedes_another_native_call(host, monkeypatch, maximum, accepted):
    monkeypatch.setattr(api, "MAX_SESSION_REQUESTS", maximum)
    with host.open() as session:
        for _ in range(accepted):
            session.run(*host.ctx[3:])
        before = list(host.events)
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^session_limit$"):
            session.run(*host.ctx[3:])
        assert host.events == before


@pytest.mark.parametrize("maximum,accepted", [(7, 0), (8, 1), (16, 2)])
def test_aggregate_inputs_include_fixed_parameters(host, monkeypatch, maximum, accepted):
    monkeypatch.setattr(api, "MAX_SESSION_ELEMENTS", maximum)
    with host.open() as session:
        for _ in range(accepted):
            session.run(*host.ctx[3:])
        before = list(host.events)
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^session_limit$"):
            session.run(*host.ctx[3:])
        assert host.events == before


def test_aggregate_output_budget_is_independent(host, monkeypatch, tmp_path):
    bindings = host.ctx[1]
    payload = {
        "schema_version": "tuc.bounded_cpu_model.v0",
        "parameters": {"w": [1.0] * 4},
        "graph": {
            "schema_version": "source_intent.v0", "name": "expanding_output",
            "tensors": [
                {"name": n, "shape": s}
                for n, s in (("x", [4, 1]), ("w", [1, 4]), ("y", [4, 4]))
            ],
            "operations": [
                {"name": "mm", "family": "matmul", "inputs": ["x", "w"], "outputs": ["y"]},
            ],
            "returns": [{"public_name": "scores", "tensor_name": "y"}],
        },
    }
    data = json.dumps(payload).encode()
    inputs = json.dumps({
        "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [0.0] * 4},
    }).encode()
    bundle = create_bounded_model_artifact_bundle(data, bindings)
    request = create_bounded_model_artifact_request(data, bindings, bundle, inputs)
    monkeypatch.setattr(api, "MAX_SESSION_ELEMENTS", 20)
    with api.open_bounded_model_application(data, bindings, bundle, workspace=tmp_path) as session:
        session.run(inputs, request)
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^session_limit$"):
            session.run(inputs, request)
    assert host.events == ["build", "run", "close"]


@pytest.mark.parametrize("reason", ["numeric_rejection", "timeout", "private secret"])
def test_runtime_failure_closes_and_normalizes_reason(host, reason):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    with host.open() as session:
        previous = session.run(*host.ctx[3:])
        host.failure = BoundedC11ApplicationRuntimeError(reason)
        expected = reason if reason in api._REASONS else "runtime_rejected"
        with pytest.raises(api.BoundedModelApplicationSessionError, match=f"^{expected}$"):
            session.run(*host.ctx[3:])
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^closed$"):
            session.run(*host.ctx[3:])
        assert previous.sequence == 1
    assert host.events == ["build", "run", "run", "close"]


def test_response_replay_closes_the_session(host):
    with host.open() as session:
        session.run(*host.ctx[3:])
        host.replay = True
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^response_rejected$"):
            session.run(*context(values=(5.0, 6.0, 7.0, 8.0))[3:])
    assert host.events == ["build", "run", "run", "close"]


def test_capability_mutation_closes_before_another_process(host, tmp_path):
    model, bindings, bundle, inputs, request = host.ctx
    bindings = copy.deepcopy(bindings)
    with api.open_bounded_model_application(model, bindings, bundle, workspace=tmp_path) as session:
        session.run(inputs, request)
        object.__setattr__(bindings[0].capability, "name", "changed-context")
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^context_drift$"):
            session.run(inputs, request)
    assert host.events == ["build", "run", "close"]


@pytest.mark.parametrize("after_run", [False, True])
def test_handle_program_drift_closes(host, after_run):
    with host.open() as session:
        if after_run:
            session.run(*host.ctx[3:])
            host.built.program_digest = "0" * 64
        else:
            host.wrong_digest = True
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^graph_drift$"):
            session.run(*host.ctx[3:])
    assert host.events.count("close") == 1


def test_cleanup_failure_retains_handle_for_retry(host):
    session = host.open()
    session.run(*host.ctx[3:])
    host.close_failure = True
    with pytest.raises(api.BoundedModelApplicationSessionError, match="^cleanup_failed$"):
        session.close()
    with pytest.raises(api.BoundedModelApplicationSessionError, match="^closed$"):
        session.run(*host.ctx[3:])
    host.close_failure = False
    session.close()
    assert host.events == ["build", "run", "close", "close"]


def test_interrupt_closes_before_propagating(host):
    session = host.open()
    host.failure = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        session.run(*host.ctx[3:])
    session.close()
    assert host.events == ["build", "run", "close"]


def test_build_failure_is_terminal(host, monkeypatch):
    from tuc.runtime import bounded_c11_application as runtime

    def fail(*args, **kwargs):
        host.events.append("build")
        raise runtime.BoundedC11ApplicationRuntimeError("build_failed")

    monkeypatch.setattr(runtime, "build_bounded_c11_application", fail)
    with host.open() as session:
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^build_failed$"):
            session.run(*host.ctx[3:])
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^closed$"):
            session.run(*host.ctx[3:])
    assert host.events == ["build"]


def test_concurrent_run_and_close_reject_without_interrupting_owner(host):
    host.block, host.release = threading.Event(), threading.Event()
    session = host.open()
    results = []
    owner = threading.Thread(target=lambda: results.append(session.run(*host.ctx[3:])))
    owner.start()
    try:
        assert host.block.wait(5)
        for operation in (lambda: session.run(*host.ctx[3:]), session.close):
            with pytest.raises(api.BoundedModelApplicationSessionError, match="^session_busy$"):
                operation()
    finally:
        host.release.set()
        owner.join(5)
        session.close()
    assert not owner.is_alive()
    assert len(results) == 1 and results[0].sequence == 1
    assert host.events == ["build", "run", "close"]


@pytest.mark.parametrize("workspace", ["secret-path", Path("relative"), Path("/tmp/../secret")])
def test_workspace_rejection_is_inert(host, workspace):
    with pytest.raises(api.BoundedModelApplicationSessionError, match="^workspace_rejection$"):
        api.open_bounded_model_application(*host.ctx[:3], workspace=workspace)
    assert not host.events


def test_forged_construction_and_subclassing_are_rejected(host):
    with pytest.raises(TypeError):
        api.BoundedModelApplicationSession()
    with pytest.raises(TypeError):
        type("Forged", (api.BoundedModelApplicationSession,), {})
    forged = object.__new__(api.BoundedModelApplicationSession)
    for operation in (lambda: forged.run(*host.ctx[3:]), forged.close, forged.__enter__):
        with pytest.raises(api.BoundedModelApplicationSessionError, match="^handle_rejected$"):
            operation()
