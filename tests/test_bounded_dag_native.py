"""Pure checks for the fixed native worker boundary; synthetic records only."""

import json
from pathlib import Path

import pytest

from examples import bounded_dag_native as proof


@pytest.fixture(scope="module")
def rows():
    return proof.bundles()


@pytest.fixture(scope="module")
def files(rows):
    return proof.artifact_files(rows)


def test_fixed_matrix_counts_are_derived_from_the_shared_compiler(rows, files):
    report = proof.report(rows, files)
    assert report["plans"] == 36 and report["graphs"] == 12
    counts = report["expected_matrix_counters"]
    assert counts["case_runs"] == 216
    assert counts["cpu_calls"] == 468 and counts["gpu_calls"] == 504
    assert counts["scalar_checks"] == 4212 and counts["published_outputs"] == 324
    assert counts["upload_bytes"] + counts["download_bytes"] == 94152
    assert counts["validation_download_calls"] == counts["gpu_calls"]
    assert not report["native_execution_observed"]
    assert not report["cuda_execution_observed"]
    assert not report["normal_runtime_admission"]


def test_targets_share_hardware_neutral_graph_and_primitive_texts(rows, files):
    for graph in range(12):
        variants = rows[3 * graph:3 * graph + 3]
        assert len({row[4]["hac_ir_digest"] for row in variants}) == 1
        for name in ("generated.c", "generated.h", "kernels.cuh"):
            assert len({row[3].files()[name] for row in variants}) == 1
            assert files[f"cases/{graph:02d}/{name}"] == variants[0][3].files()[name]
        for index, row in enumerate(variants, 3 * graph):
            assert files[f"plans/{index:02d}.json"] == row[3].manifest_json
    # One shared worker owns events; per-case glue owns only indexed dispatch.
    assert "family" not in files["worker.h"]
    assert "#include \"generated.c\"" in files["cases/00/host.c"]
    assert "#include \"kernels.cuh\"" in files["cases/00/device.cu"]


def test_context_binds_compiler_oracle_operator_and_workflow(files):
    source = json.loads(files["source-bindings.json"])
    assert set(source) == set(proof.SOURCE_BINDINGS)
    for name in proof.SOURCE_BINDINGS:
        assert source[name] == proof._digest(proof._read(proof.ROOT / name))
    assert files["operator.sh"] == proof._read(proof.CONTEXT / "operator.sh")
    assert files["Dockerfile.dockerignore"].splitlines()[0] == "**"
    assert "!source-bindings.json" not in files["Dockerfile.dockerignore"]
    assert "!operator.sh" not in files["Dockerfile.dockerignore"]


@pytest.mark.parametrize("index", range(36))
def test_every_plan_requires_terminal_completion_and_detects_faults(index, rows):
    baseline = proof.expected_receipt(index, "matrix", rows=rows)
    preflight = proof.expected_receipt(index, "matrix", "preflight", rows=rows)
    assert baseline["case_runs"] == 6
    assert all(preflight[key] == 0 for key in proof.COUNTERS)
    for fault, reason in ((1, "missing_operand"), (2, "numeric_mismatch"),
                          (3, "missing_publication"), (4, "missing_operand")):
        if fault == 4 and index % 3 == 0:
            continue
        value = proof.expected_receipt(index, "matrix", fault=fault, rows=rows)
        assert value["status"] == "ERROR" and value["reason"] == reason
        assert value["case_runs"] == 0
        assert value["published_outputs"] < baseline["published_outputs"]


@pytest.mark.parametrize("index,worker", [(True, "matrix"), (-1, "matrix"),
                                        (36, "matrix"), ("0", "matrix"),
                                        (1, "c11"), (2, "c11"), (0, "cuda")])
def test_unreviewed_selectors_reject_before_emission(index, worker):
    with pytest.raises(ValueError, match="selector"):
        proof.expected_receipt(index, worker)


def test_all_observation_files_are_mandatory_and_distinct(rows):
    cpu = proof.expected_files("c11", rows)
    matrix = proof.expected_files("matrix", rows)
    assert len(cpu) == 125  # 2*(12*(preflight+execute+3faults)+2invalid)+contract
    assert len(matrix) == 206  # 36*(preflight+execute+3faults)+24copyfaults+2invalid
    assert cpu["sanitized-contract.json"]["mutation_checks"] == 194688
    assert set(cpu).isdisjoint(matrix)
    for name, value in cpu.items():
        assert "matrix" not in name and value.get("gpu_calls", 0) == 0


