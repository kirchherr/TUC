"""Session lifecycle and hostile data checks; fake runtimes are not native evidence."""

import builtins
import copy
import json
import threading
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from tests.test_bounded_cpu_model import encode, inputs, model
from tuc import bounded_cpu_model_session as api
from tuc.compiler.bounded_c11_application import encode_bounded_c11_inputs
from tuc.compiler.bounded_cpu_json import inputs_from_json
from tuc.compiler.bounded_cpu_model import BoundedCPUModelError, expand_model_inputs


@pytest.fixture
def host(monkeypatch, tmp_path):
    from tuc.runtime import bounded_c11_application as runtime

    state = SimpleNamespace(
        events=[],
        received=[],
        failure=None,
        close_failure=False,
        wrong_digest=False,
        output=None,
        block=None,
        release=None,
    )

    class Built:
        def __init__(self, module, bindings):
            self.program_digest = api.prepare_bounded_c11_application(
                module, bindings
            ).program_digest
            if state.wrong_digest:
                self.program_digest = "0" * 64

        def run(self, values):
            state.events.append("run")
            state.received.append(values)
            if state.block:
                state.block.set()
                assert state.release.wait(5)
            if state.failure:
                raise state.failure
            if state.output is not None:
                return state.output
            x, w, b = values["x"], values["w"], values["b"]
            return {"scores": (x[0] * w[0] + x[1] * w[1] + b[0], x[0] * w[2] + x[1] * w[3] + b[1])}

        def close(self):
            state.events.append("close")
            if state.close_failure:
                raise RuntimeError("private filesystem details")

    def build(module, bindings, **kwargs):
        state.events.append("build")
        return Built(module, bindings)

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    state.open = lambda: api.open_cpu_model(encode(model()), workspace=tmp_path)
    return state


def test_inert_open_validation_and_close_never_import_runtime(host, monkeypatch):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "tuc.runtime.bounded_c11_application":
            pytest.fail("runtime imported before execution")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    with host.open() as session, pytest.raises(BoundedCPUModelError):
        session.run(inputs({"x": [1]}))
    assert host.events == []


def test_one_build_two_fresh_requests_and_legacy_identity(host):
    with host.open() as session:
        first = session.run(inputs({"x": [2, 3]}))
        second = session.run(inputs({"x": [-1, 2]}))
        assert host.events == ["build", "run", "run"]
        assert first.outputs == (("scores", (1.5, 11.0)),)
        assert second.outputs == (("scores", (-3.5, 5.0)),)
        assert (first.sequence, second.sequence) == (1, 2)
        assert first.model_digest == second.model_digest == session.model_digest
        assert first.program_digest == second.program_digest == session.program_digest
        assert first.request_digest != second.request_digest
        record = api._lookup(session)
        expanded = expand_model_inputs(record.model_data, inputs({"x": [2, 3]}))
        values = inputs_from_json(record.module, record.bindings, record.application, expanded)
        assert (
            first.request_digest
            == encode_bounded_c11_inputs(
                record.module, record.bindings, record.application, values
            )[40:72].hex()
        )
        with pytest.raises(FrozenInstanceError):
            first.sequence = 9
    assert host.events == ["build", "run", "run", "close"]
    session.close()
    assert host.events.count("close") == 1
    with pytest.raises(api.CPUModelSessionError, match="^closed$"):
        session.run(inputs({"x": [0, 0]}))
    with pytest.raises(api.CPUModelSessionError, match="^closed$"):
        session.__enter__()


@pytest.mark.parametrize(
    "payload",
    [
        b"{}",
        b"{",
        b"\xff",
        bytearray(b"{}"),
        None,
        inputs({"x": [1]}),
        inputs({"x": [1, 2], "b": [0.5, 0]}),
        inputs({"x": [True, 2]}),
        inputs({"x": [1e300, 2]}),
        inputs({"x": [1e-40, 2]}),
    ],
)
def test_invalid_data_never_runs_or_consumes_budget_and_can_recover(host, payload):
    with host.open() as session:
        with pytest.raises(BoundedCPUModelError):
            session.run(payload)
        assert host.events == []
        assert session.run(inputs({"x": [2, 3]})).sequence == 1
        with pytest.raises(BoundedCPUModelError):
            session.run(payload)
        assert session.run(inputs({"x": [2, 3]})).sequence == 2
        assert host.events == ["build", "run", "run"]


