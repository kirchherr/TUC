# Bounded Native Placement Matrix

RFC 0315 compares all eight CPU/GPU placements of the existing fixed Matmul ->
ReLU -> Sum graph. One matrix binary includes all schedules and unchanged C11
and CUDA arithmetic. A fixed profile identifier selects a compiled schedule;
it cannot supply code, a serialized plan, a device, a path or a command.

The compiler sees the same two full operation capabilities each time. Three
typed `require_backend` overrides select placement. Source intent, HAC-IR,
input corpus, interval oracle and ordered FP32 policy remain identical.
The core residency planner derives both boundary and intermediate copies.

| Profile | Matmul | ReLU | Sum | Planned copy bytes / run |
| --- | --- | --- | --- | ---: |
| ccc | CPU | CPU | CPU | 0 |
| ccg | CPU | CPU | GPU | 792 |
| cgc | CPU | GPU | CPU | 1320 |
| cgg | CPU | GPU | GPU | 792 |
| gcc | GPU | CPU | CPU | 1724 |
| gcg | GPU | CPU | GPU | 2516 |
| ggc | GPU | GPU | CPU | 1724 |
| ggg | GPU | GPU | GPU | 1196 |

These are explicit logical copy bytes, not measured bandwidth, total memory
traffic or a speed ranking. Less copying does not establish faster execution.
Core defaults and normal native admission remain unchanged. This does not add
general placement optimization or portable vendor-independent native code.

## Reproduce

```sh
PYTHONPATH=.:src python3 examples/bounded_native_placements.py
sh docker/native-placements/operator.sh --c11
# Only after an explicit security review of an idle sm86 host:
sh docker/native-placements/operator.sh --matrix-reviewed
PYTHONPATH=.:src python3 examples/bounded_native_placements.py \
  --compare CPU_EVIDENCE/record.json MATRIX_EVIDENCE/record.json
```

The first command is pure artifact verification. The matrix operator builds
once and invokes the same image and proof binary for all eight profiles. Each
invocation starts a fresh bounded worker; no cross-invocation buffer retention
or warm-context claim is made. Compiled wrong-code workers mutate both CPU and
GPU versions of an operation, so placement cannot bypass the negative control.

The C11 operator also runs a sanitized contract test for all eight schedules:
every individual bit in integer profile/slot/event fields is flipped and must
reject. This deterministic bounded mutation test is not coverage-guided fuzzing.

## Status

Native observations are pending. Acceptance requires the static C11 baseline,
eight matrix profiles with 2904 total scalar checks, identical mathematical
semantics, exact execution/copy counts, malformed-schedule and wrong-code
rejections, C11 ASan/UBSan and the native contract mutation test.

This is a same-maintainer experiment, not independent reproduction or hardware
attestation. General native admission, arbitrary inputs/programs, dynamic shapes,
other GPU architectures/vendors and performance remain open. See
[RFC 0315](../rfcs/0315-bounded-native-placement-matrix.md) for the security boundary.