@pytest.mark.parametrize("value", [True, -1, 1_000_001, "1;evil()", object()])
def test_initializer_rejects_noninteger_or_oversized_source_fragments(value):
    with pytest.raises(ValueError):
        proof._array([value])


def test_initializer_structure_budget_and_cycles_are_bounded():
    cyclic = []
    cyclic.append(cyclic)
    for value in ([0] * 97, cyclic, {"a": 1}, [[[[[[1]]]]]]):
        with pytest.raises(ValueError):
            proof._array(value)


def test_initializer_repeated_references_have_an_aggregate_expansion_budget():
    shared = [0] * 96
    expanded = [shared] * 96
    with pytest.raises(ValueError, match="expansion"):
        proof._array(expanded)


@pytest.mark.parametrize("change", [
    {"case_runs": True}, {"case_runs": 6.0}, {"gpu_calls": 1},
    {"unknown": 0}, {"plan_digest": "sha256:" + "0" * 64}, {"status": "ERROR"},
])
def test_exact_receipts_cannot_substitute_types_counters_or_bindings(change, rows):
    expected = proof.expected_receipt(0, "c11", rows=rows)
    with pytest.raises(ValueError, match="observation"):
        proof._exact({**expected, **change}, expected)


def _synthetic_context(monkeypatch, tmp_path, rows, files, worker):
    # Protocol fixture only. No process, image, device or native observation exists.
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, "bundles", lambda: rows)
    monkeypatch.setattr(proof, "artifact_files", lambda rows=None: files.copy())
    path = proof.emit_context()
    for name, value in proof.expected_files(worker, rows).items():
        (path / name).write_text(json.dumps(value), encoding="utf-8")
    for build in (("static", "sanitized") if worker == "c11" else ("matrix",)):
        (path / f"{build}-image-id.txt").write_text("sha256:" + "1" * 64, encoding="utf-8")
    return path


@pytest.mark.parametrize("worker", ["c11", "matrix"])
def test_complete_synthetic_protocol_requires_every_bound_control(
    monkeypatch, tmp_path, rows, files, worker
):
    path = _synthetic_context(monkeypatch, tmp_path, rows, files, worker)
    result = proof.accept(path, worker)
    assert result["worker"] == worker and result["normal_runtime_admission"] is False
    assert set(result["observations"]) == set(proof.expected_files(worker, rows))
    build = "static" if worker == "c11" else "matrix"
    (path / f"{build}-0-fault3.json").unlink()
    with pytest.raises(ValueError, match="bounded file"):
        proof.accept(path, worker)


@pytest.mark.parametrize("name", ["operator.sh", "abi.h", "source-bindings.json",
                                 "cases/11/kernels.cuh", "plans/35.json"])
def test_context_drift_rejects_before_receipts(monkeypatch, tmp_path, rows, files, name):
    path = _synthetic_context(monkeypatch, tmp_path, rows, files, "c11")
    (path / name).write_text(files[name] + "\nchanged\n", encoding="utf-8")
    with pytest.raises(ValueError, match="context drift"):
        proof.accept(path, "c11")


def test_receipts_reject_duplicates_deep_json_and_oversize(
    monkeypatch, tmp_path, rows, files
):
    path = _synthetic_context(monkeypatch, tmp_path, rows, files, "c11")
    receipt = path / "static-0-execute.json"
    for text in ('{"status":"PASS","status":"PASS"}', '[' * 6 + '0' + ']' * 6,
                 ' ' * 4097, '{"case_runs":NaN}'):
        receipt.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError):
            proof.accept(path, "c11")


def test_emission_stays_private_unique_and_inside_workspace(monkeypatch, tmp_path, files):
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, "artifact_files", lambda: files.copy())
    first, second = proof.emit_context(), proof.emit_context()
    assert first != second and first.parent == tmp_path / "tmp"
    assert {str(p.relative_to(first)).replace("\\", "/") for p in first.rglob("*")
            if p.is_file()} == set(files)
    with pytest.raises(ValueError, match="directory"):
        proof.accept(Path(tmp_path), "c11")


def test_candidate_never_launches_processes_devices_or_network(monkeypatch, rows, files):
    import ctypes
    import socket
    import subprocess

    def blocked(*args, **kwargs):
        raise AssertionError("pure candidate crossed execution boundary")

    monkeypatch.setattr(subprocess, "Popen", blocked)
    monkeypatch.setattr(ctypes, "CDLL", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    assert proof.report(rows, files)["native_execution_observed"] is False