def test_request_budget_stops_before_seventeenth_execution(host):
    with host.open() as session:
        for i in range(16):
            assert session.run(inputs({"x": [2, 3]})).sequence == i + 1
        with pytest.raises(api.CPUModelSessionError, match="^session_limit$"):
            session.run(inputs({"x": [2, 3]}))
        assert host.events.count("build") == 1 and host.events.count("run") == 16


@pytest.mark.parametrize("limit,accepted", [(7, 0), (8, 1), (16, 2)])
def test_aggregate_budget_counts_fixed_parameters_on_every_run(host, monkeypatch, limit, accepted):
    monkeypatch.setattr(api, "MAX_SESSION_ELEMENTS", limit)
    with host.open() as session:
        for _ in range(accepted):
            session.run(inputs({"x": [2, 3]}))
        with pytest.raises(api.CPUModelSessionError, match="^session_limit$"):
            session.run(inputs({"x": [2, 3]}))
        assert host.events.count("run") == accepted
        assert host.events.count("build") == bool(accepted)


@pytest.mark.parametrize(
    "reason",
    ["numeric_rejection", "timeout", "protocol_rejection", "context_drift", "secret /home/private"],
)
def test_runtime_error_closes_session_and_retains_earlier_result(host, reason):
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError

    with host.open() as session:
        first = session.run(inputs({"x": [2, 3]}))
        host.failure = BoundedC11ApplicationRuntimeError(reason)
        expected = reason if reason in api._RUNTIME_REASONS else "runtime_rejected"
        with pytest.raises(api.CPUModelSessionError, match=f"^{expected}$"):
            session.run(inputs({"x": [2, 3]}))
        assert first.outputs == (("scores", (1.5, 11.0)),)
        with pytest.raises(api.CPUModelSessionError, match="^closed$"):
            session.run(inputs({"x": [2, 3]}))
    assert host.events == ["build", "run", "run", "close"]


@pytest.mark.parametrize(
    "output",
    [
        {},
        {"wrong": (1.0, 2.0)},
        {"scores": (1.0,)},
        {"scores": [1.0, 2.0]},
        {"scores": (True, 2.0)},
        {"scores": (float("nan"), 2.0)},
        {"scores": (float("inf"), 2.0)},
        {"scores": (1e-40, 2.0)},
        {"scores": (1e300, 2.0)},
        {"scores": (0.1, 2.0)},
    ],
)
def test_malformed_outputs_poison_session_without_publishing(host, output):
    host.output = output
    session = host.open()
    with pytest.raises(api.CPUModelSessionError, match="^output_rejected$"):
        session.run(inputs({"x": [2, 3]}))
    assert host.events == ["build", "run", "close"]
    session.close()


def test_cleanup_failure_is_visible_and_retryable(host):
    session = host.open()
    session.run(inputs({"x": [2, 3]}))
    host.close_failure = True
    with pytest.raises(api.CPUModelSessionError, match="^cleanup_failed$"):
        session.close()
    with pytest.raises(api.CPUModelSessionError, match="^closed$"):
        session.run(inputs({"x": [2, 3]}))
    host.close_failure = False
    session.close()
    assert host.events == ["build", "run", "close", "close"]


def test_cleanup_error_overrides_execution_failure(host):
    session = host.open()
    host.failure = ValueError("secret")
    host.close_failure = True
    with pytest.raises(api.CPUModelSessionError, match="^cleanup_failed$"):
        session.run(inputs({"x": [2, 3]}))
    host.close_failure = False
    session.close()


def test_keyboard_interrupt_releases_resources_and_lock(host):
    session = host.open()
    host.failure = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        session.run(inputs({"x": [2, 3]}))
    session.close()
    assert host.events == ["build", "run", "close"]


def test_built_program_identity_must_match_before_run(host):
    host.wrong_digest = True
    with host.open() as session, pytest.raises(api.CPUModelSessionError, match="^graph_drift$"):
        session.run(inputs({"x": [2, 3]}))
    assert host.events == ["build", "close"]


def test_forged_copied_and_mutated_handles_cannot_run(host):
    with pytest.raises(TypeError):
        api.CPUModelSession()
    fake = object.__new__(api.CPUModelSession)
    with pytest.raises(api.CPUModelSessionError, match="^handle_rejected$"):
        fake.run(b"{}")
    with host.open() as session:
        with pytest.raises(AttributeError):
            session.model_digest = "0" * 64
        with pytest.raises(TypeError):
            copy.copy(session)
    assert host.events == []


