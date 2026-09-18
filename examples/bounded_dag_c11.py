"""Fixed CPU conformance context and receipt checks, never a native launcher.

Default operation is pure. --emit writes a fresh private allowlisted context;
the reviewed shell operator alone builds and executes it in isolated containers.
The Python oracle implements the four mathematical families independently of
the emitted operations and schedule. Receipts are local conformance observations,
not authenticated attestations or an admission path for the normal runtime.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

from examples import bounded_dag_compiler as portfolio
from tuc.backends.bounded_dag import DAGTarget, validate_bounded_dag_artifacts

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "docker/bounded-dag-c11"
FAMILIES = ("chain", "fanout", "fanin", "diamond")
SHAPES = ((1, 1, 1), (5, 3, 4), (33, 7, 5))
INPUT_CASES = 3
REPLAYS = 2
MUTATIONS = ("skip-operation", "corrupt-output", "missing-publication")
MAX_FILE_BYTES = 256 * 1024
MAX_CONTEXT_BYTES = 2 * 1024 * 1024
MAX_RECEIPT_BYTES = 4096
MAX_RECEIPT_DEPTH = 4
MAX_RECEIPT_ITEMS = 64
SCHEMA = "tuc.bounded_dag_c11_observation.v0"


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _f32(value):
    rounded = struct.unpack("<f", struct.pack("<f", value))[0]
    if not _normal_or_zero(rounded):
        raise ValueError("fixed DAG reference numeric domain rejected")
    return rounded


def _normal_or_zero(value):
    return math.isfinite(value) and (value == 0.0 or abs(value) >= 2.0 ** -126)


def _bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def fixed_inputs(shape, case):
    """Three finite bounded vectors, including non-dyadic FP32 and signed zero."""
    if shape not in SHAPES or type(case) is not int or not 0 <= case < INPUT_CASES:
        raise ValueError("fixed DAG input selection rejected")
    rows, inner, columns = shape
    result = {}
    for name, count, offset in (("a", rows * inner, 2), ("b", inner * columns, 5),
                                ("weights", columns * inner, 11)):
        if case == 0:
            values = [_f32(((i * 5 + offset) % 13 - 6) / 4) for i in range(count)]
        elif case == 1:
            values = [_f32(((i * 7 + offset) % 19 - 9) / 10) for i in range(count)]
            if name == "a":
                values[0] = abs(values[0])
        else:
            values = [_f32(((i * 11 + offset) % 23 - 11) / 7) for i in range(count)]
            if count > 1:
                values[0] = -0.0
            else:
                values[0] = abs(values[0])
        result[name] = values
    return result


def reference_outputs(family, shape, case):
    """Ordered binary32 arithmetic; does not inspect IR, artifacts or metadata."""
    if type(family) is not str or family not in FAMILIES:
        raise ValueError("fixed DAG reference family rejected")
    rows, inner, columns = shape
    inputs = fixed_inputs(shape, case)

    def relu(values):
        return [0.0 if value < 0 else value for value in values]

    def matmul(left, right, m, k, n):
        output = []
        for row in range(m):
            for column in range(n):
                value = 0.0
                for reduction in range(k):
                    product = _f32(left[row * k + reduction] * right[reduction * n + column])
                    value = _f32(value + product)
                output.append(value)
        return output

    def row_sums(values, width):
        result = []
        for row in range(rows):
            value = 0.0
            for column in range(width):
                value = _f32(value + values[row * width + column])
            result.append(value)
        return result

    left, right = inputs["a"], inputs["b"]
    if family in ("fanin", "diamond"):
        left, right = relu(left), relu(right)
    projection = matmul(left, right, rows, inner, columns)
    if family == "diamond":
        second = matmul(relu(projection), inputs["weights"], rows, columns, inner)
        return {"raw": row_sums(projection, columns), "row_sum": row_sums(second, inner)}
    if family == "fanout":
        return {"raw": row_sums(projection, columns),
                "row_sum": row_sums(relu(projection), columns)}
    return {"row_sum": row_sums(relu(projection) if family == "chain" else projection, columns)}


def _constant(name, vectors):
    if not vectors or len(vectors) != INPUT_CASES or not vectors[0]:
        raise ValueError("fixed DAG constant rejected")
    rows = []
    for values in vectors:
        if len(values) != len(vectors[0]) or not all(_normal_or_zero(value) for value in values):
            raise ValueError("fixed DAG constant extent or finiteness rejected")
        rows.append("  {" + ",".join(f"UINT32_C(0x{_bits(value):08x})" for value in values) + "}")
    return f"static const uint32_t {name}[3][{len(vectors[0])}] = {{\n" + ",\n".join(rows) + "\n};"


def _worker(index, family, shape, manifest):
    """Inline only canonical events from a fully revalidated compiler bundle."""
    tensors = manifest["tensors"]
    buffers = manifest["buffers"]
    operations = manifest["operations"]
    if manifest["planned_copy_bytes"] or any(op["target"] != "c11" for op in operations):
        raise ValueError("CPU conformance rejects device operations or copies")
    inputs = [fixed_inputs(shape, case) for case in range(INPUT_CASES)]
    expected = [reference_outputs(family, shape, case) for case in range(INPUT_CASES)]
    input_names = [tensors[tensor]["name"] for tensor in manifest["input_tensors"]]
    output_names = [tensors[tensor]["name"] for tensor in manifest["output_tensors"]]
    if set(input_names) != ({"a", "b", "weights"} if family == "diamond" else {"a", "b"}):
        raise ValueError("fixed DAG input boundary changed")
    if set(output_names) != set(expected[0]):
        raise ValueError("fixed DAG terminal boundary changed")
    lines = [f"#define tuc_dag_op_{op['index']} tuc_case_{index}_op_{op['index']}"
             for op in operations]
    lines += ['#include "generated.c"', '#include "../../common.h"']
    for tensor in manifest["input_tensors"]:
        name = tensors[tensor]["name"]
        lines.append(_constant(f"input_{tensor}", [value[name] for value in inputs]))
    for tensor in manifest["output_tensors"]:
        name = tensors[tensor]["name"]
        lines.append(_constant(f"expected_{tensor}", [value[name] for value in expected]))
    lines += [f"int tuc_case_{index}(struct tuc_counts *counts) {{"]
    for buffer in buffers:
        lines.append(f"  float slot_{buffer['index']}[{buffer['bytes'] // 4}];")
    lines += [f"  for (size_t vector = 0; vector < {INPUT_CASES}U; ++vector) {{",
              f"    for (size_t replay = 0; replay < {REPLAYS}U; ++replay) {{",
              f"      unsigned char ready[{len(buffers)}] = {{0}};",
              "      size_t publications = 0U;"]
    for buffer in buffers:
        lines.append(f"      tuc_poison(slot_{buffer['index']}, {buffer['bytes'] // 4}U);")
    first_publication = True
    for event in manifest["events"]:
        kind = event["kind"]
        if kind == "bind_input":
            slot = event["outputs"][0]
            tensor = buffers[slot]["tensor"]
            count = buffers[slot]["bytes"] // 4
            lines += [f"      tuc_bind(slot_{slot}, input_{tensor}[vector], {count}U);",
                      f"      ready[{slot}] = 1U;"]
        elif kind == "execute":
            op = event["operation"]
            output = event["outputs"][0]
            checks = " || ".join(f"!ready[{slot}]" for slot in event["inputs"])
            args = ", ".join(f"slot_{slot}" for slot in (*event["inputs"], output))
            lines += [f"      if ({checks}) return 1;",
                      f"      if (!(TUC_DAG_FAULT == 1 && {op}U == 0U)) {{",
                      f"        tuc_dag_op_{op}({args});",
                      "        ++counts->function_calls;",
                      f"        if (!tuc_normal_finite(slot_{output}, "
                      f"{buffers[output]['bytes'] // 4}U)) return 2;",
                      f"        ready[{output}] = 1U;", "      }"]
        elif kind == "publish_output":
            slot = event["inputs"][0]
            tensor = buffers[slot]["tensor"]
            count = buffers[slot]["bytes"] // 4
            lines.append(f"      if (!ready[{slot}]) return 1;")
            if first_publication:
                lines += [f"      if (TUC_DAG_FAULT == 2) tuc_corrupt(slot_{slot});",
                          "      if (TUC_DAG_FAULT != 3) {"]
                first_publication = False
            else:
                lines.append("      {")
            lines += [f"        if (!tuc_check(slot_{slot}, expected_{tensor}[vector],",
                      f"                       {count}U, counts)) return 2;",
                      "        ++publications;", "        ++counts->published_outputs;", "      }"]
        else:
            raise ValueError("fixed C11 schedule event rejected")
    lines += [f"      if (publications != {len(output_names)}U) return 3;",
              "      ++counts->case_runs;", "    }", "  }", "  return 0;", "}", ""]
    return "\n".join(lines)


COMMON = r'''#ifndef TUC_DAG_COMMON_H
#define TUC_DAG_COMMON_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#ifndef TUC_DAG_FAULT
#define TUC_DAG_FAULT 0
#endif
struct tuc_counts {
  size_t case_runs, function_calls, scalar_checks, published_outputs;
};
static inline void tuc_poison(float *output, size_t count) {
  const uint32_t poison = UINT32_C(0x7fc00001);
  for (size_t i = 0; i < count; ++i) memcpy(output + i, &poison, sizeof(poison));
}
static inline void tuc_bind(float *output, const uint32_t *input, size_t count) {
  for (size_t i = 0; i < count; ++i) memcpy(output + i, input + i, sizeof(uint32_t));
}
static inline void tuc_corrupt(float *value) {
  uint32_t bits;
  memcpy(&bits, value, sizeof(bits));
  bits ^= UINT32_C(1);
  memcpy(value, &bits, sizeof(bits));
}
static inline int tuc_normal_finite(const float *values, size_t count) {
  for (size_t i = 0; i < count; ++i) {
    const int category = fpclassify(values[i]);
    if (category != FP_NORMAL && category != FP_ZERO) return 0;
  }
  return 1;
}
static inline int tuc_check(const float *actual, const uint32_t *expected,
                            size_t count, struct tuc_counts *counts) {
  for (size_t i = 0; i < count; ++i) {
    uint32_t bits;
    memcpy(&bits, actual + i, sizeof(bits));
    if (!tuc_normal_finite(actual + i, 1U)) return 0;
    if (bits != expected[i] && !((bits & UINT32_C(0x7fffffff)) == 0U &&
                                (expected[i] & UINT32_C(0x7fffffff)) == 0U)) return 0;
    ++counts->scalar_checks;
  }
  return 1;
}
#endif
'''


def _main():
    declarations = "\n".join(f"int tuc_case_{i}(struct tuc_counts *counts);" for i in range(12))
    functions = ", ".join(f"tuc_case_{i}" for i in range(12))
    return f'''#define _POSIX_C_SOURCE 200809L
#include "common.h"
#include <fenv.h>
#include <stdio.h>
#include <unistd.h>
#if !defined(__x86_64__) || !defined(__SSE2__)
#error "fixed DAG C11 conformance requires the reviewed x86-64 SSE2 target"
#endif
#include <xmmintrin.h>
{declarations}
int main(int argc, char **argv) {{
  (void)argv;
  (void)alarm(20U);
  if (argc != 1 || fegetround() != FE_TONEAREST) return 2;
  /* MXCSR: rounding-control bits 13/14, flush-to-zero bit 15, denormals-are-zero bit 6. */
  if ((_mm_getcsr() & UINT32_C(0xe040)) != 0U) return 2;
  struct tuc_counts counts = {{0, 0, 0, 0}};
  size_t rejected_cases = 0U;
  int (*const cases[])(struct tuc_counts *) = {{{functions}}};
  const char *const reasons[] = {{"", "missing_operand", "numeric_mismatch",
                                "missing_publication"}};
  for (size_t i = 0; i < 12U; ++i) {{
    int result = cases[i](&counts);
    if (result != 0) {{
      if (result < 1 || result > 3) return 2;
      if (TUC_DAG_FAULT == result) {{ ++rejected_cases; continue; }}
      printf("{{\\"schema_version\\":\\"{SCHEMA}\\",\\"status\\":\\"ERROR\\","
             "\\"reason\\":\\"%s\\",\\"case\\":%zu}}\\n", reasons[result], i);
      return 1;
    }}
  }}
  if (TUC_DAG_FAULT != 0) {{
    printf("{{\\"schema_version\\":\\"{SCHEMA}\\",\\"status\\":\\"ERROR\\","
           "\\"reason\\":\\"%s\\",\\"rejected_cases\\":%zu}}\\n",
           reasons[TUC_DAG_FAULT], rejected_cases);
    return 1;
  }}
  printf("{{\\"schema_version\\":\\"{SCHEMA}\\",\\"status\\":\\"PASS\\","
         "\\"case_runs\\":%zu,\\"function_calls\\":%zu,\\"scalar_checks\\":%zu,"
         "\\"published_outputs\\":%zu}}\\n", counts.case_runs, counts.function_calls,
         counts.scalar_checks, counts.published_outputs);
  return 0;
}}
'''


def artifact_files():
    """Build only the fixed twelve-case context in memory, validating all texts."""
    files = {"common.h": COMMON, "main.c": _main()}
    for index, (family, shape) in enumerate((f, s) for f in FAMILIES for s in SHAPES):
        count = {"chain": 3, "fanout": 4, "fanin": 4, "diamond": 7}[family]
        compiled, artifacts = portfolio.compile_case(family, "c" * count, shape)
        validate_bounded_dag_artifacts(
            artifacts, compiled.hac_ir, compiled.partition_plan, {"dag-c11": DAGTarget.C11}
        )
        manifest = json.loads(artifacts.manifest_json)
        for name, value in artifacts.files().items():
            if name != "kernels.cuh":
                files[f"cases/{index:02d}/{name}"] = value
        files[f"cases/{index:02d}/worker.c"] = _worker(index, family, shape, manifest)
    # Include the reviewed isolation script in the digest and accept-time drift
    # check. Docker's allowlist excludes it from both worker build stages.
    for name in ("Dockerfile", "Dockerfile.dockerignore", "build.sh", "operator.sh"):
        files[name] = (CONTEXT / name).read_text(encoding="utf-8")
    if any(len(value.encode()) > MAX_FILE_BYTES for value in files.values()):
        raise ValueError("fixed DAG artifact size rejected")
    if sum(len(value.encode()) for value in files.values()) > MAX_CONTEXT_BYTES:
        raise ValueError("fixed DAG context size rejected")
    return files


def expected_receipt(mutation=None):
    """Synthetic protocol expectation, never evidence of an executed process."""
    if mutation is None:
        return {"schema_version": SCHEMA, "status": "PASS", "case_runs": 72,
                "function_calls": 324, "scalar_checks": 1404, "published_outputs": 108}
    if type(mutation) is not str or mutation not in MUTATIONS:
        raise ValueError("fixed DAG mutation rejected")
    return {"schema_version": SCHEMA, "status": "ERROR", "rejected_cases": 12,
            "reason": dict(zip(MUTATIONS, ("missing_operand", "numeric_mismatch",
                                          "missing_publication"), strict=True))[mutation]}


def validate_receipt(value, mutation=None):
    expected = expected_receipt(mutation)
    if (type(value) is not dict or len(value) != len(expected) or
            any(type(key) is not str for key in value) or set(value) != set(expected) or
            any(type(value[key]) is not type(expected[key]) or value[key] != expected[key]
                for key in expected)):
        raise ValueError("fixed DAG observation rejected")
    return value


def report(files=None):
    files = artifact_files() if files is None else files
    return {"schema_version": "tuc.bounded_dag_c11_candidate.v0", "status": "PASS",
            "families": list(FAMILIES), "shapes": [list(shape) for shape in SHAPES],
            "input_cases": INPUT_CASES, "replays": REPLAYS, "compiled_cases": 12,
            "numeric_policy": "normal_or_zero_ordered_binary32_exact_except_signed_zero",
            "context_digest": "sha256:" + sha256(_json(files).encode()).hexdigest(),
            "native_execution_observed": False, "normal_runtime_admission": False,
            "cuda_execution_observed": False, "latency_ns": None, "energy_pj": None}


def emit_context():
    files = artifact_files()
    parent = ROOT / "tmp"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError("fixed DAG context parent rejected")
    parent.mkdir(exist_ok=True)
    if parent.resolve() != ROOT / "tmp":
        raise ValueError("fixed DAG context parent escapes repository")
    directory = Path(tempfile.mkdtemp(prefix="bounded-dag-c11.", dir=parent))
    for name, value in files.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as output:
            output.write(value)
    return directory


def _read_file(path, limit=MAX_FILE_BYTES):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("fixed DAG evidence file rejected")
    with path.open("rb") as source:
        value = source.read(limit + 1)
    if len(value) > limit:
        raise ValueError("fixed DAG evidence file budget exceeded")
    return value.decode("utf-8")


def _receipt_json(text):
    if type(text) is not str or len(text.encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("fixed DAG observation byte budget exceeded")
    # Bound recursive parser work before json.loads, independently of the host's
    # recursionlimit. Quotes and escaped quotes must not count as JSON structure.
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
                raise ValueError("fixed DAG observation nesting rejected")
        elif character in "]}":
            depth -= 1
        elif character in ",:":
            items += 1
        if items > MAX_RECEIPT_ITEMS:
            raise ValueError("fixed DAG observation item budget exceeded")

    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate fixed DAG observation field")
            result[key] = value
        return result

    def reject_nonfinite(value):
        raise ValueError("fixed DAG observation nonfinite number rejected")

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            reject_nonfinite(value)
        return result

    try:
        return json.loads(text, object_pairs_hook=unique_fields,
                          parse_constant=reject_nonfinite, parse_float=finite_float)
    except RecursionError as error:
        raise ValueError("fixed DAG observation nesting rejected") from error


def accept(directory):
    path = Path(directory)
    if (path.is_symlink() or not path.is_dir() or
            path.resolve().parent != ROOT / "tmp" or
            re.fullmatch(r"bounded-dag-c11\.[A-Za-z0-9_-]{8,16}", path.name) is None):
        raise ValueError("fixed DAG evidence directory rejected")
    files = artifact_files()
    for name, expected in files.items():
        target = path / name
        if any(parent.is_symlink() for parent in target.parents if parent != ROOT):
            raise ValueError("fixed DAG evidence symlink rejected")
        if _read_file(target) != expected:
            raise ValueError("fixed DAG context changed")
    observations = {}
    for build in ("static", "sanitized"):
        for mutation in (None, *MUTATIONS):
            name = f"{build}-{mutation or 'proof'}.json"
            value = _receipt_json(_read_file(path / name, MAX_RECEIPT_BYTES))
            observations[name] = validate_receipt(value, mutation)
    image_ids = {}
    for build in ("static", "sanitized"):
        image_id = _read_file(path / f"{build}-image-id.txt", 80).strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
            raise ValueError("fixed DAG image identity rejected")
        image_ids[build] = image_id
    return {**report(files), "schema_version": "tuc.bounded_dag_c11_record.v0",
            "native_execution_observed": True, "observation_scope": "fixed_cpu_portfolio_only",
            "image_ids": image_ids, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--emit", action="store_true")
    action.add_argument("--accept", type=Path)
    args = parser.parse_args()
    try:
        if args.emit:
            print(emit_context())
        else:
            print(_json(accept(args.accept) if args.accept is not None else report()))
    except (ValueError, OSError, UnicodeError) as error:
        print(f"bounded DAG conformance rejected: {type(error).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
