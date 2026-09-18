"""Actual-record comparison and explicitly synthetic hostile protocol fixtures."""

import copy
import hashlib
import json

import pytest

from examples import bounded_dag_native as native
from examples import bounded_dag_native_equivalence as equivalence

GOLDEN = native.ROOT / "tests/golden/proofs"
COUNTER_TOTALS = {
    "cpu": (72, 324, 0, 1404, 108, 0, 0, 0, 0, 0, 0),
    "gpu": (72, 0, 324, 1404, 108, 162, 29472, 108, 5616, 324, 56952),
    "mixed": (72, 144, 180, 1404, 108, 198, 38400, 126, 20664, 180, 38448),
}


@pytest.fixture(scope="module")
def reconstructed():
    return equivalence._reconstruct()


@pytest.fixture(scope="module")
def synthetic_records(reconstructed):
    # These are protocol fixtures, not observed execution evidence. Never publish
    # them as golden records or use their invented image IDs as native provenance.
    rows, context_digest, counts = reconstructed
    result = []
    for worker in ("c11", "matrix"):
        result.append({
            "schema_version": "tuc.bounded_dag_native_record.v0", "status": "PASS",
            "graphs": 12, "plans": 36, "context_digest": context_digest,
            "expected_matrix_counters": equivalence._sum_counters(counts),
            "native_execution_observed": True, "cuda_execution_observed": worker == "matrix",
            "normal_runtime_admission": False, "latency_ns": None, "energy_pj": None,
            "worker": worker, "observation_scope": "fixed_portfolio_only",
            "image_ids": ({"static": "sha256:" + "1" * 64,
                           "sanitized": "sha256:" + "2" * 64} if worker == "c11" else
                          {"matrix": "sha256:" + "3" * 64}),
            "observations": native.expected_files(worker, rows),
        })
    return result


@pytest.fixture
def protocol(monkeypatch, reconstructed, synthetic_records):
    # Cache only the trusted pure reconstruction, not input validation.
    monkeypatch.setattr(equivalence, "_reconstruct", lambda: reconstructed)
    return copy.deepcopy(synthetic_records)


def _assert_totals(report):
    for profile, expected in COUNTER_TOTALS.items():
        assert tuple(report["matrix_profile_counters"][profile][key]
                     for key in native.COUNTERS) == expected
    cpu = report["matrix_profile_counters"]["cpu"]
    assert report["c11_baseline_counters"] == {"static": cpu, "sanitized": cpu}
    total = report["matrix_counters"]
    assert total["case_runs"] == 216
    assert total["cpu_calls"] == 468 and total["gpu_calls"] == 504
    assert total["scalar_checks"] == 4212 and total["published_outputs"] == 324
    assert total["upload_bytes"] + total["download_bytes"] == 94152
    assert total["validation_download_bytes"] == 95400
    assert report["receipt_counts"] == {"c11": 125, "matrix": 206}
    assert report["fault_controls"] == {"c11": 72, "matrix": 132}
    assert report["invalid_invocation_controls"] == {"c11": 4, "matrix": 2}
    assert report["verification_scope"] == "record_validation_only"
    assert report["observation_scope"] == "fixed_portfolio_only"
    assert report["cpu_baselines_equal"] is True
    assert report["one_matrix_image"] is True
    assert report["normal_runtime_admission"] is False
    assert report["latency_ns"] is report["energy_pj"] is None
    assert "independent_reproduction" in report["blocked_claims"]


def test_complete_synthetic_protocol_has_reviewed_totals_without_execution(protocol, monkeypatch):
    import ctypes
    import socket
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier crossed execution boundary")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(ctypes, "CDLL", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    before = copy.deepcopy(protocol)
    report = equivalence.compare_records(*protocol)
    _assert_totals(report)
    assert protocol == before
    report["c11_image_ids"]["static"] = "changed"
    assert protocol == before


def test_actual_native_records_match_fixed_portfolio():
    paths = [GOLDEN / f"bounded_dag_native_{worker}_record.json"
             for worker in ("c11", "matrix")]
    records = [equivalence.load_record(path) for path in paths]
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths] == [
        "598039c13b310b9eb4b3659292686f73470f422c88a0db5a72958e1609d337ec",
        "c7cac5ecddd47c6726af12c83026bba581b136516bb408e94ae822dbb5a501dc",
    ]
    report = equivalence.compare_records(*records)
    _assert_totals(report)
    for worker, record in zip(("c11", "matrix"), records, strict=True):
        assert report[f"{worker}_record_digest"] == native._digest(native._json(record))
    comparison = GOLDEN / "bounded_dag_native_comparison.json"
    assert report == json.loads(comparison.read_text(encoding="utf-8"))


