"""Pure checks for the fixed installed Mul native harness; no native execution."""

import importlib.util
import json
import re
import struct
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def consumer(tmp_path, monkeypatch):
    folder = Path(__file__).resolve().parents[1] / "integration/bounded_mul_native"
    spec = importlib.util.spec_from_file_location("mul_native_consumer", folder / "consumer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in (*module.SUPPORT_FILES, "consumer.py"):
        (tmp_path / name).write_bytes((folder / name).read_bytes())
    # Synthetic local protocol binding; this is not an observed wheel or native proof.
    (tmp_path / "wheel-sha256.txt").write_text("sha256:" + "0" * 64 + "\n", encoding="ascii")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def _replay(manifest, values):
    tensors = manifest["tensors"]
    physical = {}
    public = {}
    for event in manifest["events"]:
        if event["kind"] == "bind_input":
            slot = event["outputs"][0]
            tensor = tensors[manifest["buffers"][slot]["tensor"]]
            physical[slot] = np.array(values[tensor["name"]], dtype=np.float32).reshape(
                tensor["shape"])
        elif event["kind"] == "execute":
            op = manifest["operations"][event["operation"]]
            args = [physical[slot] for slot in event["inputs"]]
            kind = op["kind"]
            if kind in ("matmul_rhs_transposed", "matmul"):
                right = args[1].T if kind == "matmul_rhs_transposed" else args[1]
                result = np.zeros((args[0].shape[0], right.shape[1]), dtype=np.float32)
                for k in range(args[0].shape[1]):
                    product = np.multiply(args[0][:, k, None], right[None, k, :], dtype=np.float32)
                    result = np.add(result, product, dtype=np.float32)
            elif kind == "mul":
                result = np.multiply(args[0], args[1], dtype=np.float32)
            elif kind in ("add", "add_row_bias"):
                result = np.add(args[0], args[1], dtype=np.float32)
            elif kind == "relu":
                result = np.where(args[0] < 0.0, np.float32(0.0), args[0])
            else:
                assert kind == "sum_axis1"
                result = np.zeros(args[0].shape[0], dtype=np.float32)
                for k in range(args[0].shape[1]):
                    result = np.add(result, args[0][:, k], dtype=np.float32)
            physical[event["outputs"][0]] = result
        elif event["kind"] == "publish_output":
            slot = event["inputs"][0]
            tensor = manifest["buffers"][slot]["tensor"]
            public[tensor] = physical[slot].flatten().tobytes()
        else:
            pytest.fail("CPU-only Mul must not copy across targets")
    return {item["public_name"]: public[item["tensor"]] for item in manifest["public_outputs"]}


@pytest.mark.parametrize("graph", ["square", "matrix", "gated", "mixed"])
@pytest.mark.parametrize("case", [0, 1])
def test_numpy_replay_matches_independent_scalar_oracle_and_native_bits(consumer, graph, case):
    compilation, artifact = consumer.compile_graph(graph)
    manifest = json.loads(compilation.artifacts.manifest_json)
    observed = _replay(manifest, consumer.fixed_inputs(graph, case))
    expected = consumer.reference_outputs(graph, case)
    for name, values in expected.items():
        assert observed[name] == b"".join(struct.pack("<f", value) for value in values)
    assert any(op["kind"] == "mul" for op in manifest["operations"])
    assert "static int tuc_multiply(" in artifact.source
    assert "no CUDA source is emitted" in compilation.artifacts.cuda_source
    files = consumer.artifact_files()
    bits = re.search(rf"uint32_t {graph}_case{case}_expected\[\]=\{{([^}}]+)\}}", files["worker.c"])
    encoded = [int(value, 16) for value in re.findall("0x([0-9a-f]{8})", bits.group(1))]
    assert b"".join(struct.pack("<I", value) for value in encoded) == observed["scores"]


def test_negative_zero_and_square_have_distinct_bit_semantics(consumer):
    square = consumer.reference_outputs("square", 0)["scores"]
    matrix = consumer.reference_outputs("matrix", 0)["scores"]
    assert struct.pack("<f", square[0]) == struct.pack("<I", 0)
    assert struct.pack("<f", matrix[0]) == struct.pack("<I", 0x80000000)
    values = consumer.fixed_inputs("matrix", 1)
    wrong = tuple(a + b for a, b in zip(values["x"], values["scale"], strict=True))
    assert wrong != consumer.reference_outputs("matrix", 1)["scores"]
    public, _ = consumer.compile_graph("square")
    assert len(public.input_bindings) == 1
    assert json.loads(public.artifacts.manifest_json)["operations"][0]["inputs"] == [0, 0]


def test_fixed_counters_isolation_and_fault_protocol_are_explicit(consumer):
    files = consumer.artifact_files()
    report = consumer.report(files)
    assert report["native_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    assert report["cuda_execution_observed"] is False
    assert len(report["graphs"]) == 4 and len(report["controls"]) == 29
    assert report["control_exclusions"] == {"square": ["input_input_alias"]}
    assert "if (graph==0U && control==11) continue;" in files["worker.c"]
    assert report["expected_baseline"] == {
        "schema_version": "tuc.bounded_mul_native_observation.v0",
        "binding_digest": report["binding_digest"], "fault": 0,
        "status": "PASS", "reason": "none", "case_runs": 16, "entrypoint_calls": 131,
        "scalar_checks": 64, "published_outputs": 16, "rejected_cases": 115,
        "sentinel_checks": 459,
    }
    assert "float data[7][14], original[7][14], output[10]" in files["worker.c"]
    assert "case 28:" in files["worker.c"]
    assert "0x0d800000" in files["worker.c"]  # 2**-100 product rounds to zero.
    assert "0x00800000" in files["worker.c"] and "0x3f000000" in files["worker.c"]
    assert "-fsanitize=address,undefined" in files["build.sh"]
    assert "-fno-sanitize-recover=all" in files["build.sh"]
    assert "--network=none" in files["operator.sh"] and "--read-only" in files["operator.sh"]
    assert "--gpus" not in files["operator.sh"] and "> record.json" in files["operator.sh"]
    assert "consumer.py --accept" in files["operator.sh"]
    for fault, reason in ((1, "numeric_mismatch"), (2, "status_mismatch"), (3, "output_modified")):
        expected = consumer._expected(files, fault)
        assert expected["status"] == "ERROR" and expected["reason"] == reason
        assert expected["entrypoint_calls"] == (1 if fault == 1 else 17)
    assert consumer._expected(files, invalid=True)["entrypoint_calls"] == 0


def _synthetic_evidence(consumer):
    path = consumer.emit_context()
    files = consumer.artifact_files()
    for build in ("static", "sanitized"):
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if fault == 0 else f"fault{fault}"
            (path / f"{build}-{suffix}.json").write_text(
                consumer._json(consumer._expected(files, fault, invalid)), encoding="ascii")
        (path / f"{build}-image-id.txt").write_text("sha256:" + "a" * 64 + "\n", encoding="ascii")
    return path


def test_synthetic_complete_receipts_accept_and_stale_binding_rejects(consumer):
    path = _synthetic_evidence(consumer)
    record = consumer.accept(path)
    assert record["schema_version"] == "tuc.bounded_mul_native_record.v0"
    assert len(record["observations"]) == 10
    assert record["observation_scope"] == "four_fixed_mul_cpu_graphs"
    stale = path / "static-proof.json"
    payload = json.loads(stale.read_text())
    payload["binding_digest"] = "sha256:" + "1" * 64
    stale.write_text(consumer._json(payload), encoding="ascii")
    with pytest.raises(ValueError, match="receipt"):
        consumer.accept(path)


@pytest.mark.parametrize("text", ["{}{}", '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}',
                                  '{"a":0.0}', '{"a":1234567890}', "[" * 5 + "0" + "]" * 5,
                                  " " * 8193], ids=range(8))
def test_receipt_parser_is_bounded_duplicate_safe(consumer, text):
    with pytest.raises(ValueError):
        consumer._receipt_json(text)


@pytest.mark.parametrize("changed", [True, False, 1.0, "1", None, [], {}], ids=range(7))
def test_all_receipt_counter_types_exact(consumer, changed):
    expected = consumer._expected(consumer.artifact_files())
    for field in consumer.COUNTERS:
        value = dict(expected, **{field: changed})
        with pytest.raises(ValueError):
            consumer._exact(value, expected)


@pytest.mark.parametrize("change", ["missing", "extra", "artifact", "image", "crash"])
def test_evidence_coverage_context_identity_and_unexpected_failure_reject(consumer, change):
    path = _synthetic_evidence(consumer)
    if change == "missing":
        (path / "sanitized-fault3.json").unlink()
    elif change == "extra":
        (path / "unapproved.txt").write_text("extra")
    elif change == "artifact":
        (path / "square-entrypoint.c").write_text("wrong code")
    elif change == "image":
        (path / "static-image-id.txt").write_text("gcc:latest")
    else:
        (path / "sanitized-fault2.json").write_text("AddressSanitizer: DEADLYSIGNAL")
    with pytest.raises(ValueError):
        consumer.accept(path)


def test_all_support_inputs_bound_and_replay_bytes_deterministic(consumer):
    files = consumer.artifact_files()
    assert consumer.artifact_files() == files
    for name in ("consumer.py", "build.sh", "wheel-sha256.txt"):
        support = consumer.ROOT / name
        original = support.read_text()
        support.write_text(original + "\n# drift\n", encoding="utf-8")
        if name == "wheel-sha256.txt":
            with pytest.raises(ValueError):
                consumer.artifact_files()
        else:
            assert consumer._binding(consumer.artifact_files()) != consumer._binding(files)
        support.write_text(original, encoding="utf-8")
