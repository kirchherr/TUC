import copy
import json
import subprocess
from fractions import Fraction

import pytest

from examples import bounded_native_fanout as fanout
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from examples.bounded_reduction_c11 import load_observation
from tuc.ir.modules import IRStage
from tuc.runtime import runtime_execution_readiness_report


@pytest.mark.parametrize(
    "profile,slots,steps,copy_bytes",
    [
        ("cccc", 6, 8, 0),
        ("gccc", 9, 11, 1724),
        ("gggg", 10, 12, 1328),
    ],
)
def test_fixed_fanout_plans(profile, slots, steps, copy_bytes):
    compiled, plan = fanout.compile_case(profile)
    assert len(plan.buffers) == slots
    assert len(plan.steps) == steps
    assert plan.copy_bytes == copy_bytes
    assert sum(b.bytes for b in plan.buffers) == 2648 + copy_bytes
    consumers = [
        s
        for s in plan.steps
        if s.kind == "execute" and plan.buffers[s.inputs[0]].tensor == "projection"
    ]
    assert len(consumers) == 2
    assert consumers[0].inputs == consumers[1].inputs
    copies = [
        s
        for s in plan.steps
        if s.kind == "copy" and plan.buffers[s.inputs[0]].tensor == "projection"
    ]
    assert len(copies) == (1 if profile == "gccc" else 0)
    if copies:
        assert consumers[0].inputs == copies[0].outputs
        assert (
            len(
                [e for e in compiled.partition_plan.transfer_edges if e.tensor_name == "projection"]
            )
            == 2
        )
    assert [plan.buffers[s.inputs[0]].tensor for s in plan.steps if s.kind == "publish_output"] == [
        "row_raw",
        "row_positive",
    ]
    with pytest.raises(ValueError, match="no trusted executor contract"):
        runtime_execution_readiness_report(compiled.hac_ir.graph, compiled.partition_plan)


def test_source_and_hac_ir_are_shared_but_distinct_from_previous_chain():
    source = fanout.parse_source()
    assert fanout._digest_payload(source) == fanout.INTENT_DIGEST
    assert len(source["returns"]) == 2
    assert len({fanout.compile_case(p)[0].dump(IRStage.HAC_IR) for p in fanout.PROFILES}) == 1
    assert fanout.INTENT_DIGEST != fanout.CHAIN.INTENT_DIGEST
    assert source["operations"][1]["inputs"] == source["operations"][2]["inputs"]


@pytest.mark.parametrize("change", ["consumer", "output", "shape", "order", "operation", "returns"])
def test_source_changes_fail_closed(change):
    value = copy.deepcopy(fanout.parse_source())
    if change == "consumer":
        value["operations"][2]["inputs"] = ["activated"]
    elif change == "output":
        value["operations"][3]["outputs"] = ["row_raw"]
    elif change == "shape":
        value["tensors"][0]["shape"][0] += 1
    elif change == "order":
        value["operations"].reverse()
    elif change == "operation":
        value["operations"].pop()
    else:
        value["returns"].pop()
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.checked_intent(value)


def test_both_numeric_branches_and_unchanged_primitives():
    files = fanout.numeric_files()
    plan = json.loads(files["emission_plan.json"])
    assert plan["expected_rounded_outputs"] == 554
    assert plan["scalar_checks"] == 726
    assert plan["output_names"] == ["row_raw", "row_positive"]
    for name in ("generated.c", "generated.h", "kernels.cuh"):
        assert files[name].encode() == (fanout.previous.CONTEXT / name).read_bytes()
    case = fanout.CHAIN.corpus()[0]
    raw = fanout.FP.reference(case["a"], case["b"])
    positive = fanout.CHAIN.reference(case)
    for (r, budget), (p, other_budget) in zip(raw, positive, strict=True):
        assert budget == other_budget
        assert abs(r - p) > budget
    for actual, (exact, budget) in zip(fanout.FP.ordered_reference(case), raw, strict=True):
        assert abs(Fraction(actual) - exact) <= budget


