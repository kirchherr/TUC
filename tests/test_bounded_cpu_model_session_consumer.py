"""Independent NumPy oracle and consumer fault tests; no native evidence."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from integration.bounded_cpu_model_session import consumer as c
from tuc import bounded_cpu_model_session as api


@pytest.mark.parametrize("softmax,changed", [(False, False), (True, False), (False, True)])
@pytest.mark.parametrize("x", [[2, 3], [-1, 2]])
def test_equations_match_independent_numpy(softmax, changed, x):
    array = np.asarray(x, dtype=np.float32)
    weight = np.asarray([[3 if changed else 2, -1], [1, 3]], dtype=np.float32)
    expected = weight @ array + np.asarray([0.5, -0.0], dtype=np.float32)
    if softmax:
        exp = np.exp(expected - expected.max(), dtype=np.float32)
        expected = exp / exp.sum(dtype=np.float32)
        np.testing.assert_allclose(c.reference(x, softmax, changed), expected, atol=2e-6, rtol=2e-5)
    else:
        np.testing.assert_array_equal(
            np.asarray(c.reference(x, softmax, changed), dtype=np.float32).view(np.uint32),
            expected.view(np.uint32),
        )


@pytest.mark.parametrize("fault", [None, "output", "identity", "context", "cleanup", "numeric"])
def test_installed_consumer_with_real_session_and_synthetic_runtime(monkeypatch, tmp_path, fault):
    from tuc.runtime import bounded_c11_application as runtime

    state = SimpleNamespace(builds=0, calls=0, closes=0)

    class Built:
        def __init__(self, module, bindings, workspace):
            state.builds += 1
            self.softmax = any(op.family == "softmax" for op in module.operations)
            self.program_digest = api.prepare_bounded_c11_application(
                module, bindings
            ).program_digest
            if fault == "identity":
                self.program_digest = "f" * 64
            self.directory = workspace / "synthetic-context"
            self.directory.mkdir()
            (self.directory / "fixture").write_bytes(b"fixed")

        def run(self, values):
            state.calls += 1
            x = np.asarray(values["x"], dtype=np.float32)
            weight = np.asarray(values["w"], dtype=np.float32).reshape(2, 2)
            with np.errstate(over="ignore", invalid="ignore"):
                scores = weight @ x + np.asarray(values["b"], dtype=np.float32)
            if not np.isfinite(scores).all():
                if fault != "numeric":
                    raise runtime.BoundedC11ApplicationRuntimeError("numeric_rejection")
                return {"scores": (0.0, 0.0)}
            if self.softmax:
                exp = np.exp(scores - scores.max(), dtype=np.float32)
                scores = exp / exp.sum(dtype=np.float32)
            if fault == "output":
                scores[0] += 0.5
            if fault == "context":
                (self.directory / "fixture").write_text(str(state.calls))
            return {"scores": tuple(float(v) for v in scores)}

        def close(self):
            state.closes += 1
            if fault != "cleanup":
                (self.directory / "fixture").unlink()
                self.directory.rmdir()

    monkeypatch.setattr(
        runtime,
        "build_bounded_c11_application",
        lambda module, bindings, workspace: Built(module, bindings, workspace),
    )
    if fault:
        with pytest.raises((AssertionError, api.CPUModelSessionError)):
            c.run(tmp_path)
    else:
        record = c.run(tmp_path)
        assert (state.builds, state.calls, state.closes) == (4, 22, 4)
        assert record["successful_runs"] == 21 and record["scalar_checks"] == 42
        assert record["stable_context_checks"] == 17 and len(record["rejections"]) == 9
        assert all(math.isfinite(v) for r in record["records"] for v in r["outputs"])
    assert not (tmp_path / "record.json").exists()
