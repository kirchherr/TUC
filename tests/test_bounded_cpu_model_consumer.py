"""Independent NumPy equations and consumer fault controls; no native evidence."""

import copy
import importlib.util
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_model import consumer as c
from tuc import bounded_cpu_application_cli as cli
from tuc.compiler.bounded_cpu_model import model_from_json, pack_model


def numpy_reference(family, profile, envelope):
    values = {k: np.asarray(v, dtype=np.float32) for k, v in envelope["inputs"].items()}

    def linear(x, weight, rows, inner, columns):
        x, weight = x.reshape(rows, inner), weight.reshape(columns, inner)
        output = np.zeros((rows, columns), dtype=np.float32)
        for index in range(inner):
            output = np.add(
                output,
                np.multiply(x[:, index, None], weight[None, :, index], dtype=np.float32),
                dtype=np.float32,
            )
        return output

    def probabilities(x):
        shifted = np.subtract(x, x.max(axis=1, keepdims=True), dtype=np.float32)
        exp = np.exp(shifted, dtype=np.float32)
        total = np.zeros((len(x), 1), dtype=np.float32)
        for index in range(x.shape[1]):
            total = np.add(total, exp[:, index, None], dtype=np.float32)
        return np.divide(exp, total, dtype=np.float32)

    if family == "attention":
        m, k, s, d = ((2, 4, 3, 2), (1, 2, 4, 3))[profile]
        logits = linear(values["q"], values["key"], m, k, s)
        p = probabilities(np.multiply(logits, values["scale"], dtype=np.float32))
        result = np.zeros((m, d), dtype=np.float32)
        for i in range(s):
            result = np.add(
                result,
                np.multiply(
                    p[:, i, None], values["value"].reshape(s, d)[None, i, :], dtype=np.float32
                ),
                dtype=np.float32,
            )
    else:
        m, k, n = (((2, 3, 3), (1, 2, 2)) if family == "linear" else ((2, 3, 4), (1, 2, 3)))[
            profile
        ]
        x = values["x"].reshape(m, k)
        if family == "classifier":
            x = np.add(
                np.multiply(x, values["gain"], dtype=np.float32), values["offset"], dtype=np.float32
            )
        result = np.add(linear(x, values["weight"], m, k, n), values["bias"], dtype=np.float32)
        if family == "classifier":
            result = probabilities(result)
    return result.ravel()


@pytest.mark.parametrize("family", c.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_oracle_and_model_identity_independently(family, profile, case):
    values = c.data(family, profile, case)
    expected = numpy_reference(family, profile, values)
    actual = np.asarray(c.reference(family, profile, values)["scores"], dtype=np.float32)
    if family == "linear":
        np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))
    else:
        np.testing.assert_allclose(actual, expected, rtol=c.RTOL, atol=c.ATOL)
    packed = pack_model(
        c.encoded(c.graph(family, profile)),
        c.encoded(
            {"schema_version": c.INPUT_SCHEMA, "inputs": c.fixed_parameters(family, profile)}
        ),
    )
    assert model_from_json(packed).model_digest == c.model_identity(json.loads(packed))


@pytest.mark.parametrize("change", ["material", "nan", "wrong_name", "extra", "short", "boolean"])
def test_numeric_checker_rejects_material_or_structural_faults(change):
    expected = c.reference("classifier", 0, c.data("classifier", 0, 0))
    bad = copy.deepcopy(expected)
    if change == "material":
        bad["scores"][0] += 0.25
    elif change == "nan":
        bad["scores"][0] = float("nan")
    elif change == "wrong_name":
        bad["secret"] = bad.pop("scores")
    elif change == "extra":
        bad["extra"] = []
    elif change == "short":
        bad["scores"].pop()
    else:
        bad["scores"][0] = True
    with pytest.raises(ValueError):
        c.check_outputs(bad, expected, "classifier", 0)


def test_bitwise_checker_keeps_signed_zero():
    with pytest.raises(ValueError):
        c.check_outputs({"scores": [0.0]}, {"scores": [-0.0]}, "linear", 0)


def test_candidate_and_import_have_no_process_effect(monkeypatch):
    monkeypatch.setattr(c.subprocess, "Popen", lambda *a, **k: pytest.fail("process called"))
    path = Path(c.__file__)
    spec = importlib.util.spec_from_file_location("inert_model_consumer", path)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    report = instance.candidate()
    assert report["native_execution_observed"] is False and len(report["models"]) == 6
    assert report["planned_scalar_checks"] == 110
    assert report["planned_bitexact_scalar_checks"] == 38


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "program",
        "model",
        "request",
        "batch",
        "output",
        "negative_stdout",
        "wrong_error",
        "dirty_workspace",
    ],
)
def test_whole_consumer_checks_real_cli_dataflow_with_synthetic_runtime(
    monkeypatch, tmp_path, capsys, fault
):
    from tuc.runtime import bounded_c11_application as runtime

    monkeypatch.setattr(c, "ROOT", tmp_path)
    monkeypatch.setattr(c, "_installed_cli", lambda: Path("unused"))
    monkeypatch.setattr(cli, "_require_platform", lambda: None)
    monkeypatch.setattr(cli, "_read_file", lambda name, limit: Path(name).read_bytes())

    class Built:
        def __init__(self, module):
            self.family, self.profile = module.name.removeprefix("model_").rsplit("_", 1)

        def __enter__(self):
            return self

        def run(self, values):
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                result = numpy_reference(self.family, int(self.profile), {"inputs": values})
            if not np.isfinite(result).all():
                raise runtime.BoundedC11ApplicationRuntimeError("numeric_rejection")
            return {"scores": tuple(float(x) for x in result)}

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        runtime, "build_bounded_c11_application", lambda module, *a, **k: Built(module)
    )

    def invoke(executable, args):
        code = cli.main(args)
        captured = capsys.readouterr()
        output, error = captured.out.encode(), captured.err.encode()
        if code == 0 and args[0] in {"run-model", "run-model-batch"}:
            report = json.loads(output)
            if fault in {"program", "model"}:
                report[fault + "_digest"] = "f" * 64
            elif fault == "request" and args[0] == "run-model":
                report["request_digest"] = "a" * 64
            elif fault == "batch" and args[0] == "run-model-batch":
                report["batch_digest"] = "b" * 64
            elif fault == "output" and args[0] == "run-model":
                report["outputs"]["scores"][0] += 0.25
            elif fault == "dirty_workspace":
                (Path(args[-1]) / "leftover").write_text("bad")
            output = c.encoded(report)
        if code != 0:
            if fault == "negative_stdout":
                output = b"partial result"
            elif fault == "wrong_error":
                error = b"tuc-cpu-app: process_error\n"
        return code, output, error

    monkeypatch.setattr(c, "_invoke", invoke)
    if fault:
        with pytest.raises(ValueError):
            c.run()
        assert not (tmp_path / "record.json").exists()
    else:
        report = c.run()
        assert report["single_runs"] == 13 and report["batch_request_runs"] == 12
        assert report["scalar_checks"] == 110 and report["row_mass_checks"] == 12
        assert report["negative_controls"] == 8 and report["numeric_rejections"] == 2
        assert len(report["numeric_controls"][-1]["requests"]) == 2
        assert (
            report["models"][0]["program_digest"] == report["parameter_variant"]["program_digest"]
        )
        assert report["models"][0]["model_digest"] != report["parameter_variant"]["model_digest"]
        # This synthetic test report is temporary and never retained as CI evidence.
        assert struct.pack("<f", c.fixed_parameters("linear", 0)["bias"][-1])[-1] == 0x80
