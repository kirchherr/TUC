"""Pure tests for the fixed Add/Bias native conformance consumer."""

import importlib.util
import json
import struct
from pathlib import Path

import pytest


@pytest.fixture
def native_consumer(tmp_path, monkeypatch):
    folder = Path(__file__).resolve().parents[1] / "integration/bounded_add_bias_native"
    spec = importlib.util.spec_from_file_location(
        "add_bias_native_consumer", folder / "consumer.py")
    consumer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(consumer)
    for name in (*consumer.SUPPORT_FILES, "consumer.py"):
        (tmp_path / name).write_bytes((folder / name).read_bytes())
    # Synthetic host test binding, explicitly not an observed wheel/execution fixture.
    (tmp_path / "wheel-sha256.txt").write_text("sha256:" + "0" * 64 + "\n", encoding="ascii")
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    return consumer


def test_native_harness_is_pure_bound_and_counts_are_explicit(native_consumer):
    proof = native_consumer
    files = proof.artifact_files()
    report = proof.report(files)
    assert report["native_execution_observed"] is False
    assert report["cuda_execution_observed"] is False
    assert len(report["graphs"]) == 4 and len(report["controls"]) == 28
    assert report["expected_baseline"] == {
        "schema_version": "tuc.bounded_add_bias_native_observation.v0",
        "binding_digest": report["binding_digest"], "fault": 0,
        "status": "PASS", "reason": "none", "case_runs": 24, "entrypoint_calls": 136,
        "scalar_checks": 114, "published_outputs": 24, "rejected_cases": 112,
        "sentinel_checks": 532,
    }
    assert proof.reference_outputs("vector", 0) == {"sum": (-2.75, -1.5, -0.25, 1.0, -1.0)}
    assert proof.reference_outputs("bias", 0) == {"sum": (-2.75, -1.5, -0.25, -1.25, 0.0, 1.25)}
    zeros = proof.reference_outputs("vector", 2)["sum"]
    assert [struct.unpack("<I", struct.pack("<f", n))[0] for n in zeros] == [
        0, 0x80000000, 0, 0, 0x80000000]
    assert "case 20:" in files["worker.c"] and "case 21:" in files["worker.c"]
    assert "fixture->elements[2]" in files["worker.c"]
    assert "fixture->elements[3]" in files["worker.c"]
    assert "-fsanitize=address,undefined" in files["build.sh"]
    assert "-fno-sanitize-recover=all" in files["build.sh"]
    assert "--network=none" in files["operator.sh"]
    assert "--read-only" in files["operator.sh"]
    assert "--gpus" not in files["operator.sh"]
    assert "consumer.py --accept" in files["operator.sh"]
    assert "> record.json" in files["operator.sh"]
    assert not any(name.endswith(".cu") for name in files)


def test_native_harness_accepts_only_complete_source_bound_protocol_evidence(native_consumer):
    proof = native_consumer
    path = proof.emit_context()
    files = proof.artifact_files()
    for build in ("static", "sanitized"):
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if fault == 0 else f"fault{fault}"
            (path / f"{build}-{suffix}.json").write_text(
                proof._json(proof._expected(files, fault, invalid)), encoding="ascii")
        (path / f"{build}-image-id.txt").write_text("sha256:" + "a" * 64 + "\n", encoding="ascii")
    # These are synthetic protocol fixtures, not measured/observed golden records.
    record = proof.accept(path)
    assert len(record["observations"]) == 10
    assert record["observation_scope"] == "four_fixed_cpu_graphs"
    stale = path / "static-proof.json"
    payload = json.loads(stale.read_text())
    payload["binding_digest"] = "sha256:" + "1" * 64
    stale.write_text(proof._json(payload), encoding="ascii")
    with pytest.raises(ValueError, match="receipt"):
        proof.accept(path)


@pytest.mark.parametrize("text", ["{}{}", '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}',
                                  '{"a":0.0}', '{"a":1234567890}', "[" * 5 + "0" + "]" * 5,
                                  " " * 8193], ids=range(8))
def test_native_receipt_parser_is_bounded_and_duplicate_safe(native_consumer, text):
    with pytest.raises(ValueError):
        native_consumer._receipt_json(text)


def test_native_receipt_count_types_and_context_drift_reject(native_consumer):
    proof = native_consumer
    files = proof.artifact_files()
    expected = proof._expected(files)
    for key, value in expected.items():
        changed = dict(expected)
        changed[key] = float(value) if type(value) is int else None
        with pytest.raises(ValueError):
            proof._exact(changed, expected)
    old_binding = proof._binding(files)
    support = proof.ROOT / "build.sh"
    support.write_text(
        support.read_text() + "\n# independently changed support\n", encoding="utf-8")
    assert proof._binding(proof.artifact_files()) != old_binding