@pytest.mark.parametrize("worker", ("c11", "matrix"))
def test_single_record_api_checks_the_same_contract(worker, protocol):
    record = protocol[worker == "matrix"]
    assert equivalence.validate_record(record, worker) is record
    with pytest.raises(ValueError):
        equivalence.validate_record(record, "matrix" if worker == "c11" else "c11")


@pytest.mark.parametrize("record_index", (0, 1))
@pytest.mark.parametrize("field,value", [
    ("schema_version", "tuc.bounded_dag_native_candidate.v0"), ("status", "ERROR"),
    ("graphs", True), ("plans", 36.0), ("worker", "unreviewed"),
    ("native_execution_observed", False), ("cuda_execution_observed", 1),
    ("normal_runtime_admission", 0), ("latency_ns", 0), ("energy_pj", 0),
    ("observation_scope", "arbitrary_inputs"), ("unexpected", None),
    ("context_digest", "sha256:" + "0" * 64),
])
def test_changed_record_metadata_rejected(record_index, field, value, protocol):
    protocol[record_index][field] = value
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("field", native.COUNTERS)
@pytest.mark.parametrize("value", (True, 0.0, -1, "0", 1_000_001))
def test_counter_types_and_budgets_cannot_be_coerced(field, value, protocol):
    protocol[1]["observations"]["matrix-0-execute.json"][field] = value
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "other"), ("worker", "c11"), ("plan_index", 1),
    ("plan_digest", "sha256:" + "0" * 64), ("mode", "preflight"),
    ("status", "ERROR"), ("reason", "execution_error"), ("unknown", 0),
])
def test_receipt_identity_and_execution_substitution_rejected(field, value, protocol):
    protocol[1]["observations"]["matrix-0-execute.json"][field] = value
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("worker,build", [("c11", "static"), ("c11", "sanitized"),
                                         ("matrix", "matrix")])
@pytest.mark.parametrize("suffix", ("preflight", "execute", "fault1", "fault2", "fault3"))
def test_every_receipt_category_is_mandatory(worker, build, suffix, protocol):
    del protocol[worker == "matrix"]["observations"][f"{build}-0-{suffix}.json"]
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("change", ("copy_fault", "invalid_plan", "invalid_mode", "contract",
                                    "unknown", "renamed", "swapped", "cpu_copy_fault"))
def test_control_coverage_and_exact_receipt_names(change, protocol):
    observations = protocol[1]["observations"]
    if change == "copy_fault":
        del observations["matrix-1-fault4.json"]
    elif change in ("invalid_plan", "invalid_mode"):
        del observations[f"matrix-invalid-{change.split('_')[1]}.json"]
    elif change == "contract":
        del protocol[0]["observations"]["sanitized-contract.json"]
    elif change == "unknown":
        observations["unexpected.json"] = observations["matrix-0-execute.json"]
    elif change == "renamed":
        observations["../matrix-0-execute.json"] = observations.pop("matrix-0-execute.json")
    elif change == "swapped":
        observations["matrix-1-execute.json"] = observations["matrix-0-execute.json"]
    else:
        observations["matrix-0-fault4.json"] = observations["matrix-1-fault4.json"]
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("name", ("matrix-1-fault1.json", "matrix-1-fault2.json",
                                  "matrix-1-fault3.json", "matrix-1-fault4.json",
                                  "matrix-invalid-plan.json", "matrix-invalid-mode.json"))
def test_unrelated_runtime_error_never_satisfies_negative_control(name, protocol):
    protocol[1]["observations"][name]["reason"] = "execution_error"
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


def test_fault_prefix_and_validation_transfer_counters_are_audited(protocol):
    observations = protocol[1]["observations"]
    receipt = observations["matrix-34-fault3.json"]
    assert receipt["published_outputs"] == 1 and receipt["scalar_checks"] == 33
    assert receipt["case_runs"] == 0
    receipt["published_outputs"] = 0
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("which", ("expected_total", "contract_bool", "preflight_count",
                                   "planned_vs_validation", "sanitizer_disagreement"))
def test_nested_metadata_and_separate_counter_categories(which, protocol):
    if which == "expected_total":
        protocol[0]["expected_matrix_counters"]["cpu_calls"] = True
    elif which == "contract_bool":
        protocol[0]["observations"]["sanitized-contract.json"]["plans"] = True
    elif which == "preflight_count":
        protocol[1]["observations"]["matrix-1-preflight.json"]["case_runs"] = 6
    elif which == "planned_vs_validation":
        receipt = protocol[1]["observations"]["matrix-1-execute.json"]
        receipt["download_bytes"] += receipt["validation_download_bytes"]
        receipt["validation_download_bytes"] = 0
    else:
        protocol[0]["observations"]["sanitized-0-execute.json"]["scalar_checks"] += 1
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("image", ("none", "sha256:" + "A" * 64, "sha256:" + "a" * 63,
                                  "sha256:" + "a" * 65, 123, True, "sha256:" + "a" * 64 + "\n"))
