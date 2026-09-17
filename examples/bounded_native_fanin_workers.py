"""Pure artifact and observation checks for the fixed RFC 0318 fan-in workers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path

from examples import bounded_native_fanin as candidate
from examples import bounded_native_fanout as fanout
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_plan_native_bridge import _bounded_metadata, _replace_once
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation

CONTEXT = ROOT / "docker/native-fanin"
PROFILES = candidate.PROFILES
STATIC_FAULTS = (
    "schedule-count",
    "schedule-slot",
    "schedule-space",
    "schedule-order",
    "schedule-size",
    "schedule-duplicate",
    "schedule-placement",
    "schedule-join-left",
    "schedule-join-right",
    "schedule-join-swap",
)
NUMERIC_FAULTS = (
    "bypass-left",
    "bypass-right",
    "bypass-both",
    "missing-join",
    "incomplete-left",
    "incomplete-right",
    "over-budget",
    "nonfinite",
)
RUNTIME_FAULTS = (
    "skip-left",
    "skip-right",
    "invalidate-left",
    "invalidate-right",
    "clobber-left",
    "clobber-right",
    "skip-publish",
)
MUTATIONS = (*STATIC_FAULTS, *NUMERIC_FAULTS, *RUNTIME_FAULTS)
MANUAL_FILES = (
    "contract.h",
    "worker.h",
    "host.c",
    "device.cu",
    "operator.sh",
    "build-c11.sh",
    "build-cuda.sh",
    "Dockerfile",
)
ORDER = ["relu_left", "relu_right", "matmul", "sum_axis1"]


def emit(payload):
    candidate.checked_intent(payload)
    fp = candidate.fp
    files = fp.shapes.emit(fp.shapes.parse_source("odd"), "odd")
    for side, size in (("left", 231), ("right", 35)):
        macro = side.upper()
        body = f"""#ifdef TUC_INCOMPLETE_{macro}
    if (index == {size - 1}U) return;
#endif
    const float value = input[index];
#if defined(TUC_BYPASS_{macro}) || defined(TUC_BYPASS_BOTH)
    output[index] = value;
#else
    output[index] = value < 0.0F ? 0.0F : value;
