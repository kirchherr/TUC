from __future__ import annotations

import copy
import json
import subprocess
from fractions import Fraction

import numpy as np
import pytest

from examples import bounded_composed_chain as chain
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import source_intent_from_mapping, source_intent_to_triton_metadata
from tuc.runtime import execute_graph


def test_source_chain_reaches_existing_hac_ir_and_trusted_execution():
    module = source_intent_from_mapping(chain.parse_source())
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability,
                                     VectorSimulatorBackend().capability])
    case = chain.corpus()[0]
    # The trusted prototype executor uses float64 storage; native FP32 is separate.
    inputs = {k: np.array(case[k], dtype=np.float64) for k in ("a", "b")}
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    expected = np.maximum(inputs["a"] @ inputs["b"], 0).sum(axis=1)
    np.testing.assert_allclose(execution.output_for("row_sum"), expected, rtol=2e-6)


def test_exact_oracle_cannot_move_relu_after_reduction():
    case = chain.corpus()[0]
    assert case["name"] == "cancellation"
    for wrong, (exact, budget) in zip(chain.fp.ordered_reference(case),
                                     chain.reference(case), strict=True):
        assert abs(Fraction(wrong) - exact) > budget
        assert abs(Fraction(max(wrong, 0)) - exact) > budget


def test_entire_corpus_fits_bound_with_nontrivial_rounding():
    cases = chain.corpus()
    rounded = 0
    for i in (*range(10), 0):
        for actual, (exact, budget) in zip(chain.ordered_reference(cases[i]),
                                          chain.reference(cases[i]), strict=True):
            assert abs(Fraction(actual) - exact) <= budget
            lo, hi = chain.fp.interval(exact, budget)
            assert lo <= actual <= hi
            rounded += actual != float(exact)
    assert rounded == 256
    plan = chain.verify_artifacts()
    assert plan["expected_rounded_outputs"] == rounded
    assert plan["tensor_bytes"] == (231 + 35 + 165 + 165 + 33) * 4
    assert plan["runtime_admission"] is False
    assert plan["contract_digest"] != chain.fp._digest_payload(chain.fp.CONTRACT)


@pytest.mark.parametrize("change", ["axis", "shape", "dtype", "relu", "edge", "symbol", "extra"])
def test_emitter_rejects_unreviewed_semantics(change):
    value = copy.deepcopy(chain.parse_source())
    if change == "axis":
        value["operations"][2]["attributes"]["axis"] = 0
    elif change == "shape":
        value["tensors"][0]["shape"][0] = 34
    elif change == "dtype":
        value["tensors"][0]["dtype"] = "float64"
    elif change == "relu":
        value["operations"][1]["attributes"]["elementwise_kind"] = "identity"
    elif change == "edge":
        value["operations"][2]["inputs"] = ["projection"]
    elif change == "symbol":
        value["operations"][1]["name"] = 'x);system("bad");'
    else:
        value["execute"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        chain.emit(value)


@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), 0.1, 1e100, 2**-30])
def test_oracle_rejects_out_of_domain_inputs(invalid):
    case = chain.corpus()[0]
    case["a"][0][0] = invalid
    with pytest.raises(BoundedCompilerEmissionError):
        chain.reference(case)


def test_three_generated_stages_preserve_nan_poison_and_fixed_bounds():
    files = chain.emit(chain.parse_source())
    assert files["kernels.cuh"].count("__global__ void") == 3
    assert files["generated.c"].count("void tuc_") == 3
    for name in ("generated.c", "kernels.cuh"):
        assert "value < 0.0F ? 0.0F : value" in files[name]
        assert "index < 165U" in files[name]
        assert "row < 33U" in files[name]
    host = (chain.CONTEXT / "host.c").read_text()
    device = (chain.CONTEXT / "device.cu").read_text()
    assert "tuc_sum_axis1(activated, output)" in host
    assert "buffers[5]" in device and "buffers[3], buffers[4]" in device
    assert "cudaMemset(buffers[i], 0xff" in device
    assert "activated[i] = NAN" in host
    assert "relu_blocks = 1U" in device


@pytest.mark.parametrize("target", chain.TARGETS)
def test_observations_bind_order_counts_policy_and_security(target, monkeypatch):
    plan = chain.verify_artifacts()
    monkeypatch.setattr(chain, "verify_artifacts", lambda: plan)
    good = chain.expected_observation(target)
    assert chain.validate_observation(good, target) == good
    for key, value in (("operation_order", ["matmul", "sum_axis1", "relu"]),
                       ("generated_function_calls", 22), ("scalar_checks", 362),
                       ("outputs_differing_from_reference64", 256.0), ("cases_passed", 10),
                       ("tensor_bytes", 1856), ("execution_policy_passed", 1),
                       ("security_boundary_passed", False), ("raw_values_serialized", True),
                       ("untrusted_extra", "bad")):
        with pytest.raises(BoundedCompilerEmissionError):
            chain.validate_observation({**good, key: value}, target)
    with pytest.raises(BoundedCompilerEmissionError):
        chain.validate_observation(chain.expected_observation(target, True), target)


def test_pure_comparison_rejects_record_or_artifact_drift(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier launched a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    cpu, gpu = [chain.build_record(chain.expected_observation(t), t, "sha256:" + "1" * 64)
                for t in chain.TARGETS]
    assert chain.compare_records(cpu, gpu)["status"] == "PASS"
    for key in ("program_files_digest", "operator_image_id", "provenance"):
        with pytest.raises(BoundedCompilerEmissionError):
            chain.compare_records(cpu, {**gpu, key: "wrong"})
    with pytest.raises(BoundedCompilerEmissionError):
        chain.compare_records(cpu, cpu)
    read = chain._read_bounded_file
    monkeypatch.setattr(chain, "_read_bounded_file", lambda p:
                        read(p) + (b"\n" if p.name == "kernels.cuh" else b""))
    with pytest.raises(BoundedCompilerEmissionError):
        chain.verify_artifacts()


def test_native_isolation_and_numerical_policy_remain_explicit():
    script = (chain.ROOT / "scripts/run_bounded_composed_chain.sh").read_text()
    for flag in ("--cuda-reviewed", "--network=none", "--read-only", "--user=10001:10001",
                 "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=1g",
                 "--pids-limit=32", "--gpus=device=0", "timeout 30s", "c11-sanitizer"):
        assert flag in script
    assert "--privileged" not in script and "--volume" not in script
    gpu = (chain.CONTEXT / "build-cuda.sh").read_text()
    assert "--fmad=false --ftz=false" in gpu and "--list-ptx" in gpu
    assert "--dump-sass" in gpu and "/FFMA/" in gpu
    cpu = (chain.CONTEXT / "build-c11.sh").read_text()
    assert "-ffp-contract=off" in cpu and "-fno-fast-math" in cpu
    assert "first[row] != output[row]" in (chain.CONTEXT / "common.h").read_text()
    assert max(len(s.encode()) for s in chain.artifact_files().values()) < 65536
    assert json.loads((chain.CONTEXT / "numeric_contract.json").read_text()) == chain.CONTRACT