def test_image_identity_syntax_is_strict(image, protocol):
    protocol[1]["image_ids"]["matrix"] = image
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


def test_image_roles_and_exact_keys_cannot_be_substituted(protocol):
    protocol[1]["image_ids"] = protocol[0]["image_ids"]
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


def test_baseline_counts_are_independent_of_receipt_expectation_simulator(protocol, monkeypatch):
    original = native.expected_files

    def compromised_expectation(worker, rows):
        result = original(worker, rows)
        if worker == "matrix":
            result["matrix-0-execute.json"]["cpu_calls"] += 1
        return result

    monkeypatch.setattr(native, "expected_files", compromised_expectation)
    protocol[1]["observations"]["matrix-0-execute.json"]["cpu_calls"] += 1
    with pytest.raises(ValueError):
        equivalence.compare_records(*protocol)


@pytest.mark.parametrize("bad", (None, True, [], (), {"observations": {}},
                                  {"key": object()}, {"key": float("nan")},
                                  {"key": "x" * 129}, {"x" * 129: 0}, {1: 0}))
def test_malformed_inputs_reject_before_reconstruction(bad, protocol, monkeypatch):
    def forbidden():
        raise AssertionError("malformed record reached compiler reconstruction")

    monkeypatch.setattr(equivalence, "_reconstruct", forbidden)
    with pytest.raises(ValueError):
        equivalence.compare_records(bad, protocol[1])


def test_cycles_depth_shared_expansion_and_custom_containers_reject(protocol, monkeypatch):
    class CustomDict(dict):
        def items(self):
            raise AssertionError("custom container executed")

    def forbidden():
        raise AssertionError("unbounded record reached compiler reconstruction")

    monkeypatch.setattr(equivalence, "_reconstruct", forbidden)
    cyclic = {}
    cyclic["cycle"] = cyclic
    deep = {"a": {"a": {"a": {"a": {"a": 0}}}}}
    shared = {str(i): 0 for i in range(200)}
    expanded = {str(i): shared for i in range(26)}
    for bad in (cyclic, deep, expanded, CustomDict(), {str(i): 0 for i in range(207)}):
        with pytest.raises(ValueError):
            equivalence.compare_records(bad, protocol[1])


@pytest.mark.parametrize("text", (
    '{"status":"PASS","status":"PASS"}',
    '{"observations":{"a":{"case_runs":0,"case_runs":0}}}',
    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1.0}',
    '{"x":1e400}', '{"x":-1}', '{"x":1000001}', '{"x":' + '9' * 5000 + '}',
    '[' * 10000 + '0' + ']' * 10000, ' ' * (256 * 1024 + 1),
    '{"unterminated":"value}', '{"x":"\\ud800"}',
), ids=("duplicate_root", "duplicate_nested", "nan", "infinity", "negative_infinity",
        "float", "overflow_float", "negative_integer", "oversized_integer", "huge_integer",
        "deep", "oversized", "malformed", "surrogate"))
def test_bounded_json_rejects_ambiguous_and_unbounded_text(text, tmp_path):
    path = tmp_path / "record.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        equivalence.load_record(path)


def test_json_nesting_scan_ignores_escaped_quotes_and_braces():
    value = {"text": '{[\\\"]}}}}'}
    assert equivalence._json_record(json.dumps(value)) == value


def test_loader_bounds_raw_file_bytes_and_rejects_nonfiles(tmp_path):
    with pytest.raises(ValueError):
        equivalence.load_record(tmp_path)
    path = tmp_path / "oversized.json"
    path.write_bytes(b" " * (equivalence.MAX_RECORD_BYTES + 1))
    with pytest.raises(ValueError):
        equivalence.load_record(path)
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeError):
        equivalence.load_record(path)


def test_cli_reads_only_records_and_returns_sanitized_errors(
    protocol, tmp_path, monkeypatch, capsys
):
    paths = [tmp_path / f"{worker}.json" for worker in ("c11", "matrix")]
    for path, value in zip(paths, protocol, strict=True):
        path.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["bounded_dag_native_equivalence", *(str(p) for p in paths)])
    assert equivalence.main() == 0
    _assert_totals(json.loads(capsys.readouterr().out))
    paths[0].write_text('{"secret-path-marker":NaN}', encoding="utf-8")
    assert equivalence.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "bounded DAG native comparison rejected\n"
