"""Installed-wheel, fixed-application C11 conformance data and receipt verifier.

Default operation only constructs text and metadata. The separate reviewed
operator builds and executes containers. No Python function launches native code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import tuc
from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

ROOT = Path(__file__).resolve().parent
INPUT_CASES = 3
REPLAYS = 2
MAX_FILE_BYTES = 256 * 1024
MAX_CONTEXT_BYTES = 2 * 1024 * 1024
MAX_RECEIPT_BYTES = 4096
MAX_RECEIPT_DEPTH = 4
MAX_RECEIPT_ITEMS = 64
SCHEMA = "tuc.bounded_source_c11_observation.v0"
MUTATIONS = tuple(f"skip-operation-{i}" for i in range(7)) + (
    "corrupt-output-0", "corrupt-output-1", "missing-publication-0",
    "missing-publication-1", "swap-outputs", "poison-final-scalar",
)
SUPPORT_FILES = ("Dockerfile", "Dockerfile.dockerignore", "build.sh", "operator.sh")
PACKAGE_FILES = (
    "compiler/bounded_source.py", "compiler/pipeline.py", "compiler/lowering.py",
    "compiler/movement.py", "compiler/decisions.py", "backends/base.py",
    "backends/registry.py", "backends/bounded_dag.py", "backends/bounded_dag_codegen.py",
    "frontend/source_intent.py", "frontend/source_intent_metadata.py",
    "frontend/source_intent_returns.py", "frontend/triton_metadata.py", "frontend/hints.py",
    "ir/model.py", "ir/modules.py", "ir/dialect.py", "ir/dump.py", "ir/memory.py",
    "runtime/partitioning.py", "runtime/plan.py", "runtime/residency.py",
)
COUNTERS = ("case_runs", "function_calls", "scalar_checks", "published_outputs", "rejected_cases")
INPUT_SHAPES = (("a", (3, 2)), ("b", (2, 4)), ("c", (4, 3)), ("d", (3, 2)))


def source_module():
    return SourceIntentModule(
        "project_recombine_and_summarize",
        tuple(SourceIntentTensor(name, shape) for name, shape in (
            *INPUT_SHAPES, ("p", (3, 4)), ("q", (4, 2)), ("rp", (3, 4)),
            ("rq", (4, 2)), ("joined", (3, 2)), ("raw_rows", (3,)), ("joint_rows", (3,)),
        )),
        (
            SourceIntentOperation("left_projection", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation("right_projection", "matmul", ("c", "d"), ("q",)),
            SourceIntentOperation("left_activation", "elementwise", ("p",), ("rp",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("right_activation", "elementwise", ("q",), ("rq",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("recombine", "matmul", ("rp", "rq"), ("joined",)),
            SourceIntentOperation("left_rows", "reduction", ("p",), ("raw_rows",),
                                  attributes={"axis": 1}),
            SourceIntentOperation("joined_rows", "reduction", ("joined",), ("joint_rows",),
                                  attributes={"axis": 1}),
        ),
        returns=(SourceIntentReturn("branch_total", "raw_rows"),
                 SourceIntentReturn("joined_total", "joint_rows")),
    )


def backend_bindings():
    return (BoundedBackendBinding(BackendCapability(
        "consumer_cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                                   OperationKind.REDUCTION}),
        memory_domain=MemoryDomainKind.HOST_RAM,
    ), DAGTarget.C11),)


def compile_cpu():
    module, bindings = source_module(), backend_bindings()
    result = compile_bounded_source_intent(module, bindings)
    validate_bounded_source_compilation(module, bindings, result)
    manifest = json.loads(result.artifacts.manifest_json)
    if (len(manifest["operations"]) != 7 or len(manifest["tensors"]) != 11 or
            len(manifest["buffers"]) != 11 or len(manifest["events"]) != 13 or
            manifest["planned_buffer_bytes"] != 336 or manifest["planned_copy_bytes"] != 0 or
            any(op["target"] != "c11" for op in manifest["operations"]) or
            any(buffer["space"] != "host" for buffer in manifest["buffers"]) or
            tuple(binding.public_name for binding in result.output_bindings) !=
            ("branch_total", "joined_total")):
        raise ValueError("fixed source C11 application changed")
    return result


def _normal_or_zero(value):
    return math.isfinite(value) and (value == 0.0 or abs(value) >= 2.0 ** -126)


def _f32(value):
    rounded = struct.unpack("<f", struct.pack("<f", value))[0]
    if not _normal_or_zero(rounded):
        raise ValueError("fixed source C11 numeric domain rejected")
    return rounded


def _bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def fixed_inputs(case):
    """Exact RFC 0321 consumer corpus, independent of compiler artifacts."""
    if type(case) is not int or not 0 <= case < INPUT_CASES:
        raise ValueError("fixed source C11 input case rejected")
    result = {}
    for tensor, (name, shape) in enumerate(INPUT_SHAPES):
        values = []
        for index in range(math.prod(shape)):
            numerator = ((index * 7 + tensor * 3) % 19) - 9
            value = (numerator / 8 if case == 0 else numerator / 7 if case == 1 else
                     -0.0 if index % 3 == 0 else numerator / 16)
            values.append(_f32(value))
        result[name] = values
    return result


def reference_outputs(case):
    """Explicit application math; no manifest, event, IR or kernel inspection."""
    inputs = fixed_inputs(case)

    def product(left, right, rows, inner, columns):
        output = []
        for row in range(rows):
            for column in range(columns):
                value = 0.0
                for k in range(inner):
                    value = _f32(value + _f32(left[row * inner + k] * right[k * columns + column]))
                output.append(value)
        return output

    def row_sum(values, columns):
        output = []
        for row in range(3):
            value = 0.0
            for column in range(columns):
                value = _f32(value + values[row * columns + column])
            output.append(value)
        return output

    left = product(inputs["a"], inputs["b"], 3, 2, 4)
    right = product(inputs["c"], inputs["d"], 4, 3, 2)
    joined = product([v if v > 0 else 0.0 for v in left],
                     [v if v > 0 else 0.0 for v in right], 3, 4, 2)
    return {"branch_total": row_sum(left, 4), "joined_total": row_sum(joined, 2)}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_file(path, limit=MAX_FILE_BYTES):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("fixed source C11 bounded regular file required")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("fixed source C11 file budget exceeded")
    return data.decode("utf-8")


def _wheel_digest(required=False):
    path = ROOT / "wheel-sha256.txt"
    if not path.exists() and not path.is_symlink():
        if required:
            raise ValueError("fixed source C11 wheel binding required")
        return None
    text = _read_file(path, 80)
    digest = text.removesuffix("\r\n") if text.endswith("\r\n") else text.removesuffix("\n")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ValueError("fixed source C11 wheel binding rejected")
    return digest


def _constant(name, vectors):
    rows = ["{" + ",".join(f"UINT32_C(0x{_bits(value):08x})" for value in row) + "}"
            for row in vectors]
    return (f"static const uint32_t {name}[3][{len(vectors[0])}] = {{" +
            ",".join(rows) + "};")


_COMMON = r'''#define _POSIX_C_SOURCE 200809L
#include "generated.h"
#include <fenv.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#if !defined(__x86_64__) || !defined(__SSE2__)
#error "reviewed x86-64 SSE2 target required"
#endif
#include <xmmintrin.h>
#ifndef TUC_SOURCE_FAULT
#define TUC_SOURCE_FAULT 0
#endif
#if TUC_SOURCE_FAULT < 0 || TUC_SOURCE_FAULT > 13
#error "unknown conformance fault"
#endif
struct tuc_counts {
  size_t case_runs, function_calls, scalar_checks, published_outputs, rejected_cases;
};
static void tuc_poison(float *values, size_t count) {
  const uint32_t bits = UINT32_C(0x7fc00001);
  for (size_t i = 0; i < count; ++i) memcpy(values + i, &bits, sizeof(bits));
}
static void tuc_bind(float *output, const uint32_t *input, size_t count) {
  for (size_t i = 0; i < count; ++i) memcpy(output + i, input + i, sizeof(uint32_t));
}
static int tuc_normal(const float *values, size_t count) {
  for (size_t i = 0; i < count; ++i) {
    const int category = fpclassify(values[i]);
    if (category != FP_NORMAL && category != FP_ZERO) return 0;
  }
  return 1;
}
static void tuc_corrupt(float *value) {
  uint32_t bits;
  memcpy(&bits, value, sizeof(bits));
  bits ^= UINT32_C(1);
  memcpy(value, &bits, sizeof(bits));
}
static int tuc_check(const float *actual, const uint32_t *expected, size_t count,
                     struct tuc_counts *counts) {
  for (size_t i = 0; i < count; ++i) {
    uint32_t bits;
    memcpy(&bits, actual + i, sizeof(bits));
    if (!tuc_normal(actual + i, 1U)) return 0;
    if (bits != expected[i] && !((bits & UINT32_C(0x7fffffff)) == 0U &&
                                (expected[i] & UINT32_C(0x7fffffff)) == 0U)) return 0;
    ++counts->scalar_checks;
  }
  return 1;
}
'''


def _worker(compilation, manifest, binding_digest):
    buffers, tensors = manifest["buffers"], manifest["tensors"]
    public = {binding.tensor_index: binding.public_name for binding in compilation.output_bindings}
    expected = [reference_outputs(case) for case in range(INPUT_CASES)]
    inputs = [fixed_inputs(case) for case in range(INPUT_CASES)]
    terminal_slots = [event["inputs"][0] for event in manifest["events"]
                      if event["kind"] == "publish_output"]
    if len(terminal_slots) != 2 or any(buffers[slot]["bytes"] != 12 for slot in terminal_slots):
        raise ValueError("fixed source C11 publication boundary rejected")
    lines = [_COMMON, f'#define TUC_SOURCE_BINDING "{binding_digest}"']
    for tensor in manifest["input_tensors"]:
        name = tensors[tensor]["name"]
        lines.append(_constant(f"input_{tensor}", [values[name] for values in inputs]))
    for tensor in manifest["output_tensors"]:
        vectors = [values[public[tensor]] for values in expected]
        lines.append(_constant(f"expected_{tensor}", vectors))
    lines.append("static int tuc_run(size_t vector, struct tuc_counts *counts) {")
    for buffer in buffers:
        lines.append(f"  float slot_{buffer['index']}[{buffer['bytes'] // 4}];")
    lines += [f"  unsigned char ready[{len(buffers)}] = {{0}};", "  size_t publications = 0U;"]
    for buffer in buffers:
        lines.append(f"  tuc_poison(slot_{buffer['index']}, {buffer['bytes'] // 4}U);")
    publication = 0
    for event in manifest["events"]:
        kind = event["kind"]
        if kind == "bind_input":
            slot = event["outputs"][0]
            tensor = buffers[slot]["tensor"]
            count = buffers[slot]["bytes"] // 4
            lines += [f"  if (ready[{slot}]) return 4;",
                      f"  tuc_bind(slot_{slot}, input_{tensor}[vector], {count}U);",
                      f"  if (!tuc_normal(slot_{slot}, {count}U)) return 4;",
                      f"  ready[{slot}] = 1U;"]
        elif kind == "execute":
            op, output = event["operation"], event["outputs"][0]
            checks = " || ".join(f"!ready[{slot}]" for slot in event["inputs"])
            args = ", ".join(f"slot_{slot}" for slot in (*event["inputs"], output))
            lines += [f"  if ({checks}) return 1;", f"  if (ready[{output}]) return 4;",
                      f"  if (TUC_SOURCE_FAULT != {op + 1}) {{",
                      f"    tuc_dag_op_{op}({args});", "    ++counts->function_calls;",
                      f"    if (!tuc_normal(slot_{output}, "
                      f"{buffers[output]['bytes'] // 4}U)) return 4;",
                      f"    ready[{output}] = 1U;", "  }"]
        elif kind == "publish_output":
            slot = event["inputs"][0]
            tensor, count = buffers[slot]["tensor"], buffers[slot]["bytes"] // 4
            other = terminal_slots[1 - publication]
            lines += [f"  if (!ready[{slot}]) return 1;",
                      f"  if (TUC_SOURCE_FAULT != {publication + 10}) {{",
                      f"    if (TUC_SOURCE_FAULT == {publication + 8}) tuc_corrupt(slot_{slot});"]
            if publication == 0:
                lines.append(f"    if (TUC_SOURCE_FAULT == 13) "
                             f"tuc_poison(slot_{slot} + {count - 1}U, 1U);")
            lines += [f"    if (TUC_SOURCE_FAULT == 12 && !ready[{other}]) return 1;",
                      f"    if (!tuc_check(TUC_SOURCE_FAULT == 12 ? slot_{other} : slot_{slot},",
                      f"                   expected_{tensor}[vector], {count}U, counts)) return 2;",
                      "    ++publications;", "    ++counts->published_outputs;", "  }"]
            publication += 1
        else:
            raise ValueError("fixed source C11 schedule event rejected")
    lines += ["  return publications == 2U ? 0 : 3;", "}", _main()]
    return "\n".join(lines)


def _main():
    return r'''
static void tuc_receipt(const char *status, const char *reason, const struct tuc_counts *counts) {
  printf("{\"schema_version\":\"tuc.bounded_source_c11_observation.v0\","
         "\"status\":\"%s\",\"reason\":\"%s\",\"binding_digest\":\"%s\",\"fault\":%d,"
         "\"case_runs\":%zu,\"function_calls\":%zu,\"scalar_checks\":%zu,"
         "\"published_outputs\":%zu,\"rejected_cases\":%zu}\n",
         status, reason, TUC_SOURCE_BINDING, TUC_SOURCE_FAULT,
         counts->case_runs, counts->function_calls,
         counts->scalar_checks, counts->published_outputs, counts->rejected_cases);
}
int main(int argc, char **argv) {
  (void)argv;
  struct tuc_counts counts = {0, 0, 0, 0, 0};
  if (argc != 1) { tuc_receipt("ERROR", "invalid_invocation", &counts); return 2; }
  (void)alarm(20U);
  if (fegetround() != FE_TONEAREST || (_mm_getcsr() & UINT32_C(0xe040)) != 0U ||
      getuid() != 10001U || geteuid() != 10001U || getgid() != 10001U || getegid() != 10001U) {
    tuc_receipt("ERROR", "environment_error", &counts); return 2;
  }
  const int expected_failure = (TUC_SOURCE_FAULT >= 1 && TUC_SOURCE_FAULT <= 7) ? 1 :
                              (TUC_SOURCE_FAULT == 10 || TUC_SOURCE_FAULT == 11) ? 3 : 2;
  const char *const reasons[] = {"none", "missing_operand", "numeric_mismatch",
                                "missing_publication", "execution_error"};
  for (size_t vector = 0; vector < 3U; ++vector) {
    for (size_t replay = 0; replay < 2U; ++replay) {
      const int result = tuc_run(vector, &counts);
      if (TUC_SOURCE_FAULT == 0 && result == 0) { ++counts.case_runs; continue; }
      if (TUC_SOURCE_FAULT != 0 && result == expected_failure) {
        ++counts.rejected_cases; continue;
      }
      tuc_receipt("ERROR", "execution_error", &counts); return 2;
    }
  }
  tuc_receipt(TUC_SOURCE_FAULT == 0 ? "PASS" : "ERROR",
              reasons[TUC_SOURCE_FAULT == 0 ? 0 : expected_failure], &counts);
  return TUC_SOURCE_FAULT == 0 ? 0 : 1;
}
'''


def artifact_files():
    """Construct a bounded inert context bound to the separately installed wheel."""
    result = compile_cpu()
    manifest = json.loads(result.artifacts.manifest_json)
    wheel = _wheel_digest(required=True)
    package = Path(tuc.__file__).resolve().parent
    bindings = {"schema_version": "tuc.bounded_source_c11_bindings.v0",
                "consumer_digest": _digest(_read_file(ROOT / "consumer.py")),
                "package_sources": {name: _digest(_read_file(package / name))
                                    for name in PACKAGE_FILES},
                "wheel_digest": wheel, "source_intent_digest": result.source_intent_digest,
                "backend_bindings_digest": result.backend_bindings_digest,
                "hac_ir_digest": manifest["hac_ir_digest"],
                "primitive_source_digests": {
                    name: hashlib.sha256(result.artifacts.files()[name].encode("utf-8")).hexdigest()
                    for name in ("generated.c", "generated.h")
                },
                "inputs": [asdict(binding) for binding in result.input_bindings],
                "returns": [asdict(binding) for binding in result.output_bindings]}
    files = {"generated.c": result.artifacts.c11_source,
             "generated.h": result.artifacts.c11_header,
             "schedule.h": result.artifacts.schedule_header,
             "manifest.json": result.artifacts.manifest_json,
             "source-bindings.json": _json(bindings),
             "consumer.py": _read_file(ROOT / "consumer.py")}
    files.update({name: _read_file(ROOT / name) for name in SUPPORT_FILES})
    if wheel is not None:
        files["wheel-sha256.txt"] = wheel + "\n"
    files["worker.c"] = _worker(result, manifest, _binding_digest(files))
    if (any(len(text.encode("utf-8")) > MAX_FILE_BYTES for text in files.values()) or
            sum(len(text.encode("utf-8")) for text in files.values()) > MAX_CONTEXT_BYTES):
        raise ValueError("fixed source C11 context budget exceeded")
    return files


def _binding_digest(files):
    # The client text binds the worker-generation logic. Excluding the rendered
    # worker avoids a hash cycle while binding every input that generated it.
    return _digest(_json({name: text for name, text in files.items() if name != "worker.c"}))


def _expect(fault, invalid, manifest, public, binding_digest):
    if (type(fault) is not int or not 0 <= fault <= 13 or type(invalid) is not bool or
            (invalid and fault != 0)):
        raise ValueError("fixed source C11 fault selector rejected")
    counts = dict.fromkeys(COUNTERS, 0)
    value = {"schema_version": SCHEMA, "status": "PASS", "reason": "none", "fault": fault,
             "binding_digest": binding_digest}
    if invalid:
        return {**value, "status": "ERROR", "reason": "invalid_invocation", **counts}
    buffers = manifest["buffers"]
    for case in range(INPUT_CASES):
        outputs = reference_outputs(case)
        for _ in range(REPLAYS):
            ready, publications = set(), 0
            reason = "none"
            for event in manifest["events"]:
                kind = event["kind"]
                if any(slot not in ready for slot in event["inputs"]):
                    reason = "missing_operand"
                    break
                if kind == "execute":
                    if fault == event["operation"] + 1:
                        continue
                    counts["function_calls"] += 1
                elif kind == "publish_output":
                    ordinal = publications
                    publications += 1
                    if fault == ordinal + 10:
                        continue
                    tensor = buffers[event["inputs"][0]]["tensor"]
                    expected = outputs[public[tensor]]
                    actual = list(expected)
                    if fault == ordinal + 8:
                        actual[0] = struct.unpack("<f", struct.pack("<I", _bits(actual[0]) ^ 1))[0]
                    if fault == 12:
                        actual = outputs["joined_total" if public[tensor] == "branch_total"
                                         else "branch_total"]
                    if fault == 13 and ordinal == 0:
                        actual[-1] = math.nan
                    for got, wanted in zip(actual, expected, strict=True):
                        if not _normal_or_zero(got) or got != wanted:
                            reason = "numeric_mismatch"
                            break
                        counts["scalar_checks"] += 1
                    if reason != "none":
                        break
                    counts["published_outputs"] += 1
                ready.update(event["outputs"])
            if reason == "none" and fault in (10, 11):
                reason = "missing_publication"
            if reason == "none":
                counts["case_runs"] += 1
            else:
                counts["rejected_cases"] += 1
                value.update(status="ERROR", reason=reason)
    if fault and counts["rejected_cases"] != 6:
        raise ValueError("fixed source C11 mutation lacks corpus coverage")
    return {**value, **counts}


def expected_receipt(fault=0, invalid=False):
    """Synthetic protocol expectation, never observed execution evidence."""
    if type(fault) is not int or not 0 <= fault <= 13 or type(invalid) is not bool:
        raise ValueError("fixed source C11 fault selector rejected")
    return _expected_from_files(artifact_files(), fault, invalid)


def _expected_from_files(files, fault=0, invalid=False):
    bindings = json.loads(files["source-bindings.json"])
    public = {binding["tensor_index"]: binding["public_name"] for binding in bindings["returns"]}
    return _expect(fault, invalid, json.loads(files["manifest.json"]), public,
                   _binding_digest(files))


def _exact(value, expected):
    if (type(value) is not dict or len(value) != len(expected) or
            any(type(key) is not str for key in value) or set(value) != set(expected) or
            any(type(value[key]) is not type(expected[key]) or value[key] != expected[key]
                for key in expected)):
        raise ValueError("fixed source C11 receipt rejected")
    return value


def validate_receipt(value, fault=0, invalid=False):
    return _exact(value, expected_receipt(fault, invalid))


def _receipt_json(text):
    if type(text) is not str or len(text) > MAX_RECEIPT_BYTES:
        raise ValueError("fixed source C11 receipt budget rejected")
    if len(text.encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("fixed source C11 receipt budget rejected")
    depth = items = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            items += 1
            if depth > MAX_RECEIPT_DEPTH:
                raise ValueError("fixed source C11 receipt depth rejected")
        elif character in "]}":
            depth -= 1
        elif character in ",:":
            items += 1
        if items > MAX_RECEIPT_ITEMS:
            raise ValueError("fixed source C11 receipt item budget rejected")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("fixed source C11 duplicate receipt key")
            result[key] = value
        return result

    def reject_number(_value):
        raise ValueError("fixed source C11 receipt number rejected")

    def integer(value):
        if len(value) > 7 or not 0 <= int(value) <= 1_000_000:
            reject_number(value)
        return int(value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject_number,
                      parse_float=reject_number, parse_int=integer)


def report(files=None):
    files = artifact_files() if files is None else files
    bindings = json.loads(files["source-bindings.json"])
    return {"schema_version": "tuc.bounded_source_c11_candidate.v0", "status": "PASS",
            "source_intent_digest": bindings["source_intent_digest"],
            "backend_bindings_digest": bindings["backend_bindings_digest"],
            "wheel_digest": bindings["wheel_digest"],
            "wheel_bound": bindings["wheel_digest"] is not None,
            "binding_digest": _binding_digest(files),
            "computation": {key: bindings[key] for key in (
                "source_intent_digest", "hac_ir_digest", "primitive_source_digests",
                "inputs", "returns")},
            "context_digest": _digest(_json(files)), "input_cases": 3, "replays": 2,
            "operations": 7, "expected_baseline": _expected_from_files(files),
            "native_execution_observed": False, "cuda_execution_observed": False,
            "normal_runtime_admission": False, "latency_ns": None, "energy_pj": None}


def emit_context():
    _wheel_digest(required=True)
    files = artifact_files()
    parent = ROOT / "tmp"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError("fixed source C11 context parent rejected")
    parent.mkdir(exist_ok=True)
    if parent.resolve() != ROOT.resolve() / "tmp":
        raise ValueError("fixed source C11 context path rejected")
    directory = Path(tempfile.mkdtemp(prefix="bounded-source-c11.", dir=parent))
    for name, text in files.items():
        with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return directory


def accept(directory):
    _wheel_digest(required=True)
    path = Path(directory)
    if (path.is_symlink() or not path.is_dir() or path.resolve().parent != ROOT.resolve() / "tmp" or
            re.fullmatch(r"bounded-source-c11\.[A-Za-z0-9_-]{8,16}", path.name) is None):
        raise ValueError("fixed source C11 evidence path rejected")
    files = artifact_files()
    names = {f"{build}-{name}.json" for build in ("static", "sanitized")
             for name in ("proof", *(f"fault{i}" for i in range(1, 14)), "invalid")}
    image_files = {f"{build}-image-id.txt" for build in ("static", "sanitized")}
    actual = set()
    for item in path.iterdir():
        if len(actual) > len(files) + len(names) + len(image_files):
            raise ValueError("fixed source C11 evidence file count rejected")
        if item.is_symlink() or not item.is_file():
            raise ValueError("fixed source C11 evidence file type rejected")
        actual.add(item.name)
    if actual - {"record.json"} != set(files) | names | image_files:
        raise ValueError("fixed source C11 evidence coverage rejected")
    for name, text in files.items():
        if _read_file(path / name) != text:
            raise ValueError("fixed source C11 context drift rejected")
    observations = {}
    for build in ("static", "sanitized"):
        for fault in range(14):
            name = f"{build}-{'proof' if fault == 0 else f'fault{fault}'}.json"
            value = _receipt_json(_read_file(path / name, MAX_RECEIPT_BYTES))
            observations[name] = _exact(value, _expected_from_files(files, fault))
        name = f"{build}-invalid.json"
        value = _receipt_json(_read_file(path / name, MAX_RECEIPT_BYTES))
        observations[name] = _exact(value, _expected_from_files(files, invalid=True))
    image_ids = {}
    for build in ("static", "sanitized"):
        image_id = _read_file(path / f"{build}-image-id.txt", 80).strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
            raise ValueError("fixed source C11 image identity rejected")
        image_ids[build] = image_id
    record = {**report(files), "schema_version": "tuc.bounded_source_c11_record.v0",
              "native_execution_observed": True, "observation_scope": "fixed_cpu_application_only",
              "image_ids": image_ids, "observations": observations}
    if len(_json(record).encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("fixed source C11 record budget rejected")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--emit", action="store_true")
    group.add_argument("--accept", type=Path)
    args = parser.parse_args(argv)
    try:
        output = str(emit_context()) if args.emit else _json(
            accept(args.accept) if args.accept is not None else report()
        )
    except (OSError, ValueError):
        print("fixed source C11 conformance rejected", file=sys.stderr)
        return 1
    sys.stdout.buffer.write((output + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