def test_concurrent_run_and_close_reject_without_affecting_owner(host):
    host.block, host.release = threading.Event(), threading.Event()
    session = host.open()
    results = []
    worker = threading.Thread(target=lambda: results.append(session.run(inputs({"x": [2, 3]}))))
    worker.start()
    try:
        assert host.block.wait(5)
        for operation in (lambda: session.run(inputs({"x": [2, 3]})), session.close):
            with pytest.raises(api.CPUModelSessionError, match="^session_busy$"):
                operation()
    finally:
        host.release.set()
        worker.join(5)
        session.close()
    assert len(results) == 1 and results[0].sequence == 1
    assert host.events == ["build", "run", "close"]


def test_parameter_change_retains_program_but_changes_model_and_results(host, tmp_path):
    changed = model()
    changed["parameters"]["w"][0] = 3
    with host.open() as first, api.open_cpu_model(encode(changed), workspace=tmp_path) as second:
        a, b = first.run(inputs({"x": [2, 3]})), second.run(inputs({"x": [2, 3]}))
        assert a.program_digest == b.program_digest and a.model_digest != b.model_digest
        assert a.outputs != b.outputs and a.request_digest != b.request_digest
    assert host.events.count("build") == 2 and host.events.count("close") == 2


@pytest.mark.parametrize("workspace", [None, "path", 1])
def test_workspace_type_rejects_without_runtime(workspace):
    with pytest.raises(api.CPUModelSessionError, match="^workspace_rejection$"):
        api.open_cpu_model(encode(model()), workspace=workspace)


def test_changed_input_bytes_and_returned_mapping_cannot_mutate_parameters(host):
    with host.open() as session:
        result = session.run(inputs({"x": [2, 3]}))
        mutable = dict(result.outputs)
        mutable["scores"] = (99.0, 99.0)
        assert (
            session.run(inputs(json.loads(inputs({"x": [2, 3]}))["inputs"])).outputs
            == result.outputs
        )


def test_build_failure_closes_without_retry_or_execution(host, monkeypatch):
    from tuc.runtime import bounded_c11_application as runtime

    def fail(*args, **kwargs):
        host.events.append("build")
        raise runtime.BoundedC11ApplicationRuntimeError("build_failed")

    monkeypatch.setattr(runtime, "build_bounded_c11_application", fail)
    with host.open() as session:
        with pytest.raises(api.CPUModelSessionError, match="^build_failed$"):
            session.run(inputs({"x": [2, 3]}))
        with pytest.raises(api.CPUModelSessionError, match="^closed$"):
            session.run(inputs({"x": [2, 3]}))
    assert host.events == ["build"]


def test_output_aggregate_limit_with_large_matmul_and_two_returns(monkeypatch, tmp_path):
    from tuc.runtime import bounded_c11_application as runtime

    graph = {
        "schema_version": "source_intent.v0",
        "name": "expanding_outputs",
        "tensors": [
            {"name": n, "shape": s}
            for n, s in (("x", [64, 1]), ("w", [1, 64]), ("p", [64, 64]), ("y", [64, 64]))
        ],
        "operations": [
            {"name": "mm", "family": "matmul", "inputs": ["x", "w"], "outputs": ["p"]},
            {
                "name": "second_mm",
                "family": "matmul",
                "inputs": ["x", "w"],
                "outputs": ["y"],
            },
        ],
        "returns": [{"public_name": n, "tensor_name": n} for n in ("p", "y")],
    }
    calls = []

    def build(module, bindings, **kwargs):
        def run(values):
            calls.append("run")
            return {"p": (0.0,) * 4096, "y": (0.0,) * 4096}

        return SimpleNamespace(
            program_digest=api.prepare_bounded_c11_application(module, bindings).program_digest,
            run=run,
            close=lambda: calls.append("close"),
        )

    monkeypatch.setattr(runtime, "build_bounded_c11_application", build)
    data = encode(
        {
            "schema_version": "tuc.bounded_cpu_model.v0",
            "graph": graph,
            "parameters": {"w": [0] * 64},
        }
    )
    with api.open_cpu_model(data, workspace=tmp_path) as session:
        for index in range(8):
            assert session.run(inputs({"x": [0] * 64})).sequence == index + 1
        with pytest.raises(api.CPUModelSessionError, match="^session_limit$"):
            session.run(inputs({"x": [0] * 64}))
    assert calls == ["run"] * 8 + ["close"]
