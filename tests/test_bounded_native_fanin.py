import copy
import json
import subprocess
from dataclasses import replace
from fractions import Fraction

import pytest

from examples import bounded_native_fanin as fanin
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from tuc.ir.modules import IRStage
from tuc.runtime import runtime_execution_readiness_report


def test_fixed_source_and_placement_independent_hac_ir():
    payload = fanin.parse_source()
    module = fanin.checked_intent(payload)
    assert fanin._digest_payload(payload) == fanin.INTENT_DIGEST
    assert [op.inputs for op in module.operations] == [
        ("a",),
        ("b",),
        ("left", "right"),
        ("projection",),
    ]
    assert [t.shape for t in module.tensors if t.name in ("left", "right")] == [(33, 7), (7, 5)]
    compiled = [fanin.compile_case(p)[0] for p in fanin.PROFILES]
    assert len({c.dump(IRStage.HAC_IR) for c in compiled}) == 1
    for case in compiled:
        with pytest.raises(ValueError, match="no trusted executor contract"):
            runtime_execution_readiness_report(case.hac_ir.graph, case.partition_plan)


@pytest.mark.parametrize("profile", fanin.PROFILES)
def test_profiles_keep_both_producers_at_the_join(profile):
    compiled, plan = fanin.compile_case(profile)
    value = fanin.snapshot(profile)
    join = value["join"]
    assert join["operands"] == ["left", "right"]
    assert len(set(join["operand_slots"])) == 2
    assert join["both_inputs_available_in_plan"] is True
    assert join["space"] == ("host" if profile[2] == "c" else "accelerator")
    assert [s.backend for s in plan.steps if s.kind == "execute"] == [
        "bounded-c11" if p == "c" else "bounded-cuda" for p in profile
    ]
    assert len(plan.buffers) <= 9 and len(plan.steps) <= 10
    expected = {
        "cccc": (0, 2920),
        "gccc": (1848, 4768),
        "cgcc": (280, 3200),
        "gcgg": (1196, 4116),
        "cggg": (1196, 4116),
        "gggg": (1196, 4116),
    }
    assert (value["planned_copy_bytes"], value["planned_buffer_bytes"]) == expected[profile]
    assert fanin.inspect_schedule(compiled, plan) == join
    fanin.validate_snapshot(value, profile)


@pytest.mark.parametrize(
    "profile,tensor",
    [
        ("gccc", "left"),
        ("cgcc", "right"),
        ("gcgg", "right"),
        ("cggg", "left"),
    ],
)
def test_each_remote_join_operand_needs_its_copy(profile, tensor):
    compiled, plan = fanin.compile_case(profile)
    copies = [
        s for s in plan.steps if s.kind == "copy" and plan.buffers[s.outputs[0]].tensor == tensor
    ]
    assert len(copies) == 1
    incomplete = replace(plan, steps=tuple(s for s in plan.steps if s != copies[0]))
    with pytest.raises(BoundedCompilerEmissionError, match="unavailable"):
        fanin.inspect_schedule(compiled, incomplete)


@pytest.mark.parametrize("profile", fanin.PROFILES)
@pytest.mark.parametrize(
    "fault",
    [
        "missing-left",
        "missing-right",
        "swapped",
        "raw-left",
        "raw-right",
        "early-join",
        "missing-publication",
        "duplicate-publication",
        "invalid-slot",
    ],
)
def test_bad_schedule_cannot_satisfy_join_contract(profile, fault):
    compiled, plan = fanin.compile_case(profile)
    steps = list(plan.steps)
    ops = compiled.hac_ir.graph.operations
    join_index = next(i for i, s in enumerate(steps) if s.operation == ops[2].name)
    join = steps[join_index]
    if fault.startswith("missing-") and fault != "missing-publication":
        op = ops[0 if fault == "missing-left" else 1]
        steps = [s for s in steps if s.operation != op.name]
    elif fault == "swapped":
        steps[join_index] = replace(join, inputs=tuple(reversed(join.inputs)))
    elif fault.startswith("raw-"):
        port = 0 if fault == "raw-left" else 1
        tensor = "a" if port == 0 else "b"
        raw = next(i for i, b in enumerate(plan.buffers) if b.tensor == tensor)
        inputs = list(join.inputs)
        inputs[port] = raw
        steps[join_index] = replace(join, inputs=tuple(inputs))
    elif fault == "early-join":
        steps.pop(join_index)
        steps.insert(0, join)
    elif fault == "missing-publication":
        steps.pop()
    elif fault == "duplicate-publication":
        steps.append(steps[-1])
    else:
        steps[join_index] = replace(join, inputs=(-1, join.inputs[1]))
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.inspect_schedule(compiled, replace(plan, steps=tuple(steps)))


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "source_intent_digest",
        "hac_ir",
        "hs_ir",
        "partition",
        "decisions",
        "overrides",
        "residency",
        "join",
        "planned_copy_bytes",
        "native_execution_observed",
        "normal_runtime_admission",
        "latency_ns",
    ],
)
def test_candidate_snapshot_drift_rejected(field):
    value = fanin.snapshot("gcgg")
    value[field] = "modified"
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.validate_snapshot(value, "gcgg")