@pytest.mark.parametrize(
    "profile", [None, True, [], {}, "", "ccc", "gccc-extra", "cccg", "../cccc"]
)
def test_unknown_profiles_reject(profile):
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.compile_case(profile)


@pytest.mark.parametrize(
    "field",
    ["residency", "profile", "overrides", "hac_ir", "partition", "copy_bytes", "latency_ns"],
)
def test_modified_plan_rejected(field):
    value = fanout.snapshot("gccc")
    value[field] = "modified"
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.lower(value, "gccc")


@pytest.mark.parametrize(
    "value", [{"x": [0] * 513}, {"x": "x" * 16385}, {"x": 2**64}, {"x": float("nan")}]
)
def test_metadata_limits_before_compilation(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded data reached compiler")

    monkeypatch.setattr(fanout, "snapshot", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.lower(value, "cccc")


@pytest.mark.parametrize("profile", fanout.PROFILES)
def test_required_copy_consumer_and_publication_counts(profile):
    value = fanout.expected_observation(profile, "matrix")
    assert value["numeric_observation"]["scalar_checks"] == 726
    assert value["residency"]["shared_consumer_calls"] == 22
    assert value["residency"]["published_outputs"] == 22
    assert value["residency"]["projection_copy_calls"] == (11 if profile == "gccc" else 0)
    for field in ("projection_copy_calls", "shared_consumer_calls", "published_outputs"):
        wrong = copy.deepcopy(value)
        wrong["residency"][field] += 1
        with pytest.raises(BoundedCompilerEmissionError):
            fanout.validate_observation(wrong, profile, "matrix")


@pytest.mark.parametrize("profile", fanout.PROFILES)
def test_shared_availability_and_both_publications_required(profile):
    invalid = fanout.expected_observation(profile, "matrix", mutation="invalidate-shared")
    assert invalid["residency"]["shared_consumer_calls"] == 1
    assert invalid["numeric_observation"]["generated_function_calls"] == 2
    assert invalid["residency"]["published_outputs"] == 0
    skipped = fanout.expected_observation(profile, "matrix", mutation="skip-second-publish")
    assert skipped["residency"]["published_outputs"] == 1
    assert skipped["numeric_observation"]["generated_function_calls"] == 4
    clobbered = fanout.expected_observation(profile, "matrix", mutation="clobber-shared")
    assert clobbered["numeric_observation"]["reason_code"] == "numeric_contract_mismatch"
    for value in (invalid, skipped, clobbered):
        with pytest.raises(BoundedCompilerEmissionError):
            fanout.validate_observation(value, profile, "matrix")


@pytest.mark.parametrize("mutation", fanout.STATIC_FAULTS)
def test_static_schedule_rejections_precede_calls_and_allocation(mutation):
    value = fanout.expected_observation("gccc", "matrix", mutation=mutation)
    assert value["numeric_observation"]["tensor_bytes"] == 0
    assert not any(value["residency"].values())


@pytest.mark.parametrize(
    "preflight,mutation",
    [(0, None), (1, None), ("true", None), (False, []), (True, "skip-publish")],
)
def test_modes_are_not_coerced(preflight, mutation):
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.validate_observation({}, "cccc", "c11", preflight, mutation)


def test_pure_verifier_and_operator_boundary(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier started a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert fanout.verify_artifacts()["status"] == "PASS"
    operator = (fanout.CONTEXT / "operator.sh").read_text()
    for flag in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--pids-limit=32",
        "--security-opt=no-new-privileges:true",
        "--memory=1g",
        "timeout 30s",
    ):
        assert flag in operator
    assert "--privileged" not in operator
    assert '"$image_id" /opt/tuc/proof "$profile"' in operator
    for path in fanout.CONTEXT.iterdir():
        assert path.stat().st_size <= 65536


def test_missing_duplicate_reordered_and_substituted_profiles_rejected():
    values = [fanout.expected_observation(p, "matrix") for p in fanout.PROFILES]
    for wrong in (
        values[:-1],
        list(reversed(values)),
        [values[0]] * 3,
        [fanout.expected_observation("cccc", "c11"), *values[1:]],
    ):
        with pytest.raises(BoundedCompilerEmissionError):
            fanout.build_record(wrong, "matrix", "sha256:" + "a" * 64)


@pytest.mark.parametrize("profile", fanout.PROFILES)
def test_preflight_is_never_execution(profile):
    value = fanout.expected_observation(profile, "matrix", True)
    assert not any(value["residency"].values())
    assert value["numeric_observation"]["scalar_checks"] == 0
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.validate_observation(value, profile, "matrix")


def test_missing_projection_copy_stops_before_either_consumer():
    value = fanout.expected_observation("gccc", "matrix", mutation="skip-transfer")
    assert value["residency"]["gpu_calls"] == 1
    assert value["residency"]["cpu_calls"] == 0
    assert value["residency"]["projection_copy_calls"] == 0
    assert value["residency"]["shared_consumer_calls"] == 0
    assert value["residency"]["published_outputs"] == 0


@pytest.mark.parametrize("worker", (None, [], True, "cuda", "unknown"))
def test_worker_scope_is_closed(worker):
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.profiles_for(worker)


def test_three_operation_observation_cannot_be_relabelled():
    value = fanout.expected_observation("cccc", "matrix")
    value["numeric_observation"]["schema_version"] = "tuc.bounded_placement_numeric.v0"
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.validate_observation(value, "cccc", "matrix")


def observed(name):
    return load_observation(fanout.ROOT / "tests/golden/proofs" / f"native_fanout_{name}.json")


def test_observed_fanout_and_native_sanitizers():
    cpu, matrix = observed("c11_record"), observed("matrix_record")
    assert fanout.compare_records(cpu, matrix) == observed("comparison")
    assert cpu["observations"][0] == observed("c11_sanitized")
    assert observed("c11_contract_sanitized") == {
        "schema_version": "tuc.fanout_contract_sanitizer.v0",
        "status": "PASS",
        "profiles_checked": 3,
        "invalid_selectors": 4,
        "bitflip_rejections": 8736,
    }
    shared = matrix["observations"][1]
    assert shared["profile"] == "gccc"
    assert shared["residency"]["projection_copy_calls"] == 11
    assert shared["residency"]["shared_consumer_calls"] == 22
    assert shared["residency"]["published_outputs"] == 22
    assert shared["residency"]["download_bytes"] == 7260
    assert sum(o["numeric_observation"]["scalar_checks"] for o in matrix["observations"]) == 2178
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.compare_records(cpu, {**matrix, "program_files_digest": "modified"})


@pytest.mark.parametrize("worker", ("c11", "matrix"))
def test_observed_preflight_and_invalid_selector_rejections(worker):
    values = observed(f"{worker}_preflights")
    assert list(values) == list(fanout.profiles_for(worker))
    for profile, value in values.items():
        fanout.validate_observation(value, profile, worker, True)
        with pytest.raises(BoundedCompilerEmissionError):
            fanout.validate_observation(value, profile, worker)
    invalid = observed(f"{worker}_unknown_profile")
    fanout.validate_observation(invalid, "cccc", worker, mutation="unknown-profile")
    with pytest.raises(BoundedCompilerEmissionError):
        fanout.validate_observation(invalid, "cccc", worker)


@pytest.mark.parametrize(
    "worker,profile",
    [(worker, profile) for worker in ("c11", "matrix") for profile in fanout.profiles_for(worker)],
)
def test_all_observed_fault_controls(worker, profile):
    mutations = (*fanout.MUTATIONS, *(("skip-transfer",) if profile != "cccc" else ()))
    seen = set()
    for group in (1, 2, 3):
        values = observed(f"{worker}_{profile}_controls_{group}")
        assert set(values) == set(mutations[(group - 1) * 8 : group * 8])
        assert not seen.intersection(values)
        seen.update(values)
        for mutation, value in values.items():
            fanout.validate_observation(value, profile, worker, mutation=mutation)
            with pytest.raises(BoundedCompilerEmissionError):
                fanout.validate_observation(value, profile, worker)
    assert seen == set(mutations)
