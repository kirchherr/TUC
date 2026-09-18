"""Installed-wheel C11 graph-entrypoint conformance generator and verifier.

Python emits and verifies bounded inert text only. The separate explicit operator
owns native compilation/execution. Synthetic expected receipts are not evidence.
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
from tuc.compiler.bounded_c11 import (
    emit_bounded_c11_entrypoint,
    validate_bounded_c11_entrypoint,
)
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
GRAPHS = ("app", "tiny")
INPUT_CASES = 3
REPLAYS = 2
CONTROL_COUNT = 34
MAX_FILE_BYTES = 512 * 1024
MAX_CONTEXT_BYTES = 4 * 1024 * 1024
MAX_RECEIPT_BYTES = 4096
MAX_RECEIPT_DEPTH = 4
MAX_RECEIPT_ITEMS = 64
SCHEMA = "tuc.bounded_c11_entrypoint_observation.v0"
SUPPORT_FILES = ("Dockerfile", "Dockerfile.dockerignore", "build.sh", "operator.sh")
INPUT_SHAPES = (("a", (3, 2)), ("b", (2, 4)), ("c", (4, 3)), ("d", (3, 2)))
CONTROL_NAMES = (
    "input_arity", "output_arity", "null_input_descriptors", "null_output_descriptors",
    "null_input", "null_output", "input_extent", "output_extent",
    "misaligned_input", "misaligned_output", "input_input_overlap", "input_output_overlap",
    "output_output_overlap", "output_input_descriptor_overlap", "output_descriptor_overlap",
    "input_address_wrap", "output_address_wrap", "misaligned_input_descriptors",
    "misaligned_output_descriptors", "nan_input", "signaling_nan_input", "infinite_input",
    "subnormal_input", "overflow_product", "hidden_subnormal_product", "rounded_zero_product",
    "rounding_mode", "flush_to_zero", "denormals_are_zero", "unmasked_exception",
    "unbounded_input_arity", "unbounded_output_arity",
    "overflow_addition", "hidden_subnormal_addition",
)
COUNTERS = ("case_runs", "entrypoint_calls", "scalar_checks", "published_outputs",
            "rejected_cases", "sentinel_checks")

PACKAGE_FILES = (
    "compiler/bounded_c11.py", "backends/bounded_c11_codegen.py",
    "compiler/bounded_source.py", "compiler/pipeline.py", "compiler/lowering.py",
    "compiler/movement.py", "compiler/decisions.py", "backends/base.py",
    "backends/registry.py", "backends/bounded_dag.py", "backends/bounded_dag_codegen.py",
    "frontend/source_intent.py", "frontend/source_intent_metadata.py",
    "frontend/source_intent_returns.py", "frontend/triton_metadata.py", "frontend/hints.py",
    "ir/model.py", "ir/modules.py", "ir/dialect.py", "ir/dump.py", "ir/memory.py",
    "runtime/partitioning.py", "runtime/plan.py", "runtime/residency.py",
)

def _app_module():
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

def _normal_or_zero(value):
    return math.isfinite(value) and (value == 0.0 or abs(value) >= 2.0 ** -126)

def _f32(value):
    rounded = struct.unpack("<f", struct.pack("<f", value))[0]
    if not _normal_or_zero(rounded):
        raise ValueError("fixed C11 entrypoint numeric domain rejected")
    return rounded

def _bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]

def _app_inputs(case):
    """Exact RFC 0321 consumer corpus, independent of compiler artifacts."""
    if type(case) is not int or not 0 <= case < INPUT_CASES:
        raise ValueError("fixed C11 entrypoint input case rejected")
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

def _app_reference(case):
    """Explicit application math; no manifest, event, IR or kernel inspection."""
    inputs = _app_inputs(case)

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
        raise ValueError("fixed C11 entrypoint bounded regular file required")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("fixed C11 entrypoint file budget exceeded")
    return data.decode("utf-8")

def _wheel_digest(required=False):
    path = ROOT / "wheel-sha256.txt"
    if not path.exists() and not path.is_symlink():
        if required:
            raise ValueError("fixed C11 entrypoint wheel binding required")
        return None
    text = _read_file(path, 80)
    digest = text.removesuffix("\r\n") if text.endswith("\r\n") else text.removesuffix("\n")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ValueError("fixed C11 entrypoint wheel binding rejected")
    return digest

def _constant(name, vectors):
    rows = ["{" + ",".join(f"UINT32_C(0x{_bits(value):08x})" for value in row) + "}"
            for row in vectors]
    return (f"static const uint32_t {name}[3][{len(vectors[0])}] = {{" +
            ",".join(rows) + "};")

def _receipt_json(text):
    if type(text) is not str or len(text) > MAX_RECEIPT_BYTES:
        raise ValueError("fixed C11 entrypoint receipt budget rejected")
    if len(text.encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("fixed C11 entrypoint receipt budget rejected")
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
                raise ValueError("fixed C11 entrypoint receipt depth rejected")
        elif character in "]}":
            depth -= 1
        elif character in ",:":
            items += 1
        if items > MAX_RECEIPT_ITEMS:
            raise ValueError("fixed C11 entrypoint receipt item budget rejected")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("fixed C11 entrypoint duplicate receipt key")
            result[key] = value
        return result

    def reject_number(_value):
        raise ValueError("fixed C11 entrypoint receipt number rejected")

    def integer(value):
        if len(value) > 7 or not 0 <= int(value) <= 1_000_000:
            reject_number(value)
        return int(value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject_number,
                      parse_float=reject_number, parse_int=integer)


def source_module(graph="app"):
    if graph == "app":
        return _app_module()
    if graph != "tiny":
        raise ValueError("fixed entrypoint graph rejected")
    return SourceIntentModule(
        "tiny_projection_sum",
        (SourceIntentTensor("left", (1, 2)), SourceIntentTensor("right", (2, 1)),
         SourceIntentTensor("product", (1, 1)), SourceIntentTensor("rows", (1,))),
        (SourceIntentOperation("project", "matmul", ("left", "right"), ("product",)),
         SourceIntentOperation("summarize", "reduction", ("product",), ("rows",),
                               attributes={"axis": 1})),
        returns=(SourceIntentReturn("tiny_total", "rows"),),
    )


def compile_graph(graph):
    module, bindings = source_module(graph), backend_bindings()
    compilation = compile_bounded_source_intent(module, bindings)
    validate_bounded_source_compilation(module, bindings, compilation)
    artifact = emit_bounded_c11_entrypoint(module, bindings, compilation)
    validate_bounded_c11_entrypoint(module, bindings, compilation, artifact)
    return compilation, artifact


def fixed_inputs(graph, case):
    if type(case) is not int or not 0 <= case < INPUT_CASES:
        raise ValueError("fixed entrypoint input case rejected")
    if graph == "app":
        return _app_inputs(case)
    if graph != "tiny":
        raise ValueError("fixed entrypoint graph rejected")
    left, right = (((1.25, -0.5), (0.75, 2.0)),
                   ((1 / 7, -3 / 7), (2 / 7, 5 / 7)),
                   ((-0.0, 2.0), (3.0, -0.5)))[case]
    return {"left": [_f32(value) for value in left], "right": [_f32(value) for value in right]}


def reference_outputs(graph, case):
    if graph == "app":
        return _app_reference(case)
    inputs = fixed_inputs(graph, case)
    value = 0.0
    for left, right in zip(inputs["left"], inputs["right"], strict=True):
        value = _f32(value + _f32(left * right))
    return {"tiny_total": [_f32(0.0 + value)]}


_WORKER = r'''#define _POSIX_C_SOURCE 200809L
#include "entrypoint.h"
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
#ifndef TUC_ENTRYPOINT_FAULT
#define TUC_ENTRYPOINT_FAULT 0
#endif
#if TUC_ENTRYPOINT_FAULT < 0 || TUC_ENTRYPOINT_FAULT > 3
#error "unknown fixed worker fault"
#endif
typedef enum tuc_c11_status (*tuc_entry)(const struct tuc_c11_input *, size_t,
                                       const struct tuc_c11_output *, size_t);
struct tuc_counts {
  size_t case_runs, entrypoint_calls, scalar_checks, published_outputs;
  size_t rejected_cases, sentinel_checks;
};
struct tuc_case {
  tuc_entry run;
  size_t input_count, output_count;
  size_t input_sizes[4], output_sizes[2];
  const uint32_t *input[3][4];
  const uint32_t *expected[3][2];
};
static void tuc_bits(float *value, uint32_t bits) { memcpy(value, &bits, sizeof(bits)); }
static uint32_t tuc_read(const float *value) {
  uint32_t bits; memcpy(&bits, value, sizeof(bits)); return bits;
}
static void tuc_init(const struct tuc_case *test, size_t vector,
                     float input[4][12], float output[2][3],
                     struct tuc_c11_input inputs[4], struct tuc_c11_output outputs[2]) {
  memset(input, 0, 4U * 12U * sizeof(float));
  for (size_t i = 0; i < 4U; ++i) {
    inputs[i].data = input[i]; inputs[i].elements = test->input_sizes[i];
    for (size_t j = 0; j < test->input_sizes[i]; ++j)
      tuc_bits(&input[i][j], test->input[vector][i][j]);
  }
  for (size_t i = 0; i < 2U; ++i) {
    outputs[i].data = output[i]; outputs[i].elements = test->output_sizes[i];
    for (size_t j = 0; j < 3U; ++j) tuc_bits(&output[i][j], UINT32_C(0x7fc01234));
  }
}
static int tuc_positive(const struct tuc_case *test, size_t vector, struct tuc_counts *counts) {
  float input[4][12], output[2][3];
  struct tuc_c11_input inputs[4]; struct tuc_c11_output outputs[2];
  tuc_init(test, vector, input, output, inputs, outputs);
  unsigned char input_before[sizeof(input)], inputs_before[sizeof(inputs)];
  unsigned char outputs_before[sizeof(outputs)];
  memcpy(input_before, input, sizeof(input));
  memcpy(inputs_before, inputs, sizeof(inputs)); memcpy(outputs_before, outputs, sizeof(outputs));
  enum tuc_c11_status result = test->run(inputs, test->input_count, outputs, test->output_count);
  ++counts->entrypoint_calls;
  if (result != TUC_C11_OK) return 2;
  if (TUC_ENTRYPOINT_FAULT == 1) tuc_bits(&output[0][0], tuc_read(&output[0][0]) ^ UINT32_C(1));
  for (size_t i = 0; i < test->output_count; ++i) {
    for (size_t j = 0; j < test->output_sizes[i]; ++j) {
      const uint32_t actual = tuc_read(&output[i][j]), expected = test->expected[vector][i][j];
      if (actual != expected && !((actual & UINT32_C(0x7fffffff)) == 0U &&
                                 (expected & UINT32_C(0x7fffffff)) == 0U)) return 1;
      ++counts->scalar_checks;
    }
    ++counts->published_outputs;
  }
  for (size_t i = 0; i < 2U; ++i)
    for (size_t j = test->output_sizes[i]; j < 3U; ++j)
      if (tuc_read(&output[i][j]) != UINT32_C(0x7fc01234)) return 3;
  if (memcmp(input_before, input, sizeof(input)) != 0 ||
      memcmp(inputs_before, inputs, sizeof(inputs)) != 0 ||
      memcmp(outputs_before, outputs, sizeof(outputs)) != 0) return 3;
  ++counts->case_runs;
  return 0;
}
static int tuc_negative(const struct tuc_case *test, size_t vector, size_t control,
                        struct tuc_counts *counts) {
  float input[4][12], output[2][3];
  struct tuc_c11_input inputs[4]; struct tuc_c11_output outputs[2];
  tuc_init(test, vector, input, output, inputs, outputs);
  const struct tuc_c11_input *input_arg = inputs;
  const struct tuc_c11_output *output_arg = outputs;
  size_t input_count = test->input_count, output_count = test->output_count;
  enum tuc_c11_status expected = TUC_C11_ARGUMENT;
  const unsigned int saved_csr = _mm_getcsr();
  const int saved_round = fegetround();
  switch (control) {
    case 0: --input_count; break;
    case 1: --output_count; break;
    case 2: input_arg = NULL; break;
    case 3: output_arg = NULL; break;
    case 4: inputs[0].data = NULL; break;
    case 5: outputs[0].data = NULL; break;
    case 6: --inputs[0].elements; break;
    case 7: --outputs[0].elements; break;
    case 8: inputs[0].data = (const float *)(const void *)
                           ((const unsigned char *)input + 1U); break;
    case 9: outputs[0].data = (float *)(void *)((unsigned char *)output + 1U); break;
    case 10: inputs[1].data = inputs[0].data; break;
    case 11: outputs[0].data = input[0]; break;
    case 12: outputs[1].data = outputs[0].data; break;
    case 13: outputs[0].data = (float *)(void *)inputs; break;
    case 14: outputs[0].data = (float *)(void *)outputs; break;
    case 15: inputs[0].data = (const float *)(uintptr_t)(UINTPTR_MAX - (uintptr_t)3U); break;
    case 16: outputs[0].data = (float *)(uintptr_t)(UINTPTR_MAX - (uintptr_t)3U); break;
    case 17: input_arg = (const struct tuc_c11_input *)(const void *)
                       ((const unsigned char *)inputs + 1U); break;
    case 18: output_arg = (const struct tuc_c11_output *)(const void *)
                        ((const unsigned char *)outputs + 1U); break;
    case 19: tuc_bits(&input[0][0], UINT32_C(0x7fc00001)); expected = TUC_C11_NUMERIC; break;
    case 20: tuc_bits(&input[0][0], UINT32_C(0x7f800001)); expected = TUC_C11_NUMERIC; break;
    case 21: tuc_bits(&input[0][0], UINT32_C(0x7f800000)); expected = TUC_C11_NUMERIC; break;
    case 22: tuc_bits(&input[0][0], UINT32_C(1)); expected = TUC_C11_NUMERIC; break;
    case 23:
      tuc_bits(&input[0][0], UINT32_C(0x7f7fffff));
      tuc_bits(&input[1][0], UINT32_C(0x40000000)); expected = TUC_C11_NUMERIC; break;
    case 24:
    case 25:
      /* Both operands are normal. The first product underflows and a later
         1*1 term hides it in the final dot product if product checks are absent. */
      tuc_bits(&input[0][0], UINT32_C(0x00800000));
      tuc_bits(&input[0][1], UINT32_C(0x3f800000));
      tuc_bits(&input[1][0], control == 24U ? UINT32_C(0x3f000000) : UINT32_C(0x00800000));
      tuc_bits(&input[1][test->input_count == 4U ? 4U : 1U], UINT32_C(0x3f800000));
      expected = TUC_C11_NUMERIC; break;
    case 26:
      if (fesetround(FE_DOWNWARD) != 0) return 4;
      expected = TUC_C11_ENVIRONMENT; break;
    case 27: _mm_setcsr(saved_csr | UINT32_C(0x8000)); expected = TUC_C11_ENVIRONMENT; break;
    case 28: _mm_setcsr(saved_csr | UINT32_C(0x0040)); expected = TUC_C11_ENVIRONMENT; break;
    case 29:
      /* A signaling NaN must remain unread while invalid exceptions are unmasked. */
      tuc_bits(&input[0][0], UINT32_C(0x7f800001));
      _mm_setcsr((saved_csr & ~UINT32_C(0x00bf)));
      expected = TUC_C11_ENVIRONMENT; break;
    case 30: input_count = SIZE_MAX; break;
    case 31: output_count = SIZE_MAX; break;
    case 32:
      memset(input, 0, sizeof(input));
      tuc_bits(&input[0][0], UINT32_C(0x3f800000));
      tuc_bits(&input[0][1], UINT32_C(0x3f800000));
      tuc_bits(&input[1][0], UINT32_C(0x7f7fffff));
      tuc_bits(&input[1][test->input_count == 4U ? 4U : 1U], UINT32_C(0x7f7fffff));
      expected = TUC_C11_NUMERIC; break;
    case 33:
      memset(input, 0, sizeof(input));
      tuc_bits(&input[0][0], UINT32_C(0x3f800000));
      tuc_bits(&input[1][0], UINT32_C(0x00800001));
      tuc_bits(&input[1][1], UINT32_C(0x80800000));
      if (test->input_count == 4U) {
        /* Each projection value is normal; a row sum briefly becomes
           subnormal before a later +1 would conceal the invalid addition. */
        tuc_bits(&input[1][2], UINT32_C(0x3f800000));
      } else tuc_bits(&input[0][1], UINT32_C(0x3f800000));
      expected = TUC_C11_NUMERIC; break;
    default: return 4;
  }
  unsigned char input_before[sizeof(input)], inputs_before[sizeof(inputs)];
  unsigned char outputs_before[sizeof(outputs)];
  memcpy(input_before, input, sizeof(input));
  memcpy(inputs_before, inputs, sizeof(inputs)); memcpy(outputs_before, outputs, sizeof(outputs));
  const enum tuc_c11_status result = test->run(input_arg, input_count, output_arg, output_count);
  ++counts->entrypoint_calls;
  if (fesetround(saved_round) != 0) return 4;
  _mm_setcsr(saved_csr);
  if (TUC_ENTRYPOINT_FAULT == 2) expected = TUC_C11_OK;
  if (result != expected) return 2;
  if (TUC_ENTRYPOINT_FAULT == 3) tuc_bits(&output[1][2], UINT32_C(0));
  for (size_t i = 0; i < 2U; ++i) {
    for (size_t j = 0; j < 3U; ++j) {
      if (tuc_read(&output[i][j]) != UINT32_C(0x7fc01234)) return 3;
      ++counts->sentinel_checks;
    }
  }
  if (memcmp(input_before, input, sizeof(input)) != 0 ||
      memcmp(inputs_before, inputs, sizeof(inputs)) != 0 ||
      memcmp(outputs_before, outputs, sizeof(outputs)) != 0) return 3;
  ++counts->rejected_cases;
  return 0;
}
'''


def _worker(compiled, binding_digest):
    lines = [_WORKER, f'#define TUC_ENTRYPOINT_BINDING "{binding_digest}"']
    initializers = []
    for graph in GRAPHS:
        compilation, entrypoint = compiled[graph]
        ins, outs = compilation.input_bindings, compilation.output_bindings
        for binding in ins:
            lines.append(_constant(f"{graph}_in_{binding.tensor_index}",
                                   [fixed_inputs(graph, case)[binding.public_name]
                                    for case in range(INPUT_CASES)]))
        for binding in outs:
            lines.append(_constant(f"{graph}_out_{binding.tensor_index}",
                                   [reference_outputs(graph, case)[binding.public_name]
                                    for case in range(INPUT_CASES)]))
        input_sizes = [math.prod(binding.shape) for binding in ins] + [0] * (4 - len(ins))
        output_sizes = [math.prod(binding.shape) for binding in outs] + [0] * (2 - len(outs))
        input_rows = ["{" + ",".join(
            [f"{graph}_in_{binding.tensor_index}[{case}]" for binding in ins]
            + ["NULL"] * (4 - len(ins))) + "}" for case in range(3)]
        output_rows = ["{" + ",".join(
            [f"{graph}_out_{binding.tensor_index}[{case}]" for binding in outs]
            + ["NULL"] * (2 - len(outs))) + "}" for case in range(3)]
        initializers.append("{" + f"{entrypoint.entrypoint_symbol},{len(ins)}U,{len(outs)}U," +
                            "{" + ",".join(str(value) + "U" for value in input_sizes) + "}," +
                            "{" + ",".join(str(value) + "U" for value in output_sizes) + "}," +
                            "{" + ",".join(input_rows) + "},{" + ",".join(output_rows) + "}}")
    lines.append("static const struct tuc_case tuc_cases[2] = {" + ",".join(initializers) + "};")
    lines.append(_MAIN)
    return "\n".join(lines)


_MAIN = r'''
static void tuc_receipt(const char *status, const char *reason, const struct tuc_counts *counts) {
  printf("{\"schema_version\":\"tuc.bounded_c11_entrypoint_observation.v0\","
         "\"status\":\"%s\",\"reason\":\"%s\",\"binding_digest\":\"%s\",\"fault\":%d,"
         "\"case_runs\":%zu,\"entrypoint_calls\":%zu,\"scalar_checks\":%zu,"
         "\"published_outputs\":%zu,\"rejected_cases\":%zu,\"sentinel_checks\":%zu}\n",
         status, reason, TUC_ENTRYPOINT_BINDING, TUC_ENTRYPOINT_FAULT,
         counts->case_runs, counts->entrypoint_calls, counts->scalar_checks,
         counts->published_outputs, counts->rejected_cases, counts->sentinel_checks);
}
int main(int argc, char **argv) {
  (void)argv;
  struct tuc_counts counts = {0, 0, 0, 0, 0, 0};
  if (argc != 1) { tuc_receipt("ERROR", "invalid_invocation", &counts); return 2; }
  (void)alarm(20U);
  const unsigned int csr = _mm_getcsr();
  if (fegetround() != FE_TONEAREST || (csr & UINT32_C(0xe040)) != 0U ||
      (csr & UINT32_C(0x1f80)) != UINT32_C(0x1f80) ||
      getuid() != 10001U || geteuid() != 10001U || getgid() != 10001U || getegid() != 10001U) {
    tuc_receipt("ERROR", "environment_error", &counts); return 2;
  }
  const char *const reasons[] = {"none", "numeric_mismatch", "status_mismatch",
                                "output_modified", "environment_error"};
  for (size_t graph = 0; graph < 2U; ++graph) {
    for (size_t vector = 0; vector < 3U; ++vector) {
      for (size_t replay = 0; replay < 2U; ++replay) {
        int result = tuc_positive(&tuc_cases[graph], vector, &counts);
        if (result != 0) { tuc_receipt("ERROR", reasons[result], &counts); return 1; }
        for (size_t control = 0; control < 34U; ++control) {
          if (graph == 1U && control == 12U) continue;
          result = tuc_negative(&tuc_cases[graph], vector, control, &counts);
          if (result != 0) { tuc_receipt("ERROR", reasons[result], &counts); return 1; }
        }
      }
    }
  }
  tuc_receipt("PASS", "none", &counts);
  return 0;
}
'''


def _binding_digest(files):
    # The copied client binds the worker generator; omitting rendered worker.c
    # avoids a hash cycle while including both graphs and all context inputs.
    return _digest(_json({name: value for name, value in files.items() if name != "worker.c"}))


def _validate_files(files):
    names = {f"{graph}-entrypoint.{suffix}" for graph in GRAPHS for suffix in ("c", "h", "json")}
    names.update((*SUPPORT_FILES, "entrypoint.h", "worker.c", "source-bindings.json",
                  "consumer.py", "wheel-sha256.txt"))
    if (type(files) is not dict or len(files) != len(names) or
            any(type(name) is not str for name in files) or set(files) != names or
            any(type(value) is not str or len(value.encode("utf-8")) > MAX_FILE_BYTES
                for value in files.values()) or
            sum(len(value.encode("utf-8")) for value in files.values()) > MAX_CONTEXT_BYTES):
        raise ValueError("fixed entrypoint context rejected")


def artifact_files():
    wheel = _wheel_digest(required=True)
    compiled = {graph: compile_graph(graph) for graph in GRAPHS}
    package = Path(tuc.__file__).resolve().parent
    client = _read_file(ROOT / "consumer.py")
    bindings = {
        "schema_version": "tuc.bounded_c11_entrypoint_bindings.v0",
        "consumer_digest": _digest(client), "wheel_digest": wheel,
        "package_sources": {name: _digest(_read_file(package / name)) for name in PACKAGE_FILES},
        "graphs": {},
    }
    files = {"consumer.py": client, "wheel-sha256.txt": wheel + "\n",
             "entrypoint.h": '#include "app-entrypoint.h"\n#include "tiny-entrypoint.h"\n'}
    for graph, (compilation, entrypoint) in compiled.items():
        for name, text in entrypoint.files().items():
            files[f"{graph}-{name}"] = text
        bindings["graphs"][graph] = {
            "source_intent_digest": compilation.source_intent_digest,
            "backend_bindings_digest": compilation.backend_bindings_digest,
            "entrypoint_symbol": entrypoint.entrypoint_symbol,
            "entrypoint_digests": {
                name: _digest(text) for name, text in entrypoint.files().items()
            },
            "inputs": [asdict(binding) for binding in compilation.input_bindings],
            "returns": [asdict(binding) for binding in compilation.output_bindings],
        }
    files.update({name: _read_file(ROOT / name) for name in SUPPORT_FILES})
    files["source-bindings.json"] = _json(bindings)
    files["worker.c"] = _worker(compiled, _binding_digest(files))
    _validate_files(files)
    return files


def _expected_from_files(files, fault=0, invalid=False):
    if (type(fault) is not int or not 0 <= fault <= 3 or type(invalid) is not bool or
            (invalid and fault != 0)):
        raise ValueError("fixed entrypoint receipt selector rejected")
    counts = ((12, 414, 42, 18, 402, 2412), (0, 1, 0, 0, 0, 0),
              (1, 2, 6, 2, 0, 0), (1, 2, 6, 2, 0, 5))[fault]
    reason = ("none", "numeric_mismatch", "status_mismatch", "output_modified")[fault]
    if invalid:
        reason, counts = "invalid_invocation", (0, 0, 0, 0, 0, 0)
    return {"schema_version": SCHEMA, "binding_digest": _binding_digest(files),
            "status": "ERROR" if fault or invalid else "PASS", "reason": reason, "fault": fault,
            **dict(zip(COUNTERS, counts, strict=True))}


def expected_receipt(fault=0, invalid=False):
    """Synthetic protocol expectation, never evidence of an executed worker."""
    return _expected_from_files(artifact_files(), fault, invalid)


def _exact(value, expected):
    if (type(value) is not dict or len(value) != len(expected) or
            any(type(key) is not str for key in value) or set(value) != set(expected) or
            any(type(value[key]) is not type(expected[key]) or value[key] != expected[key]
                for key in expected)):
        raise ValueError("fixed entrypoint receipt rejected")
    return value


def validate_receipt(value, fault=0, invalid=False):
    return _exact(value, expected_receipt(fault, invalid))


def report(files=None):
    files = artifact_files() if files is None else files
    _validate_files(files)
    bindings = json.loads(files["source-bindings.json"])
    return {"schema_version": "tuc.bounded_c11_entrypoint_candidate.v0", "status": "PASS",
            "wheel_digest": bindings["wheel_digest"], "binding_digest": _binding_digest(files),
            "context_digest": _digest(_json(files)), "graphs": bindings["graphs"],
            "input_cases": 3, "replays": 2, "control_names": list(CONTROL_NAMES),
            "expected_baseline": _expected_from_files(files),
            "native_execution_observed": False, "cuda_execution_observed": False,
            "normal_runtime_admission": False, "latency_ns": None, "energy_pj": None}


def emit_context():
    files = artifact_files()
    parent = ROOT / "tmp"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError("fixed entrypoint context parent rejected")
    parent.mkdir(exist_ok=True)
    if parent.resolve() != ROOT.resolve() / "tmp":
        raise ValueError("fixed entrypoint context path rejected")
    directory = Path(tempfile.mkdtemp(prefix="bounded-c11-entrypoint.", dir=parent))
    for name, text in files.items():
        with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return directory


def accept(directory):
    path = Path(directory)
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or
            not path.is_dir() or path.resolve().parent != ROOT.resolve() / "tmp" or
            re.fullmatch(r"bounded-c11-entrypoint\.[A-Za-z0-9_-]{8,16}", path.name) is None):
        raise ValueError("fixed entrypoint evidence path rejected")
    files = artifact_files()
    receipts = {f"{build}-{name}.json" for build in ("static", "sanitized")
                for name in ("proof", "fault1", "fault2", "fault3", "invalid")}
    images = {f"{build}-image-id.txt" for build in ("static", "sanitized")}
    actual = set()
    for item in path.iterdir():
        if len(actual) > len(files) + len(receipts) + len(images):
            raise ValueError("fixed entrypoint evidence count rejected")
        if item.is_symlink() or not item.is_file():
            raise ValueError("fixed entrypoint regular evidence required")
        actual.add(item.name)
    if actual - {"record.json"} != set(files) | receipts | images:
        raise ValueError("fixed entrypoint evidence coverage rejected")
    for name, text in files.items():
        if _read_file(path / name) != text:
            raise ValueError("fixed entrypoint context drift rejected")
    observations, image_ids = {}, {}
    for build in ("static", "sanitized"):
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if fault == 0 else f"fault{fault}"
            name = f"{build}-{suffix}.json"
            value = _receipt_json(_read_file(path / name, MAX_RECEIPT_BYTES))
            observations[name] = _exact(value, _expected_from_files(files, fault, invalid))
        image_id = _read_file(path / f"{build}-image-id.txt", 80).strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
            raise ValueError("fixed entrypoint image identity rejected")
        image_ids[build] = image_id
    result = {**report(files), "schema_version": "tuc.bounded_c11_entrypoint_record.v0",
              "native_execution_observed": True, "observation_scope": "two_fixed_cpu_entrypoints",
              "image_ids": image_ids, "observations": observations}
    if len(_json(result).encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("fixed entrypoint record budget rejected")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--emit", action="store_true")
    group.add_argument("--accept", type=Path)
    args = parser.parse_args(argv)
    try:
        text = str(emit_context()) if args.emit else _json(
            accept(args.accept) if args.accept is not None else report(),
        )
    except (OSError, ValueError):
        print("fixed C11 entrypoint conformance rejected", file=sys.stderr)
        return 1
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