@pytest.mark.parametrize(
    "field,value",
    [
        ("shape", (33, 8)),
        ("shape", (33, True)),
        ("bytes", 4),
        ("bytes", True),
        ("dtype", "float16"),
        ("tensor", "unknown"),
        ("space", "host"),
    ],
)
def test_buffer_contract_rejected(field, value):
    compiled, plan = fanin.compile_case("gccc")
    buffer = replace(plan.buffers[0], **{field: value})
    with pytest.raises(BoundedCompilerEmissionError, match="buffer"):
        fanin.inspect_schedule(compiled, replace(plan, buffers=(buffer, *plan.buffers[1:])))


@pytest.mark.parametrize("field", ["buffers", "steps"])
def test_typed_schedule_budget_rejected(field):
    compiled, plan = fanin.compile_case("gccc")
    with pytest.raises(BoundedCompilerEmissionError, match="budget"):
        fanin.inspect_schedule(compiled, replace(plan, **{field: getattr(plan, field) * 100}))


@pytest.mark.parametrize("profile", [None, True, [], {}, "", "ccc", "cccg", "../cccc"])
def test_unknown_profile_rejected(profile):
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.compile_case(profile)


@pytest.mark.parametrize("fault", ["operand", "shape", "dtype", "relu", "axis", "order"])
def test_changed_source_contract_rejected(fault):
    value = copy.deepcopy(fanin.parse_source())
    if fault == "operand":
        value["operations"][2]["inputs"] = ["a", "right"]
    elif fault == "shape":
        value["tensors"][0]["shape"][0] += 1
    elif fault == "dtype":
        value["tensors"][0]["dtype"] = "float16"
    elif fault == "relu":
        value["operations"][0]["attributes"] = {"elementwise_kind": "identity"}
    elif fault == "axis":
        value["operations"][3]["attributes"] = {"axis": 0}
    else:
        value["operations"].reverse()
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.checked_intent(value)


@pytest.mark.parametrize("value", [{"x": [0] * 513}, {"x": "x" * 16385}, {"x": float("nan")}])
def test_metadata_budget_precedes_compilation(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded metadata reached compilation")

    monkeypatch.setattr(fanin, "snapshot", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.validate_snapshot(value, "cccc")


def test_numerical_contract_and_first_case_wrong_code_witnesses():
    report = fanin.numeric_summary()
    assert report["planned_scalar_checks_per_profile"] == 363
    assert report["ordered_oracle_rounding_witnesses"] == 265
    assert set(report["first_case_fault_witnesses"].values()) == {33}
    assert len(report["first_case_fault_witnesses"]) == 6
    assert report["native_execution_observed"] is False
    for case in fanin.corpus():
        for actual, (exact, budget) in zip(
            fanin.ordered_reference(case),
            fanin.reference(case),
            strict=True,
        ):
            assert abs(Fraction(actual) - exact) <= budget
            assert budget == fanin.fp.GAMMA * exact


@pytest.mark.parametrize(
    "fault", ["nan", "infinity", "integer", "bool", "tiny", "shape", "missing"]
)
def test_unadmitted_numeric_inputs_rejected(fault):
    case = fanin.corpus()[0]
    if fault == "shape":
        case["b"].pop()
    elif fault == "missing":
        del case["a"]
    else:
        case["a"][0][0] = {
            "nan": float("nan"),
            "infinity": float("inf"),
            "integer": 1,
            "bool": True,
            "tiny": 2**-100,
        }[fault]
    with pytest.raises(BoundedCompilerEmissionError):
        fanin.reference(case)


def test_candidate_goldens_are_pure_and_do_not_admit_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("candidate verification started a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    report = fanin.verify_artifacts()
    assert report["status"] == "PASS"
    assert report["scope"] == "pure_source_plan_numeric_candidate"
    assert report["native_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    assert "native_execution" in report["blocked_claims"]
    assert len(fanin.artifact_files()) == 9
    for name, value in fanin.artifact_files().items():
        assert len(value.encode()) <= 65536
        fanin._bounded_metadata(json.loads(value))
        assert (fanin.CONTEXT / name).read_bytes() == value.encode()


def test_artifact_drift_rejected(tmp_path, monkeypatch):
    for name, value in fanin.artifact_files().items():
        (tmp_path / name).write_text(value, encoding="ascii", newline="\n")
    report = json.loads((tmp_path / "report.json").read_text())
    report["native_execution_observed"] = True
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="ascii")
    monkeypatch.setattr(fanin, "CONTEXT", tmp_path)
    with pytest.raises(BoundedCompilerEmissionError, match="drift"):
        fanin.verify_artifacts()


def test_cli_has_no_native_execution_mode(monkeypatch):
    monkeypatch.setattr("sys.argv", ["bounded_native_fanin.py", "--execute"])
    with pytest.raises(SystemExit) as error:
        fanin.main()
    assert error.value.code == 2
