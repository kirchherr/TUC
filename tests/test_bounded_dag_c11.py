"""Pure fixed-context and synthetic protocol checks, not native observations."""

from __future__ import annotations

import ast
import copy
import json
import re
from dataclasses import replace

import pytest

from examples import bounded_dag_c11 as proof


@pytest.fixture(scope="module")
def artifacts():
    return proof.artifact_files()


def test_fixed_context_has_twelve_cpu_cases_and_no_admission(artifacts):
    report = proof.report(artifacts)
    assert report["compiled_cases"] == 12
    assert report["input_cases"] == 3 and report["replays"] == 2
    assert report["native_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    assert report["cuda_execution_observed"] is False
    assert not any("cuda" in name or name.endswith(".cuh") for name in artifacts)
    assert len(artifacts) == 66
    assert artifacts == proof.artifact_files()
    for index in range(12):
        base = f"cases/{index:02d}/"
        manifest = json.loads(artifacts[base + "manifest.json"])
        assert manifest["planned_copy_bytes"] == 0
        assert {op["target"] for op in manifest["operations"]} == {"c11"}
        worker = artifacts[base + "worker.c"]
        assert worker.count("tuc_dag_op_") == len(manifest["operations"]) * 2
        assert worker.count("tuc_poison(") == len(manifest["buffers"])
        assert worker.count("tuc_check(") == len(manifest["output_tensors"])
        assert worker.count("tuc_normal_finite(") == len(manifest["operations"])
        assert "replay < 2U" in worker and "vector < 3U" in worker
        for buffer in manifest["buffers"]:
            assert f"float slot_{buffer['index']}[{buffer['bytes'] // 4}];" in worker


@pytest.mark.parametrize("family", proof.FAMILIES)
@pytest.mark.parametrize("shape", proof.SHAPES)
def test_independent_reference_covers_every_terminal_and_finite_vector(family, shape):
    expected_names = {"raw", "row_sum"} if family in ("fanout", "diamond") else {"row_sum"}
    for case in range(proof.INPUT_CASES):
        values = proof.reference_outputs(family, shape, case)
        assert set(values) == expected_names
        assert all(len(output) == shape[0] for output in values.values())
        assert all(proof.math.isfinite(x) for output in values.values() for x in output)


def test_reference_is_independent_of_graph_compiler_and_metadata(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("oracle must not use compiler metadata")

    monkeypatch.setattr(proof.portfolio, "compile_case", forbidden)
    monkeypatch.setattr(proof.portfolio, "graph_for", forbidden)
    assert proof.reference_outputs("chain", (1, 1, 1), 0) == {"row_sum": [0.25]}
    assert proof.reference_outputs("fanout", (1, 1, 1), 0) == {
        "raw": [0.25], "row_sum": [0.25]
    }
    assert proof.reference_outputs("fanin", (1, 1, 1), 0) == {"row_sum": [0.0]}
    assert proof.reference_outputs("diamond", (1, 1, 1), 0) == {"raw": [0.0], "row_sum": [0.0]}
    assert proof.reference_outputs("fanin", (1, 1, 1), 2)["row_sum"][0] > 0


@pytest.mark.parametrize("field", ("c11_header", "c11_source", "schedule_header", "manifest_json"))
def test_changed_compiler_text_rejected_before_context_creation(monkeypatch, field):
    compiled, value = proof.portfolio.compile_case("chain", "ccc", (1, 1, 1))
    wrong = replace(value, **{field: getattr(value, field) + "\n/* corrupt */"})
    monkeypatch.setattr(proof.portfolio, "compile_case", lambda *args: (compiled, wrong))
    with pytest.raises(ValueError, match="binding"):
        proof.artifact_files()


def test_all_cpu_worker_rejects_device_schedule(artifacts):
    manifest = json.loads(artifacts["cases/00/manifest.json"])
    manifest["planned_copy_bytes"] = 4
    with pytest.raises(ValueError, match="copies"):
        proof._worker(0, "chain", (1, 1, 1), manifest)
    manifest["planned_copy_bytes"] = 0
    manifest["operations"][0]["target"] = "cuda-sm86"
    with pytest.raises(ValueError, match="device"):
        proof._worker(0, "chain", (1, 1, 1), manifest)


@pytest.mark.parametrize("mutation", (None, *proof.MUTATIONS))
def test_synthetic_receipt_requires_every_exact_field(mutation):
    value = proof.expected_receipt(mutation)
    assert proof.validate_receipt(value, mutation) == value
    for key in value:
        wrong = copy.deepcopy(value)
        wrong[key] = "changed"
        with pytest.raises(ValueError, match="observation"):
            proof.validate_receipt(wrong, mutation)
    with pytest.raises(ValueError, match="observation"):
        proof.validate_receipt({**value, "unexpected": 1}, mutation)
    if mutation:
        assert value["rejected_cases"] == 12
        with pytest.raises(ValueError, match="observation"):
            proof.validate_receipt(value)


def test_boolean_cannot_replace_integer_count():
    value = proof.expected_receipt()
    value["case_runs"] = True
    with pytest.raises(ValueError):
        proof.validate_receipt(value)


def test_duplicate_receipt_keys_and_excess_nesting_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        proof._receipt_json('{"status":"ERROR","status":"PASS"}')
    with pytest.raises(ValueError, match="nesting"):
        proof._receipt_json("[" * 2000 + "]" * 2000)


@pytest.mark.parametrize("value", ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"))
def test_receipt_rejects_nonfinite_numbers_before_protocol_comparison(value):
    with pytest.raises(ValueError, match="nonfinite"):
        proof._receipt_json('{"case_runs":' + value + "}")


def test_receipt_budget_does_not_depend_on_python_recursion_limit():
    with pytest.raises(ValueError, match="nesting"):
        proof._receipt_json("[" * (proof.MAX_RECEIPT_DEPTH + 1) + "0" +
                            "]" * (proof.MAX_RECEIPT_DEPTH + 1))
    with pytest.raises(ValueError, match="item budget"):
        proof._receipt_json("[" + ",".join("0" for _ in range(65)) + "]")
    with pytest.raises(ValueError, match="byte budget"):
        proof._receipt_json(" " * (proof.MAX_RECEIPT_BYTES + 1))
    text = json.dumps({"quoted": '[[[[{{{{,::::,"escaped"\\'})
    assert proof._receipt_json(text) == json.loads(text)


@pytest.mark.parametrize("value", (float("nan"), float("inf"), -float("inf"), 1e-40, -1e-40))
def test_python_reference_rejects_nonfinite_and_subnormal_intermediates(value):
    with pytest.raises(ValueError, match="numeric domain"):
        proof._f32(value)


def test_c_format_strings_decode_to_exact_receipt_protocol_without_native_execution(artifacts):
    source = artifacts["main.c"]
    formats = []
    for group in re.findall(r'printf\(((?:"(?:\\.|[^"\\])*"\s*)+)', source):
        formats.append("".join(ast.literal_eval(token)
                               for token in re.findall(r'"(?:\\.|[^"\\])*"', group)))
    assert len(formats) == 3
    assert all(value.endswith("\n") and "\\n" not in value for value in formats)
    failure = formats[1].replace("%zu", "%d") % ("missing_operand", 12)
    assert proof.validate_receipt(json.loads(failure), "skip-operation")
    success = formats[2].replace("%zu", "%d") % (72, 324, 1404, 108)
    assert proof.validate_receipt(json.loads(success))


def test_c_wrapper_validates_rounding_denormals_and_internal_deadline(artifacts):
    source = artifacts["main.c"]
    assert "fegetround() != FE_TONEAREST" in source
    assert "(_mm_getcsr() & UINT32_C(0xe040)) != 0U" in source
    assert "#if !defined(__x86_64__) || !defined(__SSE2__)" in source
    assert "(void)alarm(20U);" in source
    assert source.index("_mm_getcsr()") < source.index("cases[i](&counts)")
    assert "category != FP_NORMAL && category != FP_ZERO" in artifacts["common.h"]


def _synthetic_context(monkeypatch, tmp_path, artifacts):
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, "artifact_files", lambda: artifacts.copy())
    path = proof.emit_context()
    for build in ("static", "sanitized"):
        (path / f"{build}-image-id.txt").write_text("sha256:" + "a" * 64)
        for mutation in (None, *proof.MUTATIONS):
            (path / f"{build}-{mutation or 'proof'}.json").write_text(
                json.dumps(proof.expected_receipt(mutation))
            )
    return path


def test_exclusive_emission_never_overwrites_existing_context(monkeypatch, tmp_path, artifacts):
    first = _synthetic_context(monkeypatch, tmp_path, artifacts)
    second = proof.emit_context()
    assert first != second
    assert first.parent == second.parent == tmp_path / "tmp"
    assert (first / "static-proof.json").is_file()
    assert not (second / "static-proof.json").exists()


def test_synthetic_complete_receipt_acceptance_and_changed_source_rejection(
    monkeypatch, tmp_path, artifacts
):
    path = _synthetic_context(monkeypatch, tmp_path, artifacts)
    record = proof.accept(path)
    assert record["observation_scope"] == "fixed_cpu_portfolio_only"
    assert record["cuda_execution_observed"] is False
    assert record["normal_runtime_admission"] is False
    assert len(record["observations"]) == 8
    (path / "cases/11/generated.c").write_text("corrupted")
    with pytest.raises(ValueError, match="context changed"):
        proof.accept(path)


def test_operator_is_digest_bound_but_excluded_from_native_context(
    monkeypatch, tmp_path, artifacts
):
    assert artifacts["operator.sh"] == (proof.CONTEXT / "operator.sh").read_text()
    assert "!operator.sh" not in artifacts["Dockerfile.dockerignore"]
    assert artifacts["Dockerfile.dockerignore"].splitlines()[0] == "**"
    changed = {**artifacts, "operator.sh": artifacts["operator.sh"] + "\n# changed\n"}
    assert proof.report(changed)["context_digest"] != proof.report(artifacts)["context_digest"]
    path = _synthetic_context(monkeypatch, tmp_path, artifacts)
    (path / "operator.sh").write_text(changed["operator.sh"])
    with pytest.raises(ValueError, match="context changed"):
        proof.accept(path)


def test_receipt_rejects_missing_control_and_unbounded_file(monkeypatch, tmp_path, artifacts):
    path = _synthetic_context(monkeypatch, tmp_path, artifacts)
    receipt = path / "sanitized-corrupt-output.json"
    receipt.unlink()
    with pytest.raises(ValueError, match="evidence file"):
        proof.accept(path)
    receipt.write_text(" " * 4097)
    with pytest.raises(ValueError, match="evidence file"):
        proof.accept(path)


def test_directory_escape_and_parent_file_are_rejected(monkeypatch, tmp_path, artifacts):
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, "artifact_files", lambda: artifacts.copy())
    with pytest.raises(ValueError, match="directory"):
        proof.accept(tmp_path)
    (tmp_path / "tmp").write_text("not a directory")
    with pytest.raises(ValueError, match="parent"):
        proof.emit_context()


def test_emission_parent_symlink_is_rejected(monkeypatch, tmp_path, artifacts):
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, "artifact_files", lambda: artifacts.copy())
    destination = tmp_path / "elsewhere"
    destination.mkdir()
    try:
        (tmp_path / "tmp").symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable for current host account")
    with pytest.raises(ValueError, match="parent"):
        proof.emit_context()


def test_fixed_build_and_operator_preserve_isolation_and_status_checks(artifacts):
    dockerfile = artifacts["Dockerfile"]
    assert "gcc:14.2.0-bookworm@sha256:" in dockerfile
    assert "RUN --network=none" in dockerfile and "FROM scratch AS static" in dockerfile
    build = artifacts["build.sh"]
    assert "-fsanitize=address,undefined" in build
    assert "-ffp-contract=off" in build and "-fno-fast-math" in build
    operator = (proof.CONTEXT / "operator.sh").read_text()
    for flag in ("--network=none", "--read-only", "--user=10001:10001", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges:true", "--pids-limit=32", "--memory=1g"):
        assert flag in operator
    assert 'test "$status" = 1' in operator
    assert "--gpus" not in operator and "--runtime=nvidia" not in operator
    assert "--privileged" not in operator and "seccomp=unconfined" not in operator