#endif
"""
        files["generated.h"] = _replace_once(
            files["generated.h"],
            "#endif",
            f"void tuc_relu_{side}(const float *input, float *output);\n#endif",
        )
        files["generated.c"] += (
            f"\nvoid tuc_relu_{side}(const float *input, float *output) {{\n"
            f"  for (size_t index = 0; index < {size}U; ++index) {{\n" + body + "  }\n}\n"
        )
        gpu = (
            f"\n__global__ void tuc_relu_{side}(const float *input, float *output) {{\n"
            "  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;\n"
            f"  if (index < {size}U) {{\n" + body + "  }\n}\n"
        )
        # The header guard is the final endif; producer fault guards precede it.
        if not files["kernels.cuh"].endswith("#endif\n"):
            raise BoundedCompilerEmissionError("fan-in primitive header rejected")
        files["kernels.cuh"] = files["kernels.cuh"].removesuffix("#endif\n") + gpu + "#endif\n"
    for name, destination, indent in (
        ("generated.c", "row * 5U + column", "      "),
        ("kernels.cuh", "index", "    "),
    ):
        statement = f"{indent}projection[{destination}] = value;"
        files[name] = _replace_once(
            files[name],
            statement,
            f"#ifdef TUC_MISSING_JOIN\n{indent}value = 0.0F;\n#endif\n" + statement,
        )
    return files


def lower(value, profile):
    candidate.validate_snapshot(value, profile)
    compiled, plan = candidate.compile_case(profile)
    tensors = {n: i for i, n in enumerate(("a", "b", "left", "right", "projection", "row_sum"))}
    ops = {op.name: i for i, op in enumerate(compiled.hac_ir.graph.operations, 1)}
    lines = [f"static const struct tuc_buffer buffers_{profile}[] = {{"]
    for b in plan.buffers:
        lines.append(f"  {{{tensors[b.tensor]}U, {int(b.space.name != 'host')}U, {b.bytes}U}},")
    lines += ["};", f"static const struct tuc_event events_{profile}[] = {{"]
    for s in plan.steps:
        kind = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}[s.kind]
        a, b = (*s.inputs, 255, 255)[:2]
        out = s.outputs[0] if s.outputs else 255
        lines.append(
            f"  {{{kind}U, {ops.get(s.operation, 0)}U, "
            f"{int(s.backend == 'bounded-cuda')}U, {a}U, {b}U, {out}U}},"
        )
    return "\n".join([*lines, "};", ""])


def artifact_files():
    payload = candidate.parse_source()
    files = emit(payload)
    fp, cases = candidate.fp, candidate.corpus()
    summary = candidate.numeric_summary()
    refs = [candidate.reference(c) for c in cases]
    ordered = [candidate.ordered_reference(c) for c in cases]
    emission = {
        "schema_version": "tuc.bounded_fanin_emission.v0",
        "source_module_digest": _digest_text(candidate.SOURCE),
        "source_intent_digest": candidate.INTENT_DIGEST,
        "c11_code_digest": _digest_text(files["generated.c"]),
        "cuda_code_digest": _digest_text(files["kernels.cuh"]),
        "contract_digest": summary["contract_digest"],
        "corpus_digest": summary["corpus_digest"],
        "ordered_oracle_digest": summary["ordered_oracle_digest"],
        "expected_rounded_outputs": summary["ordered_oracle_rounding_witnesses"],
        "operation_order": ORDER,
        "output_names": ["row_sum"],
        "output_shapes": [[33]],
        "case_count": 10,
        "runs": 11,
        "scalar_checks_per_profile": 363,
        "native_execution_observed": False,
        "normal_runtime_admission": False,
    }
    inputs = ["#ifndef TUC_FANIN_INPUTS_H", "#define TUC_FANIN_INPUTS_H"]
    for name, value in (("ROWS", 33), ("OUTPUT_VALUES", 33), ("CASES", 10), ("RUNS", 11)):
        inputs.append(f"#define TUC_{name} {value}U")
    for macro, key in (
        ("INTENT", "source_intent_digest"),
        ("C11_CODE", "c11_code_digest"),
        ("CORPUS", "corpus_digest"),
        ("CONTRACT", "contract_digest"),
    ):
        inputs.append(f'#define TUC_{macro}_DIGEST "{emission[key]}"')
    for key, width in (("a", 231), ("b", 35)):
        inputs.append(f"static const float TUC_{key.upper()}[10][{width}] = {{")
        for case in cases:
            inputs.append(
                "  {" + ", ".join(fp._hex(x) + "F" for row in case[key] for x in row) + "},"
            )
        inputs.append("};")
    files["inputs.h"] = "\n".join([*inputs, "#endif", ""])
    oracle = ["#ifndef TUC_FANIN_ORACLE_H", "#define TUC_FANIN_ORACLE_H"]
    for name in ("LOWER", "UPPER", "REFERENCE64", "ORDERED"):
        oracle.append(f"static const double TUC_{name}[10][33] = {{")
        for i, bounds in enumerate(refs):
            values = (
                ordered[i]
                if name == "ORDERED"
                else [
                    float(x) if name == "REFERENCE64" else fp.interval(x, e)[name == "UPPER"]
                    for x, e in bounds
                ]
            )
            oracle.append("  {" + ", ".join(map(fp._hex, values)) + "},")
        oracle.append("};")
    files["oracle.h"] = "\n".join([*oracle, "#endif", ""])
    values = {
        "source_intent": payload,
        "numeric_contract": candidate.CONTRACT,
        "emission_plan": emission,
        **{f"{p}_plan": candidate.snapshot(p) for p in PROFILES},
    }
    files.update(
        {n + ".json": json.dumps(v, indent=2, sort_keys=True) + "\n" for n, v in values.items()}
    )
    tables, rows = [], []
    for profile in PROFILES:
        value = values[f"{profile}_plan"]
        tables.append(lower(value, profile))
        plan = value["residency"]
        mask = int(profile.replace("c", "0").replace("g", "1"), 2)
        rows.append(
            f'  {{"{profile}", "{_digest_payload(value)}", {mask}U, '
            f"{len(plan['buffers'])}U, {len(plan['steps'])}U, "
            f"{value['planned_buffer_bytes']}U, buffers_{profile}, events_{profile}}},"
        )
    code = _digest_payload({t: emission[f"{t}_code_digest"] for t in ("c11", "cuda")})
    files["plans.h"] = "\n".join(
        [
            "#ifndef TUC_FANIN_PLANS_H",
            "#define TUC_FANIN_PLANS_H",
            f'#define TUC_MATRIX_CODE_DIGEST "{code}"',
            *tables,
            "static const struct tuc_profile profiles[] = {",
            *rows,
            "};",
            "#endif",
            "",
        ]
    )
    # Reuse the unchanged security/numeric harness with explicit output-schema changes.
    common = _read_bounded_file(fanout.CONTEXT / "common.h").decode()
    common = _replace_once(common, "tuc.bounded_fanout_numeric.v0", "tuc.bounded_fanin_numeric.v0")
    common = _replace_once(
        common,
        r"\"operation_order\":[\"matmul\",\"relu\",\"raw_sum_axis1\",\"positive_sum_axis1\"]",
        r"\"operation_order\":[\"relu_left\",\"relu_right\",\"matmul\",\"sum_axis1\"]",
    )
    common = _replace_once(
        common,
        r"\"output_names\":[\"row_raw\",\"row_positive\"],\"output_shapes\":[[33],[33]]",
        r"\"output_names\":[\"row_sum\"],\"output_shapes\":[[33]]",
    )
    files["common.h"] = common
    contract_test = _read_bounded_file(fanout.CONTEXT / "contract_test.c").decode()
    contract_test = _replace_once(contract_test, "p < 3U", "p < 6U")
    contract_test = _replace_once(
        contract_test, r"\"profiles_checked\":3", r"\"profiles_checked\":6"
    )
    files["contract_test.c"] = _replace_once(
        contract_test, "tuc.fanout_contract_sanitizer.v0", "tuc.fanin_contract_sanitizer.v0"
    )
    faults = [
        "# Fixed compile-time controls; never external source or runtime opcodes.",
        "compile /out/bin/proof",
    ]
    faults += [
        f"compile /out/bin/{n} -DTUC_SCHEDULE_FAULT={i}" for i, n in enumerate(STATIC_FAULTS, 1)
    ]
    faults += [
        f"compile /out/bin/{n} -DTUC_{n.upper().replace('-', '_')}=1"
        for n in (*NUMERIC_FAULTS, *RUNTIME_FAULTS, "skip-left-copy", "skip-right-copy")
    ]
    files["faults.sh"] = "\n".join([*faults, ""])
    files["Dockerfile.dockerignore"] = "**\n!docker/\n!docker/native-fanin/\n" + "".join(
        f"!docker/native-fanin/{n}\n"
        for n in (*files, *MANUAL_FILES)
        if not n.endswith(".json") and n != "operator.sh"
    )
    return files


def verify_artifacts():
    candidate.verify_artifacts()
    for name, value in artifact_files().items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("fan-in worker artifact drift")
    return {
        "schema_version": "tuc.bounded_fanin_verification.v0",
        "status": "PASS",
        "profiles": list(PROFILES),
        "native_execution_observed": False,
        "normal_runtime_admission": False,
    }


def program_digest():
    paths = [CONTEXT / n for n in (*artifact_files(), *MANUAL_FILES)]
    paths += [
        ROOT / n
        for n in (
            "examples/bounded_native_fanin_workers.py",
            "examples/bounded_native_fanin.py",
            "src/tuc/runtime/residency.py",
            "src/tuc/runtime/overrides.py",
        )
    ]
    return _digest_payload(
        {
            p.relative_to(ROOT).as_posix(): "sha256:" + sha256(_read_bounded_file(p)).hexdigest()
            for p in paths
        }
    )


def profiles_for(worker):
    if type(worker) is not str or worker not in ("c11", "matrix"):
        raise BoundedCompilerEmissionError("fan-in worker rejected")
    return ("cccc",) if worker == "c11" else PROFILES


def mutations_for(profile):
    candidate.compile_case(profile)
    copies = (() if profile not in ("gccc", "cggg") else ("skip-left-copy",)) + (
        () if profile not in ("cgcc", "gcgg") else ("skip-right-copy",)
    )
    return (*MUTATIONS, *copies)


def counts(plan, steps, repeats):
    result = fanout.previous.counts(plan, steps, repeats)
    result.update(
        {
            k: 0
            for k in (
                "left_producer_calls",
                "right_producer_calls",
                "join_calls",
                "left_copy_calls",
                "right_copy_calls",
                "published_outputs",
            )
        }
    )
    for s in steps:
        tensor = plan.buffers[s.outputs[0]].tensor if s.outputs else None
        if s.kind == "execute":
            key = {
                "left": "left_producer_calls",
                "right": "right_producer_calls",
                "projection": "join_calls",
            }.get(tensor)
            if key:
                result[key] += repeats
        if s.kind == "copy" and tensor in ("left", "right"):
            result[f"{tensor}_copy_calls"] += repeats
        if s.kind == "publish_output":
            result["published_outputs"] += repeats
    return result


def expected_observation(profile, worker, preflight=False, mutation=None):
    if (
        type(profile) is not str
        or profile not in profiles_for(worker)
        or type(preflight) is not bool
    ):
        raise BoundedCompilerEmissionError("fan-in mode rejected")
    if mutation is not None and (
        type(mutation) is not str
        or mutation not in (*mutations_for(profile), "unknown-profile")
        or preflight
        or (mutation == "unknown-profile" and profile != "cccc")
    ):
        raise BoundedCompilerEmissionError("fan-in mutation rejected")
    _, plan = candidate.compile_case(profile)
    emission = json.loads(artifact_files()["emission_plan.json"])
    code = (
        emission["c11_code_digest"]
        if worker == "c11"
        else _digest_payload({t: emission[f"{t}_code_digest"] for t in ("c11", "cuda")})
    )
    numeric = {
        "schema_version": "tuc.bounded_fanin_numeric.v0",
        "target": profile,
        "mode": "preflight" if preflight else "execute",
        "status": "PASS",
        "reason_code": "none",
        **{
            k: emission[k]
            for k in (
                "source_intent_digest",
                "corpus_digest",
                "contract_digest",
                "operation_order",
                "output_names",
                "output_shapes",
            )
        },
        "code_digest": code,
        "output_values": 33,
        "case_count": 10,
        "cases_passed": 0 if preflight else 11,
        "failed_run_index": -1,
        "generated_function_calls": 0 if preflight else 44,
        "scalar_checks": 0 if preflight else 363,
        "tensor_bytes": 0 if preflight else sum(b.bytes for b in plan.buffers),
        "outputs_differing_from_reference64": 0
        if preflight
        else emission["expected_rounded_outputs"],
        "security_boundary_passed": True,
        "numeric_contract_passed": not preflight,
        "execution_policy_passed": not preflight,
        "repeated_baseline_passed": not preflight,
        "raw_values_serialized": False,
    }
    counter = counts(plan, plan.steps, 0 if preflight else 11)
    if mutation:
        numeric.update(
            status="ERROR",
            cases_passed=0,
            failed_run_index=0,
            scalar_checks=0,
            outputs_differing_from_reference64=0,
            numeric_contract_passed=False,
            execution_policy_passed=False,
            repeated_baseline_passed=False,
        )
        if mutation in STATIC_FAULTS or mutation == "unknown-profile":
            counter = counts(plan, (), 0)
            numeric.update(
                reason_code="target_not_ready",
                generated_function_calls=0,
                tensor_bytes=0,
                failed_run_index=-1,
            )
            if mutation == "unknown-profile":
                numeric.update(
                    reason_code="invalid_invocation", mode="invalid", security_boundary_passed=False
                )
        else:
            steps = plan.steps
            stop = None
            for i, step in enumerate(steps):
                tensor = plan.buffers[step.outputs[0]].tensor if step.outputs else None
                if (
                    (mutation == "skip-publish" and step.kind == "publish_output")
                    or (
                        step.kind == "execute"
                        and (
                            mutation == f"skip-{tensor}"
                            or (
                                tensor == "projection"
                                and mutation in ("invalidate-left", "invalidate-right")
                            )
                        )
                    )
                    or (step.kind == "copy" and mutation == f"skip-{tensor}-copy")
                ):
                    stop = i
                    break
            counter = counts(plan, steps if stop is None else steps[:stop], 1)
            numeric.update(
                reason_code="numeric_contract_mismatch" if stop is None else "execution_failed",
                generated_function_calls=counter["cpu_calls"] + counter["gpu_calls"],
            )
    return {
        "schema_version": "tuc.bounded_fanin_observation.v0",
        "worker": worker,
        "profile": profile,
        "plan_digest": _digest_payload(candidate.snapshot(profile)),
        "residency": counter,
        "numeric_observation": numeric,
    }


def validate_observation(value, profile, worker, preflight=False, mutation=None):
    _bounded_metadata(value)
    expected = expected_observation(profile, worker, preflight, mutation)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("fan-in observation rejected")
    return expected


def sanitizer_observation():
    probes = sum(
        32 * (4 + 3 * len(p.buffers) + 6 * len(p.steps))
        for _, p in (candidate.compile_case(n) for n in PROFILES)
    )
    return {
        "schema_version": "tuc.fanin_contract_sanitizer.v0",
        "status": "PASS",
        "profiles_checked": 6,
        "invalid_selectors": 4,
        "bitflip_rejections": probes,
    }


def build_record(observations, worker, image_id):
    _bounded_metadata(observations)
    profiles = profiles_for(worker)
    if type(observations) is not list or len(observations) != len(profiles):
        raise BoundedCompilerEmissionError("fan-in coverage rejected")
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("fan-in image rejected")
    for profile, value in zip(profiles, observations, strict=True):
        validate_observation(value, profile, worker)
    verify_artifacts()
    return {
        "schema_version": "tuc.bounded_fanin_record.v0",
        "worker": worker,
        "observations": observations,
        "operator_image_id": image_id,
        "program_files_digest": program_digest(),
        "provenance": "same_maintainer_operator",
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
    }


def accept_directory(directory, worker, image_id):
    observations = []
    for profile in profiles_for(worker):
        validate_observation(
            load_observation(directory / f"{profile}-preflight.json"), profile, worker, True
        )
        observations.append(load_observation(directory / f"{profile}-execution.json"))
        for mutation in mutations_for(profile):
            validate_observation(
                load_observation(directory / f"{profile}-{mutation}.json"),
                profile,
                worker,
                mutation=mutation,
            )
    validate_observation(
        load_observation(directory / "unknown-profile.json"),
        "cccc",
        worker,
        mutation="unknown-profile",
    )
    if worker == "c11":
        validate_observation(load_observation(directory / "sanitized.json"), "cccc", worker)
        if _canonical_json(
            load_observation(directory / "contract-sanitized.json")
        ) != _canonical_json(sanitizer_observation()):
            raise BoundedCompilerEmissionError("fan-in sanitizer rejected")
    return build_record(observations, worker, image_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("c11", "matrix"))
    parser.add_argument("--accept", type=Path)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    try:
        if args.accept and args.worker and args.image_id:
            report = accept_directory(args.accept, args.worker, args.image_id)
        elif not any((args.worker, args.accept, args.image_id)):
            report = verify_artifacts()
        else:
            raise BoundedCompilerEmissionError("fan-in invocation rejected")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print("bounded fan-in worker verification rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
