"""Independent scaling oracle and strict evidence boundaries; no native execution."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_scaling_native import consumer


def numpy_reference(graph, case):
    data = {name: np.asarray(value, dtype=np.float32)
            for name, value in consumer.fixed_inputs(graph, case).items()}

    def linear(x, w, m, k, n):
        left, right = x.reshape(m, k), w.reshape(n, k)
        value = np.zeros((m, n), dtype=np.float32)
        for i in range(k):
            value = np.add(value, np.multiply(left[:, i, None], right[None, :, i],
                                              dtype=np.float32), dtype=np.float32)
        return value

    def softmax(value):
        shifted = np.subtract(value, np.max(value, axis=1, keepdims=True), dtype=np.float32)
        exp = np.exp(shifted, dtype=np.float32)
        total = np.zeros((len(value), 1), dtype=np.float32)
        for i in range(value.shape[1]):
            total = np.add(total, exp[:, i, None], dtype=np.float32)
        return np.divide(exp, total, dtype=np.float32)

    if graph == "scalar":
        result = np.multiply(data["x"], data["scale"], dtype=np.float32)
    elif graph == "row_scale":
        result = np.multiply(data["x"].reshape(2, 3), data["scale"], dtype=np.float32)
    elif graph == "attention":
        logits = linear(data["q"], data["k"], 2, 4, 3)
        probabilities = softmax(np.multiply(logits, data["scale"], dtype=np.float32))
        result = np.zeros((2, 2), dtype=np.float32)
        for i in range(3):
            product = np.multiply(probabilities[:, i, None],
                                  data["v"].reshape(3, 2)[None, i, :], dtype=np.float32)
            result = np.add(result, product, dtype=np.float32)
    else:
        scaled = np.multiply(data["x"].reshape(2, 3), data["gain"], dtype=np.float32)
        calibrated = np.add(scaled, data["offset"], dtype=np.float32)
        logits = np.add(linear(calibrated, data["weight"], 2, 3, 4), data["bias"], dtype=np.float32)
        result = softmax(logits)
    return result.ravel()


@pytest.mark.parametrize("graph", consumer.GRAPHS)
@pytest.mark.parametrize("case", range(2))
def test_independent_numpy_oracle_and_exact_public_shapes(graph, case):
    expected = numpy_reference(graph, case)
    actual = np.asarray(consumer.reference_outputs(graph, case)["scores"], dtype=np.float32)
    if graph in ("scalar", "row_scale"):
        np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))
    else:
        np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=2e-6)
    compilation, _ = consumer.compile_graph(graph)
    assert {item.public_name for item in compilation.input_bindings} == set(
        consumer.fixed_inputs(graph, case))
    assert len(actual) == np.prod(compilation.output_bindings[0].shape)
    if graph == "classifier":
        assert np.all(actual > 0) and np.all(actual <= 1)
        np.testing.assert_allclose(actual.reshape(2, -1).sum(axis=1), 1, rtol=0, atol=8e-6)


@pytest.fixture
def context(monkeypatch, tmp_path):
    original = consumer.ROOT
    for name in (*consumer.SUPPORT_FILES, "consumer.py"):
        (tmp_path / name).write_bytes((original / name).read_bytes())
    (tmp_path / "wheel-sha256.txt").write_text("sha256:" + "a" * 64 + "\n")
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    return consumer.artifact_files()


def test_context_is_inert_bounded_and_covers_every_exclusion(context):
    report = consumer.report(context)
    assert report["native_execution_observed"] is False
    assert len(report["controls"]) == 31
    counts = report["expected_baseline"]
    rejected = sentinels = scalars = 0
    for graph in consumer.GRAPHS:
        excluded = report["control_exclusions"][graph]
        applicable = len(consumer.CONTROLS) - len(excluded)
        outputs = len(consumer.reference_outputs(graph, 0)["scores"])
        rejected += applicable
        sentinels += applicable * outputs
        scalars += 4 * outputs
    assert rejected == counts["rejected_cases"] == 118
    assert sentinels == counts["sentinel_checks"] == 677
    assert scalars == counts["scalar_checks"] == 92
    assert counts["entrypoint_calls"] == 16 + rejected
    assert sum(len(text.encode()) for text in context.values()) <= consumer.MAX_CONTEXT_BYTES
    assert 'output[1] += 0.25F' in context["worker.c"]


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1.0}',
                                   '{"x":1234567890}', "[" * 5 + "]" * 5])
def test_strict_receipt_decoder_rejects_ambiguous_or_overbudget_data(raw):
    with pytest.raises(ValueError):
        consumer._receipt_json(raw)


def write_synthetic_observations(directory, context):
    for build in ("static", "sanitized"):
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if not fault else f"fault{fault}"
            (directory / f"{build}-{suffix}.json").write_text(
                consumer._json(consumer._expected(context, fault, invalid)))
        (directory / f"{build}-image-id.txt").write_text("sha256:" + "b" * 64 + "\n")


@pytest.mark.parametrize("mutation", ["counter", "binding", "missing", "extra", "context"])
def test_acceptor_rejects_forged_counts_missing_coverage_and_context_drift(context, mutation):
    directory = consumer.emit_context()
    write_synthetic_observations(directory, context)
    # This uses synthetic data only to exercise acceptance wiring, not as evidence.
    assert len(consumer.accept(directory)["observations"]) == 10
    path = directory / "static-proof.json"
    if mutation in ("counter", "binding"):
        value = json.loads(path.read_text())
        value["scalar_checks" if mutation == "counter" else "binding_digest"] = 0
        path.write_text(json.dumps(value))
    elif mutation == "missing":
        path.unlink()
    elif mutation == "extra":
        (directory / "unexpected.json").write_text("{}")
    else:
        (directory / "worker.c").write_text("changed")
    with pytest.raises(ValueError):
        consumer.accept(directory)


def test_changed_harness_binds_context_and_diagnostics_are_not_forgivable(context):
    changed = copy.copy(context)
    changed["build.sh"] += "\n"
    assert consumer.report(changed)["binding_digest"] != consumer.report(context)["binding_digest"]
    value = consumer._expected(context)
    value["case_runs"] = True
    with pytest.raises(ValueError):
        consumer._exact(value, consumer._expected(context))
    source = Path(consumer.__file__).read_text()
    assert "subprocess" not in source and "ctypes" not in source
