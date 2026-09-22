"""Installed fixed Softmax C11 conformance; generation never launches native code."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import tempfile
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import tuc
from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import emit_bounded_c11_entrypoint
from tuc.compiler.bounded_source import BoundedBackendBinding, compile_bounded_source_intent
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

ROOT = Path(__file__).resolve().parent
GRAPHS = ("softmax", "classifier", "attention", "mixed")
SUPPORT_FILES = ("Dockerfile", "Dockerfile.dockerignore", "build.sh", "operator.sh")
PACKAGE_FILES = (
    "backends/bounded_softmax_dag.py", "backends/bounded_mul_dag.py",
    "backends/bounded_linear_dag.py",
    "backends/bounded_add_dag.py",
    "backends/bounded_c11_codegen.py",
    "compiler/bounded_c11.py", "compiler/bounded_source.py", "compiler/pipeline.py",
    "compiler/lowering.py", "compiler/movement.py", "compiler/decisions.py",
    "backends/base.py", "backends/bounded_dag.py", "backends/bounded_dag_codegen.py",
    "frontend/source_intent.py", "frontend/source_intent_metadata.py",
    "frontend/source_intent_returns.py", "frontend/triton_metadata.py", "frontend/hints.py",
    "ir/model.py", "ir/modules.py", "ir/dialect.py", "ir/dump.py", "ir/memory.py",
    "runtime/partitioning.py", "runtime/plan.py", "runtime/residency.py",
)
CONTROLS = (
    "input_count", "output_count", "null_input_descriptors", "null_output_descriptors",
    "null_input", "null_output", "short_input", "long_input", "short_output", "long_output",
    "input_output_alias", "input_input_alias", "input_descriptor_alias", "output_descriptor_alias",
    "misaligned_input", "misaligned_output", "wrapped_input", "nan_input", "infinite_input",
    "subnormal_input", "overflow_shift", "subnormal_exp", "rounding_mode",
    "flush_to_zero", "denormals_are_zero", "unmasked_exception", "huge_input_count",
    "huge_output_count", "nonzero_exp_rounding_to_zero", "subnormal_shift", "subnormal_quotient",
)
COUNTERS = ("case_runs", "entrypoint_calls", "scalar_checks", "published_outputs",
            "rejected_cases", "sentinel_checks")
SCHEMA = "tuc.bounded_softmax_native_observation.v0"
MAX_FILE_BYTES = 262144
MAX_CONTEXT_BYTES = 2097152
MAX_RECEIPT_BYTES = 8192


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def _digest(text):
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _read(path, limit=MAX_FILE_BYTES):
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or
            not path.is_file() or path.stat().st_size > limit):
        raise ValueError("fixed Softmax conformance file rejected")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("fixed Softmax conformance file budget rejected")
    return data.decode("utf-8", errors="strict")


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def module(graph):
    if graph not in GRAPHS:
        raise ValueError("fixed Softmax graph rejected")
    linear = {"rhs_transposed": True}
    softmax = {"axis": 1}
    if graph == "softmax":
        shapes = (("x", (2, 3)), ("result", (2, 3)))
        operations = (SourceIntentOperation("normalize", "softmax", ("x",), ("result",),
                                             attributes=softmax),)
    elif graph == "classifier":
        shapes = (("x", (2, 3)), ("weight", (4, 3)), ("bias", (4,)),
                  ("linear", (2, 4)), ("logits", (2, 4)), ("result", (2, 4)))
        operations = (
            SourceIntentOperation("project", "matmul", ("x", "weight"), ("linear",),
                                  attributes=linear),
            SourceIntentOperation("bias", "elementwise", ("linear", "bias"), ("logits",),
                                  attributes={"elementwise_kind": "add"}),
            SourceIntentOperation("normalize", "softmax", ("logits",), ("result",),
                                  attributes=softmax),
        )
    elif graph == "attention":
        shapes = (("q", (2, 3)), ("k", (4, 3)), ("v", (4, 2)),
                  ("logits", (2, 4)), ("probabilities", (2, 4)), ("result", (2, 2)))
        operations = (
            SourceIntentOperation("similarity", "matmul", ("q", "k"), ("logits",),
                                  attributes=linear),
            SourceIntentOperation("normalize", "softmax", ("logits",), ("probabilities",),
                                  attributes=softmax),
            SourceIntentOperation("weighted", "matmul", ("probabilities", "v"), ("result",)),
        )
    else:
        shapes = (("x", (2, 2)), ("weight", (2, 2)), ("bias", (2,)), ("scale", (2, 2)),
                  ("linear", (2, 2)), ("biased", (2, 2)), ("relu", (2, 2)),
                  ("product", (2, 2)), ("probabilities", (2, 2)), ("result", (2,)))
        operations = (
            SourceIntentOperation("project", "matmul", ("x", "weight"), ("linear",),
                                  attributes=linear),
            SourceIntentOperation("bias", "elementwise", ("linear", "bias"), ("biased",),
                                  attributes={"elementwise_kind": "add"}),
            SourceIntentOperation("activate", "elementwise", ("biased",), ("relu",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("multiply", "elementwise", ("relu", "scale"), ("product",),
                                  attributes={"elementwise_kind": "mul"}),
            SourceIntentOperation("normalize", "softmax", ("product",), ("probabilities",),
                                  attributes=softmax),
            SourceIntentOperation("sum", "reduction", ("probabilities",), ("result",),
                                  attributes={"axis": 1}),
        )
    return SourceIntentModule("native_softmax_" + graph, tuple(
        SourceIntentTensor(name, shape) for name, shape in shapes), operations,
        returns=(SourceIntentReturn("scores", "result"),))


def fixed_inputs(graph, case):
    if graph not in GRAPHS or type(case) is not int or case not in range(2):
        raise ValueError("fixed Softmax input selector rejected")
    sizes = ({"x": 6} if graph == "softmax" else
             {"x": 6, "weight": 12, "bias": 4} if graph == "classifier" else
             {"q": 6, "k": 12, "v": 8} if graph == "attention" else
             {"x": 4, "weight": 4, "bias": 2, "scale": 4})
    values = {name: tuple(_f32(((i * (port + 2) + port) % 11 - 5) /
                              (8.0 if case == 0 else 7.0)) for i in range(size))
              for port, (name, size) in enumerate(sizes.items())}
    if graph == "softmax":
        values["x"] = ((1000.0, 1000.0, 1000.0, -0.0, 0.0, 0.0) if case == 0 else
                       (80.0, 79.0, 78.0, -80.0, -79.0, -78.0))
    return values


def reference_outputs(graph, case):
    """Ordered scalar equations; libm output is compared with explicit tolerances."""
    values = fixed_inputs(graph, case)

    def linear(x, w, m, k, n):
        result = []
        for row in range(m):
            for col in range(n):
                total = 0.0
                for inner in range(k):
                    total = _f32(total + _f32(x[row*k+inner] * w[col*k+inner]))
                result.append(total)
        return result

    def softmax(x, width):
        result = []
        for start in range(0, len(x), width):
            row = x[start:start+width]
            top = max(row)
            exponentials = [_f32(math.exp(_f32(item-top))) for item in row]
            total = 0.0
            for item in exponentials:
                total = _f32(total + item)
            result.extend(_f32(item/total) for item in exponentials)
        return result

    if graph == "softmax":
        result = softmax(values["x"], 3)
    elif graph == "classifier":
        logits = linear(values["x"], values["weight"], 2, 3, 4)
        result = softmax([_f32(item + values["bias"][i % 4])
                          for i, item in enumerate(logits)], 4)
    elif graph == "attention":
        probabilities = softmax(linear(values["q"], values["k"], 2, 3, 4), 4)
        # Transpose only the independently declared V input for the scalar helper.
        transposed = [values["v"][row*2+col] for col in range(2) for row in range(4)]
        result = linear(probabilities, transposed, 2, 4, 2)
    else:
        logits = linear(values["x"], values["weight"], 2, 2, 2)
        logits = [_f32(item + values["bias"][i % 2]) for i, item in enumerate(logits)]
        logits = [_f32(max(0.0, item) * values["scale"][i]) for i, item in enumerate(logits)]
        normalized = softmax(logits, 2)
        result = [_f32(_f32(0.0 + normalized[i]) + normalized[i+1]) for i in (0, 2)]
    return {"scores": tuple(result)}


def compile_graph(graph):
    binding = BoundedBackendBinding(BackendCapability("fixed_cpu", frozenset({
        OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION,
        OperationKind.SOFTMAX}), memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11)
    source = module(graph)
    compilation = compile_bounded_source_intent(source, (binding,))
    return compilation, emit_bounded_c11_entrypoint(source, (binding,), compilation)


_WORKER = r'''#define _POSIX_C_SOURCE 200809L
#include "entrypoint.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fenv.h>
#include <math.h>
#include <xmmintrin.h>
#ifndef TUC_SOFTMAX_FAULT
#define TUC_SOFTMAX_FAULT 0
#endif
#if TUC_SOFTMAX_FAULT < 0 || TUC_SOFTMAX_FAULT > 3
#error "invalid fixed Softmax conformance control"
#endif
typedef enum tuc_c11_status (*entrypoint_fn)(const struct tuc_c11_input *, size_t,
                                           const struct tuc_c11_output *, size_t);
struct fixture {
  entrypoint_fn run; size_t inputs, elements[7], output_elements;
  const uint32_t *data[2][7]; const uint32_t *expected[2];
};
struct counts {
  size_t case_runs, entrypoint_calls, scalar_checks, published_outputs;
  size_t rejected_cases, sentinel_checks;
};
static uint32_t bits(const float *value) {
  uint32_t result; memcpy(&result, value, sizeof(result)); return result;
}
static void put(float *value, uint32_t data) { memcpy(value, &data, sizeof(data)); }
static int isolated(void) {
  if (getuid()!=10001U || geteuid()!=10001U || getgid()!=10001U || getegid()!=10001U) return 0;
  FILE *status = fopen("/proc/self/status", "r"); if (status == NULL) return 0;
  char line[256]; int privs=0, seccomp=0, caps=0;
  while (fgets(line, sizeof(line), status) != NULL) {
    if (strcmp(line, "NoNewPrivs:\t1\n") == 0) privs=1;
    if (strcmp(line, "Seccomp:\t2\n") == 0) seccomp=1;
    if (strcmp(line, "CapEff:\t0000000000000000\n") == 0) caps=1;
  }
  const int okay = !ferror(status); if (fclose(status) != 0) return 0;
  return okay && privs && seccomp && caps;
}
'''

_RUNNER = r'''
static int exercise(size_t graph, size_t input_case, int control, struct counts *counts) {
  const struct fixture *fixture = &fixtures[graph];
  float data[7][14], original[7][14], output[10];
  struct tuc_c11_input inputs[7]; struct tuc_c11_output outputs[1];
  for (size_t p=0; p<7U; ++p)
    for (size_t i=0; i<14U; ++i) put(&data[p][i], UINT32_C(0x42f68000));
  for (size_t i=0; i<10U; ++i) put(&output[i], UINT32_C(0x42f68000));
  for (size_t p=0; p<fixture->inputs; ++p) {
    for (size_t i=0; i<fixture->elements[p]; ++i)
      put(&data[p][i+1U], fixture->data[input_case][p][i]);
    inputs[p] = (struct tuc_c11_input){&data[p][1], fixture->elements[p]};
  }
  outputs[0] = (struct tuc_c11_output){&output[1], fixture->output_elements};
  const struct tuc_c11_input *input_args = inputs;
  const struct tuc_c11_output *output_args = outputs;
  size_t input_count=fixture->inputs, output_count=1U;
  enum tuc_c11_status expected=TUC_C11_OK;
  const unsigned int original_csr=_mm_getcsr(); const int original_round=fegetround();
  if (control >= 0) {
    expected = (control >= 17 && control <= 21) || control>=28 ? TUC_C11_NUMERIC :
               control >= 22 && control <= 25 ? TUC_C11_ENVIRONMENT : TUC_C11_ARGUMENT;
    switch (control) {
      case 0: input_count=0; break;
      case 1: output_count=0; break;
      case 2: input_args=NULL; break;
      case 3: output_args=NULL; break;
      case 4: inputs[0].data=NULL; break;
      case 5: outputs[0].data=NULL; break;
      case 6: --inputs[0].elements; break;
      case 7: ++inputs[0].elements; break;
      case 8: --outputs[0].elements; break;
      case 9: ++outputs[0].elements; break;
      case 10: outputs[0].data=&data[0][1]; break;
      case 11: inputs[1].data=inputs[0].data; break;
      case 12: inputs[0].data=(const float *)inputs; break;
      case 13: outputs[0].data=(float *)outputs; break;
      case 14: inputs[0].data=(const float *)((const unsigned char *)inputs[0].data+1U); break;
      case 15: outputs[0].data=(float *)((unsigned char *)outputs[0].data+1U); break;
      case 16: inputs[0].data=(const float *)(uintptr_t)(UINTPTR_MAX-3U); break;
      case 17: put(&data[0][1], UINT32_C(0x7fa00001)); break;
      case 18: put(&data[0][1], UINT32_C(0x7f800000)); break;
      case 19: put(&data[0][1], UINT32_C(1)); break;
      case 20:
      case 21:
      case 28:
      case 29:
      case 30:
        for (size_t i=0; i<fixture->elements[0]; ++i) put(&data[0][i+1U], 0U);
        if (control==20) {
          put(&data[0][1], UINT32_C(0x7f7fffff));
          put(&data[0][2], UINT32_C(0xff7fffff));
        } else if (control==29) {
          for (size_t i=1; i<4U; ++i) put(&data[0][i], UINT32_C(0x00800000));
          put(&data[0][2], UINT32_C(0x00800001));
        } else {
          data[0][3] = control==21 ? -90.0F : control==28 ? -110.0F : -87.0F;
        }
        break;
      case 22: if (fesetround(FE_DOWNWARD)!=0) return 4; break;
      case 23: _mm_setcsr(original_csr | 0x8000U); break;
      case 24: _mm_setcsr(original_csr | 0x0040U); break;
      case 25: _mm_setcsr(original_csr & ~0x0080U); break;
      case 26: input_count=SIZE_MAX; break;
      case 27: output_count=SIZE_MAX; break;
      default: return 4;
    }
  }
  memcpy(original, data, sizeof(data));
  ++counts->entrypoint_calls;
  enum tuc_c11_status status=fixture->run(input_args,input_count,output_args,output_count);
  if (fesetround(original_round)!=0) return 4;
  _mm_setcsr(original_csr);
  if (TUC_SOFTMAX_FAULT==2 && graph==0U && control==0) status=TUC_C11_OK;
  if (status!=expected) return 2;
  if (memcmp(original,data,sizeof(data))!=0) return 3;
  if (bits(&output[0])!=UINT32_C(0x42f68000)) return 3;
  for (size_t i=fixture->output_elements+1U; i<10U; ++i)
    if (bits(&output[i])!=UINT32_C(0x42f68000)) return 3;
  if (control < 0) {
    if (TUC_SOFTMAX_FAULT==1) output[1] += 0.25F;
    for (size_t i=0; i<fixture->output_elements; ++i) {
      ++counts->scalar_checks;
      float expected_value; put(&expected_value, fixture->expected[input_case][i]);
      const double actual=(double)output[i+1U], reference=(double)expected_value;
      if (!isfinite(actual) || fabs(actual-reference) > 2e-6 + 2e-5*fabs(reference)) return 1;
    }
    if (graph < 2U) {
      const size_t width=graph==0U ? 3U : 4U;
      for (size_t row=0; row<2U; ++row) {
        double mass=0.0;
        for (size_t col=0; col<width; ++col) {
          const float value=output[row*width+col+1U];
          if (value<=0.0F || value>1.0F) return 1;
          mass+=(double)value;
        }
        if (fabs(mass-1.0)>8e-6) return 1;
      }
    }
    ++counts->case_runs; ++counts->published_outputs;
  } else {
    ++counts->rejected_cases;
    if (TUC_SOFTMAX_FAULT==3 && graph==0U && control==0) put(&output[1], 0U);
    for (size_t i=0; i<fixture->output_elements; ++i) {
      ++counts->sentinel_checks;
      if (bits(&output[i+1U])!=UINT32_C(0x42f68000)) return 3;
    }
  }
  return 0;
}
static void receipt(const char *status, const char *reason, const struct counts *counts) {
  printf("{\"schema_version\":\"tuc.bounded_softmax_native_observation.v0\","
         "\"binding_digest\":\"%s\",\"status\":\"%s\",\"reason\":\"%s\",\"fault\":%d,"
         "\"case_runs\":%zu,\"entrypoint_calls\":%zu,\"scalar_checks\":%zu,"
         "\"published_outputs\":%zu,\"rejected_cases\":%zu,\"sentinel_checks\":%zu}\n",
         TUC_SOFTMAX_BINDING,status,reason,TUC_SOFTMAX_FAULT,counts->case_runs,counts->entrypoint_calls,
         counts->scalar_checks,counts->published_outputs,counts->rejected_cases,counts->sentinel_checks);
}
int main(int argc, char **argv) {
  (void)argv; alarm(10U); struct counts counts={0};
  if (argc!=1) { receipt("ERROR","invalid_invocation",&counts); return 2; }
  if (!isolated() || fesetround(FE_TONEAREST)!=0) {
    receipt("ERROR","environment_mismatch",&counts); return 2;
  }
  _mm_setcsr((_mm_getcsr() | 0x1f80U) & ~0xe040U);
  int result=0;
  for (size_t graph=0; graph<4U && result==0; ++graph)
    for (size_t c=0; c<2U && result==0; ++c)
      for (size_t replay=0; replay<2U && result==0; ++replay)
        result=exercise(graph,c,-1,&counts);
  for (size_t graph=0; graph<4U && result==0; ++graph)
    for (int control=0; control<31 && result==0; ++control) {
      if (graph!=0U && (control==20 || control==21 || control>=28)) continue;
      if (graph==0U && control==11) continue; /* One public input has no input pair. */
      result=exercise(graph,0U,control,&counts);
    }
  const char *reasons[]={"none","numeric_mismatch","status_mismatch","output_modified",
                         "environment_mismatch"};
  receipt(result==0 ? "PASS" : "ERROR",reasons[result],&counts);
  if (fflush(stdout)!=0 || ferror(stdout)) return 2;
  return result==0 ? 0 : result==4 ? 2 : 1;
}
'''


def _worker(compiled, binding):
    lines = [_WORKER, '#define TUC_SOFTMAX_BINDING "' + binding + '"']
    table = []
    for graph in GRAPHS:
        compilation, artifact = compiled[graph]
        inputs = compilation.input_bindings
        if len(inputs) > 7 or len(compilation.output_bindings) != 1:
            raise ValueError("fixed Softmax graph arity changed")
        sizes = [len(fixed_inputs(graph, 0)[item.public_name]) for item in inputs]
        if max(sizes) > 12:
            raise ValueError("fixed Softmax input extent changed")
        output = compilation.output_bindings[0].public_name
        output_size = len(reference_outputs(graph, 0)[output])
        if not 1 <= output_size <= 8:
            raise ValueError("fixed Softmax output extent changed")
        cases, expected = [], []
        for case in range(2):
            names = []
            for port, item in enumerate(inputs):
                name = f"{graph}_case{case}_in{port}"
                values = fixed_inputs(graph, case)[item.public_name]
                encoded = [struct.unpack("<I", struct.pack("<f", v))[0] for v in values]
                lines.append(f"static const uint32_t {name}[]={{" +
                             ",".join(f"UINT32_C(0x{v:08x})" for v in encoded) + "};")
                names.append(name)
            cases.append("{" + ",".join(names + ["NULL"] * (7 - len(names))) + "}")
            name = f"{graph}_case{case}_expected"
            encoded = [struct.unpack("<I", struct.pack("<f", v))[0]
                       for v in reference_outputs(graph, case)[output]]
            lines.append(f"static const uint32_t {name}[]={{" +
                         ",".join(f"UINT32_C(0x{v:08x})" for v in encoded) + "};")
            expected.append(name)
        table.append("  {" + artifact.entrypoint_symbol + f",{len(inputs)}U," + "{" +
                     ",".join(f"{v}U" for v in sizes + [0] * (7 - len(sizes))) + "}," +
                     f"{output_size}U," + "{" + ",".join(cases) + "},{" +
                     ",".join(expected) + "}},")
    return "\n".join([*lines, "static const struct fixture fixtures[]={", *table, "};", _RUNNER])


def _binding(files):
    return _digest(_json({name: text for name, text in files.items() if name != "worker.c"}))


def artifact_files():
    wheel = _read(ROOT / "wheel-sha256.txt", 80).strip()
    if re.fullmatch(r"sha256:[0-9a-f]{64}", wheel) is None:
        raise ValueError("fixed Softmax wheel digest rejected")
    compiled = {graph: compile_graph(graph) for graph in GRAPHS}
    package = Path(tuc.__file__).resolve().parent
    files = {name: _read(ROOT / name) for name in (*SUPPORT_FILES, "consumer.py")}
    files["wheel-sha256.txt"] = wheel + "\n"
    files["entrypoint.h"] = "".join(f'#include "{graph}-entrypoint.h"\n' for graph in GRAPHS)
    bindings = {"schema_version": "tuc.bounded_softmax_native_bindings.v0",
                "wheel_digest": wheel,
                "package_sources": {name: _digest(_read(package / name)) for name in PACKAGE_FILES},
                "graphs": {}}
    for graph, (compilation, artifact) in compiled.items():
        for name, text in artifact.files().items():
            files[f"{graph}-{name}"] = text
        bindings["graphs"][graph] = {
            "source_intent_digest": compilation.source_intent_digest,
            "inputs": [asdict(item) for item in compilation.input_bindings],
            "outputs": [asdict(item) for item in compilation.output_bindings],
            "entrypoint_symbol": artifact.entrypoint_symbol,
        }
    files["source-bindings.json"] = _json(bindings)
    files["worker.c"] = _worker(compiled, _binding(files))
    if (any(len(text.encode()) > MAX_FILE_BYTES for text in files.values()) or
            sum(len(text.encode()) for text in files.values()) > MAX_CONTEXT_BYTES):
        raise ValueError("fixed Softmax context budget rejected")
    return files


def _expected(files, fault=0, invalid=False):
    if (type(fault) is not int or not 0 <= fault <= 3 or type(invalid) is not bool or
            (invalid and fault)):
        raise ValueError("fixed Softmax receipt selector rejected")
    counts = ((16, 124, 80, 16, 108, 544), (0, 1, 1, 0, 0, 0),
              (16, 17, 80, 16, 0, 0), (16, 17, 80, 16, 1, 1))[fault]
    reason = ("none", "numeric_mismatch", "status_mismatch", "output_modified")[fault]
    if invalid:
        reason, counts = "invalid_invocation", (0, 0, 0, 0, 0, 0)
    return {"schema_version": SCHEMA, "binding_digest": _binding(files), "fault": fault,
            "status": "ERROR" if fault or invalid else "PASS", "reason": reason,
            **dict(zip(COUNTERS, counts, strict=True))}


def expected_receipt(fault=0, invalid=False):
    return _expected(artifact_files(), fault, invalid)


def _receipt_json(text):
    if type(text) is not str or not 1 <= len(text.encode()) <= MAX_RECEIPT_BYTES:
        raise ValueError("fixed Softmax receipt size rejected")
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 4:
                raise ValueError("fixed Softmax receipt depth rejected")
        elif char in "]}":
            depth -= 1
    def reject(_):
        raise ValueError("fixed Softmax receipt number rejected")
    def integer(token):
        if len(token) > 9:
            reject(token)
        return int(token)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("fixed Softmax duplicate receipt key")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                      parse_float=reject, parse_constant=reject)


def _exact(value, expected):
    if (type(value) is not dict or set(value) != set(expected) or
            any(type(value[key]) is not type(expected[key]) or value[key] != expected[key]
                for key in expected)):
        raise ValueError("fixed Softmax receipt rejected")
    return value


def report(files=None):
    files = artifact_files() if files is None else files
    bindings = json.loads(files["source-bindings.json"])
    return {"schema_version": "tuc.bounded_softmax_native_candidate.v0", "status": "PASS",
            "binding_digest": _binding(files), "context_digest": _digest(_json(files)),
            "wheel_digest": bindings["wheel_digest"], "graphs": bindings["graphs"],
            "controls": list(CONTROLS), "control_exclusions": {
                "softmax": ["input_input_alias"],
                **{name: [CONTROLS[i] for i in (20, 21, 28, 29, 30)]
                   for name in GRAPHS if name != "softmax"}},
            "numerical_tolerance": {"absolute": 2e-6, "relative": 2e-5, "row_mass": 8e-6},
            "expected_baseline": _expected(files),
            "native_execution_observed": False, "cuda_execution_observed": False,
            "normal_runtime_admission": False, "latency_ns": None, "energy_pj": None}


def emit_context():
    files = artifact_files()
    parent = ROOT / "tmp"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError("fixed Softmax context parent rejected")
    parent.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="bounded-softmax-native.", dir=parent))
    for name, text in files.items():
        with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return directory


def accept(directory):
    path = Path(directory)
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or
            not path.is_dir() or path.resolve().parent != ROOT.resolve() / "tmp" or
            re.fullmatch(r"bounded-softmax-native\.[A-Za-z0-9_-]{8,16}", path.name) is None):
        raise ValueError("fixed Softmax evidence path rejected")
    files = artifact_files()
    receipts = {f"{build}-{name}.json" for build in ("static", "sanitized")
                for name in ("proof", "fault1", "fault2", "fault3", "invalid")}
    images = {f"{build}-image-id.txt" for build in ("static", "sanitized")}
    actual = set()
    for item in path.iterdir():
        if len(actual) > len(files) + len(receipts) + len(images):
            raise ValueError("fixed Softmax evidence count rejected")
        if item.is_symlink() or not item.is_file():
            raise ValueError("fixed Softmax regular evidence required")
        actual.add(item.name)
    if actual - {"record.json"} != set(files) | receipts | images:
        raise ValueError("fixed Softmax evidence coverage rejected")
    for name, text in files.items():
        if _read(path / name) != text:
            raise ValueError("fixed Softmax context changed")
    observations, image_ids = {}, {}
    for build in ("static", "sanitized"):
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if fault == 0 else f"fault{fault}"
            name = f"{build}-{suffix}.json"
            observations[name] = _exact(_receipt_json(_read(path / name, MAX_RECEIPT_BYTES)),
                                         _expected(files, fault, invalid))
        image = _read(path / f"{build}-image-id.txt", 80).strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
            raise ValueError("fixed Softmax image identity rejected")
        image_ids[build] = image
    return {**report(files), "schema_version": "tuc.bounded_softmax_native_record.v0",
            "native_execution_observed": True, "observation_scope": "four_fixed_softmax_cpu_graphs",
            "observations": observations, "image_ids": image_ids}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--emit", action="store_true")
    choices.add_argument("--accept", type=Path)
    args = parser.parse_args(argv)
    try:
        text = str(emit_context()) if args.emit else _json(
            accept(args.accept) if args.accept else report()).rstrip("\n")
        sys.stdout.write(text + "\n")
        return 0
    except (OSError, ValueError, TypeError, OverflowError):
        print("fixed Softmax conformance rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
