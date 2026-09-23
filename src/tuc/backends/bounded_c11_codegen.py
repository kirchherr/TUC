"""Private, bounded, name-free emission of checked C11 graph functions.

Only closed integer graph descriptors enter this module. It emits text and
does not compile, load, execute or admit the generated function to a runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from math import prod


@dataclass(frozen=True)
class C11OperationSpec:
    kind: str
    inputs: tuple[int, ...]
    output: int


@dataclass(frozen=True)
class C11GraphSpec:
    tensor_shapes: tuple[tuple[int, ...], ...]
    operations: tuple[C11OperationSpec, ...]
    input_tensors: tuple[int, ...]
    output_tensors: tuple[int, ...]


def _record(value: object, expected: type[C11GraphSpec] | type[C11OperationSpec]) -> None:
    if type(value) is not expected:
        raise ValueError("checked C11 descriptor rejected")
    state = object.__getattribute__(value, "__dict__")
    names = {field.name for field in fields(expected)}
    if (type(state) is not dict or len(state) != len(names) or
            any(type(key) is not str or len(key) > 32 for key in state) or
            set(state) != names):
        raise ValueError("checked C11 descriptor rejected")


def validate_spec(spec: C11GraphSpec) -> tuple[int, int]:
    """Check before indexing, iteration expansion, arithmetic or text emission."""
    _record(spec, C11GraphSpec)
    if (type(spec.tensor_shapes) is not tuple or not 2 <= len(spec.tensor_shapes) <= 24 or
            type(spec.operations) is not tuple or not 1 <= len(spec.operations) <= 8):
        raise ValueError("checked C11 graph budget rejected")
    for shape in spec.tensor_shapes:
        if (type(shape) is not tuple or len(shape) not in (1, 2) or
                any(type(d) is not int or not 1 <= d <= 64 for d in shape)):
            raise ValueError("checked C11 shape rejected")
    count = len(spec.tensor_shapes)

    def indices(value: object, minimum: int, maximum: int) -> None:
        if (type(value) is not tuple or not minimum <= len(value) <= maximum or
                any(type(i) is not int or not 0 <= i < count for i in value)):
            raise ValueError("checked C11 indices rejected")

    indices(spec.input_tensors, 1, 24)
    indices(spec.output_tensors, 1, 8)
    if (len(set(spec.input_tensors)) != len(spec.input_tensors) or
            len(set(spec.output_tensors)) != len(spec.output_tensors)):
        raise ValueError("checked C11 duplicate public binding")
    producers: set[int] = set()
    consumers: set[int] = set()
    work = 0
    for op in spec.operations:
        _record(op, C11OperationSpec)
        if type(op.kind) is not str or op.kind not in (
                "matmul", "matmul_rhs_transposed", "relu", "sum_axis1", "add", "add_row_bias",
                "mul", "softmax_axis1", "mul_scalar", "mul_row_scale"):
            raise ValueError("checked C11 operation rejected")
        arity = 2 if op.kind in (
            "matmul", "matmul_rhs_transposed", "add", "add_row_bias", "mul",
            "mul_scalar", "mul_row_scale") else 1
        indices(op.inputs, arity, arity)
        if (type(op.output) is not int or not 0 <= op.output < count or
                op.output in producers or op.output in op.inputs):
            raise ValueError("checked C11 producer rejected")
        first, out = spec.tensor_shapes[op.inputs[0]], spec.tensor_shapes[op.output]
        if op.kind in ("matmul", "matmul_rhs_transposed"):
            second = spec.tensor_shapes[op.inputs[1]]
            transposed = op.kind == "matmul_rhs_transposed"
            if (len(first) != 2 or len(second) != 2 or
                    first[1] != second[1 if transposed else 0] or
                    out != (first[0], second[0 if transposed else 1])):
                raise ValueError("checked C11 matmul rejected")
            work += 2 * first[0] * first[1] * out[1]
        elif op.kind in ("add", "add_row_bias", "mul"):
            second = spec.tensor_shapes[op.inputs[1]]
            valid = (first == second if op.kind in ("add", "mul") else
                     len(first) == 2 and second == (first[1],))
            if not valid or out != first:
                raise ValueError("checked C11 binary elementwise shape rejected")
            work += prod(first)
        elif op.kind == "relu":
            if first != out:
                raise ValueError("checked C11 relu rejected")
            work += prod(first)
        elif op.kind in ("mul_scalar", "mul_row_scale"):
            second = spec.tensor_shapes[op.inputs[1]]
            valid = (second == (1,) if op.kind == "mul_scalar" else
                     len(first) == 2 and second == (first[1],) and second != (1,))
            if first == second or not valid or out != first:
                raise ValueError("checked C11 scaling shape rejected")
            work += prod(first)
        elif op.kind == "softmax_axis1":
            if len(first) != 2 or out != first:
                raise ValueError("checked C11 softmax shape rejected")
            work += 5 * prod(first)
        else:
            if len(first) != 2 or out != (first[0],):
                raise ValueError("checked C11 sum rejected")
            work += prod(first)
        producers.add(op.output)
        consumers.update(op.inputs)
    if (set(spec.input_tensors) != consumers - producers or
            set(spec.output_tensors) != producers - consumers or
            producers | consumers != set(range(count))):
        raise ValueError("checked C11 public graph boundary rejected")
    ready = set(spec.input_tensors)
    for op in spec.operations:
        if not set(op.inputs).issubset(ready):
            raise ValueError("checked C11 forward operand rejected")
        ready.add(op.output)
    scratch = sum(prod(shape) * 4 for shape in spec.tensor_shapes)
    if scratch > 262144 or work > 1_000_000:
        raise ValueError("checked C11 resource budget rejected")
    return scratch, work


def _operation(spec: C11GraphSpec, index: int) -> list[str]:
    op = spec.operations[index]
    shape = spec.tensor_shapes[op.inputs[0]]
    out = spec.tensor_shapes[op.output]
    params = ", ".join([*(f"const float *a{i}" for i in range(len(op.inputs))), "float *out"])
    if op.kind == "softmax_axis1":
        rows, columns = shape
        return [f"static int tuc_op_{index}({params}) {{",
                f"  for (size_t row = 0; row < {rows}U; ++row) {{",
                f"    const size_t base = row * {columns}U;",
                "    if (!tuc_normal(&a0[base])) return 0;",
                "    float maximum = a0[base];",
                f"    for (size_t column = 1; column < {columns}U; ++column) {{",
                "      if (!tuc_normal(&a0[base + column])) return 0;",
                "      if (a0[base + column] > maximum) maximum = a0[base + column];",
                "    }", "    float sum = 0.0F;",
                f"    for (size_t column = 0; column < {columns}U; ++column) {{",
                "      volatile float rounded_shift = a0[base + column] - maximum;",
                "      const float shift = rounded_shift;",
                "      if (!tuc_normal(&shift)) return 0;",
                "      volatile float rounded_exp = expf(shift);",
                "      const float exponential = rounded_exp;",
                "      if (!tuc_normal(&exponential) || !(exponential > 0.0F)) return 0;",
                "      out[base + column] = exponential;",
                "      if (!tuc_add(sum, exponential, &sum)) return 0;", "    }",
                "    if (!tuc_normal(&sum) || !(sum > 0.0F)) return 0;",
                f"    for (size_t column = 0; column < {columns}U; ++column) {{",
                "      volatile float rounded_quotient = out[base + column] / sum;",
                "      const float quotient = rounded_quotient;",
                "      if (!tuc_normal(&quotient) || !(quotient > 0.0F)) return 0;",
                "      out[base + column] = quotient;", "    }", "  }",
                "  return 1;", "}", ""]
    lines = [f"static int tuc_op_{index}({params}) {{",
             f"  for (size_t i = 0; i < {prod(out)}U; ++i) {{"]
    if op.kind == "relu":
        lines += ["    if (!tuc_normal(&a0[i])) return 0;",
                  "    const float value = a0[i] < 0.0F ? 0.0F : a0[i];",
                  "    if (!tuc_normal(&value)) return 0;", "    out[i] = value;"]
    elif op.kind in ("add", "add_row_bias"):
        rhs = "i" if op.kind == "add" else f"i % {shape[1]}U"
        lines += [f"    if (!tuc_add(a0[i], a1[{rhs}], &out[i])) return 0;"]
    elif op.kind == "mul":
        lines += ["    if (!tuc_multiply(a0[i], a1[i], &out[i])) return 0;"]
    elif op.kind in ("mul_scalar", "mul_row_scale"):
        rhs = "0" if op.kind == "mul_scalar" else f"i % {shape[1]}U"
        lines += [f"    if (!tuc_multiply(a0[i], a1[{rhs}], &out[i])) return 0;"]
    else:
        lines += ["    float sum = 0.0F;", f"    for (size_t k = 0; k < {shape[1]}U; ++k) {{"]
        if op.kind in ("matmul", "matmul_rhs_transposed"):
            rhs = (f"(i % {out[1]}U) * {shape[1]}U + k"
                   if op.kind == "matmul_rhs_transposed" else
                   f"k * {out[1]}U + i % {out[1]}U")
            lines += ["      float product;",
                      f"      if (!tuc_multiply(a0[(i / {out[1]}U) * {shape[1]}U + k],",
                      f"                        a1[{rhs}],"
                      " &product)) return 0;",
                      "      if (!tuc_add(sum, product, &sum)) return 0;"]
        else:
            lines += [f"      if (!tuc_add(sum, a0[i * {shape[1]}U + k], &sum)) return 0;"]
        lines += ["    }", "    out[i] = sum;"]
    return [*lines, "  }", "  return 1;", "}", ""]


def emit_checked_graph(spec: C11GraphSpec, binding_digest: str) -> tuple[str, str, str]:
    """Return header, source and the unique exported symbol; never execute."""
    scratch, _ = validate_spec(spec)
    if (type(binding_digest) is not str or len(binding_digest) != 64 or
            re.fullmatch("[0-9a-f]{64}", binding_digest) is None):
        raise ValueError("checked C11 binding rejected")
    prefix = "TUC_C11_" + binding_digest.upper()
    symbol = "tuc_c11_" + binding_digest + "_run"
    signature = [f"enum tuc_c11_status {symbol}(",
                 "    const struct tuc_c11_input *inputs, size_t input_count,",
                 "    const struct tuc_c11_output *outputs, size_t output_count)"]
    header = [f"#ifndef {prefix}_H", f"#define {prefix}_H", "#include <stddef.h>",
              "#ifndef TUC_C11_ABI_V0", "#define TUC_C11_ABI_V0",
              "struct tuc_c11_input { const float *data; size_t elements; };",
              "struct tuc_c11_output { float *data; size_t elements; };",
              "enum tuc_c11_status { TUC_C11_OK = 0, TUC_C11_ARGUMENT = 1,",
              "  TUC_C11_NUMERIC = 2, TUC_C11_ENVIRONMENT = 3 };", "#endif",
              f"#define {prefix}_INPUT_COUNT {len(spec.input_tensors)}U",
              f"#define {prefix}_OUTPUT_COUNT {len(spec.output_tensors)}U",
              f"#define {prefix}_OPERATION_COUNT {len(spec.operations)}U",
              f"#define {prefix}_SCRATCH_BYTES {scratch}U"]
    for label, tensors in (("INPUT", spec.input_tensors), ("OUTPUT", spec.output_tensors)):
        for i, tensor in enumerate(tensors):
            header.append(
                f"#define {prefix}_{label}_{i}_ELEMENTS {prod(spec.tensor_shapes[tensor])}U")
    header += ["/* Caller supplies live, stable, correctly sized buffers and descriptors.",
               " * All buffers are pairwise disjoint and disjoint from both descriptor arrays.",
               " * Returned errors preserve output values; concurrent mutation is unsupported. */",
               "#ifdef __cplusplus", 'extern "C" {', "#endif", *signature[:-1],
               signature[-1] + ";", "#ifdef __cplusplus", "}", "#endif", "#endif", ""]
    source = ['#include "entrypoint.h"', "#include <stdint.h>", "#include <string.h>",
              "#include <float.h>", "#include <limits.h>", "#include <fenv.h>",
              "#include <xmmintrin.h>",
              *(["#include <math.h>"] if any(op.kind == "softmax_axis1"
                                            for op in spec.operations) else []),
              "#if !defined(__linux__) || !defined(__x86_64__) || !defined(__SSE2__)",
              '#error "checked C11 requires Linux x86-64 SSE2 flat-address ABI"', "#endif",
              "#ifdef __FAST_MATH__", '#error "checked C11 forbids fast math"', "#endif",
              '_Static_assert(CHAR_BIT == 8 && sizeof(float) == 4 && sizeof(uintptr_t) == 8,',
              '               "checked C11 requires binary32 and 64-bit addresses");',
              '_Static_assert(FLT_RADIX == 2 && FLT_MANT_DIG == 24 && FLT_MAX_EXP == 128 &&',
              '               FLT_MIN_EXP == -125 && FLT_EVAL_METHOD == 0, "binary32 required");',
              "/* Build: -std=c11 -fno-fast-math -ffp-contract=off -frounding-math. */", "",
              "static int tuc_normal(const float *value) {",
              "  uint32_t bits; memcpy(&bits, value, sizeof(bits));",
              "  const uint32_t magnitude = bits & UINT32_C(0x7fffffff);",
              "  const uint32_t exponent = magnitude & UINT32_C(0x7f800000);",
              "  return magnitude == 0U || (exponent != 0U && exponent != UINT32_C(0x7f800000));",
              "}", "",
              "struct tuc_range { uintptr_t first; uintptr_t last; };",
              "static int tuc_range_of(const void *data, size_t bytes, size_t alignment,",
              "                        struct tuc_range *range) {",
              "  const uintptr_t first = (uintptr_t)data;",
              "  if (data == NULL || bytes == 0U || first % alignment != 0U ||",
              "      first > UINTPTR_MAX - bytes) return 0;",
              "  range->first = first; range->last = first + bytes; return 1;",
              "}", "static int tuc_overlap(struct tuc_range a, struct tuc_range b) {",
              "  return a.first < b.last && b.first < a.last;", "}", ""]
    if any(op.kind not in ("relu", "mul", "mul_scalar", "mul_row_scale")
           for op in spec.operations):
        source += ["static int tuc_add(float left, float right, float *output) {",
                   "  if (!tuc_normal(&left) || !tuc_normal(&right)) return 0;",
                   "  volatile float rounded = left + right;", "  const float value = rounded;",
                   "  if (!tuc_normal(&value)) return 0;", "  *output = value; return 1;", "}", ""]
    if any(op.kind in ("matmul", "matmul_rhs_transposed", "mul", "mul_scalar", "mul_row_scale")
           for op in spec.operations):
        source += ["static int tuc_multiply(float left, float right, float *output) {",
                   "  if (!tuc_normal(&left) || !tuc_normal(&right)) return 0;",
                   "  volatile float rounded = left * right;", "  const float value = rounded;",
                   "  uint32_t lbits, rbits, bits;",
                   "  memcpy(&lbits, &left, sizeof(lbits)); memcpy(&rbits, &right, sizeof(rbits));",
                   "  memcpy(&bits, &value, sizeof(bits));",
                   "  if (!tuc_normal(&value) || ((bits & UINT32_C(0x7fffffff)) == 0U &&",
                   "      (lbits & UINT32_C(0x7fffffff)) != 0U &&",
                   "      (rbits & UINT32_C(0x7fffffff)) != 0U)) return 0;",
                   "  *output = value; return 1;", "}", ""]
    for index in range(len(spec.operations)):
        source += _operation(spec, index)
    ni, no = len(spec.input_tensors), len(spec.output_tensors)
    source += [*signature[:-1], signature[-1] + " {",
               f"  if (input_count != {ni}U || output_count != {no}U) return TUC_C11_ARGUMENT;",
               "  struct tuc_range input_desc, output_desc;",
               f"  if (!tuc_range_of(inputs, {ni}U * sizeof(*inputs),"
               " _Alignof(struct tuc_c11_input),",
               "                    &input_desc) ||",
               f"      !tuc_range_of(outputs, {no}U * sizeof(*outputs),"
               " _Alignof(struct tuc_c11_output),",
               "                    &output_desc) || tuc_overlap(input_desc, output_desc))",
               "    return TUC_C11_ARGUMENT;",
               f"  struct tuc_c11_input in[{ni}]; struct tuc_c11_output out[{no}];",
               "  memcpy(in, inputs, sizeof(in)); memcpy(out, outputs, sizeof(out));",
               f"  struct tuc_range ranges[{ni + no}];"]
    for label, tensors, offset in (("in", spec.input_tensors, 0), ("out", spec.output_tensors, ni)):
        for index, tensor in enumerate(tensors):
            elements = prod(spec.tensor_shapes[tensor])
            source += [f"  if ({label}[{index}].elements != {elements}U ||",
                       f"      !tuc_range_of({label}[{index}].data, {elements}U * sizeof(float),",
                       f"                    _Alignof(float), &ranges[{offset + index}]))",
                       "    return TUC_C11_ARGUMENT;"]
    source += [f"  for (size_t i = 0; i < {ni + no}U; ++i) {{",
               "    if (tuc_overlap(ranges[i], input_desc) || tuc_overlap(ranges[i], output_desc))",
               "      return TUC_C11_ARGUMENT;",
               "    for (size_t j = 0; j < i; ++j)",
               "      if (tuc_overlap(ranges[i], ranges[j])) return TUC_C11_ARGUMENT;", "  }",
               "  const unsigned int csr = _mm_getcsr();",
               "  if (fegetround() != FE_TONEAREST || (csr & 0xe040U) != 0U ||",
               "      (csr & 0x1f80U) != 0x1f80U) return TUC_C11_ENVIRONMENT;"]
    for index, shape in enumerate(spec.tensor_shapes):
        source.append(f"  float tensor_{index}[{prod(shape)}];")
    for index, tensor in enumerate(spec.input_tensors):
        source += [f"  for (size_t i = 0; i < {prod(spec.tensor_shapes[tensor])}U; ++i)",
                   f"    if (!tuc_normal(&in[{index}].data[i])) return TUC_C11_NUMERIC;",
                   f"  memcpy(tensor_{tensor}, in[{index}].data, sizeof(tensor_{tensor}));"]
    for index, op in enumerate(spec.operations):
        arguments = ", ".join(f"tensor_{tensor}" for tensor in (*op.inputs, op.output))
        source.append(f"  if (!tuc_op_{index}({arguments})) return TUC_C11_NUMERIC;")
    for tensor in spec.output_tensors:
        source += [f"  for (size_t i = 0; i < {prod(spec.tensor_shapes[tensor])}U; ++i)",
                   f"    if (!tuc_normal(&tensor_{tensor}[i])) return TUC_C11_NUMERIC;"]
    source.append("  /* All fallible checks precede the first publication. */")
    for index, tensor in enumerate(spec.output_tensors):
        source.append(f"  memcpy(out[{index}].data, tensor_{tensor}, sizeof(tensor_{tensor}));")
    source += ["  return TUC_C11_OK;", "}", ""]
    return "\n".join(header), "\n".join(source), symbol
