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

## Accepted Observations

Native execution passed on 2026-09-17: the static C11 baseline and all eight
profiles in one physical sm86 matrix image each completed ten cases plus replay,
363 scalar checks and 256 rounding witnesses. The matrix totals 2904 scalar
checks, 132 CPU calls, 132 GPU calls and 220 explicit copies (110704 bytes).
All planned steps and copy counts match the observations. The table above is
per run; these totals cover eleven runs per profile.

Sixteen C11 and 128 matrix negative controls reject: seven numerical faults,
seven static schedule faults and missing publication per profile, missing
produced-value transfer on each GPU-using profile, and one unknown selector per
worker. Static faults reject before allocation or native calls. C11 also passes
ASan/UBSan. The sanitized native contract test accepts all eight schedules,
rejects four invalid selectors and rejects all 19840 single-bit mutations of
integer profile, buffer and event fields. Pointer/string corruption is not part
of this mutation corpus; these fields are compiled constants, not runtime input.

The [comparison](../tests/golden/proofs/native_placements_comparison.json) binds
the [C11 record](../tests/golden/proofs/native_placements_c11_record.json) and
the [matrix record](../tests/golden/proofs/native_placements_matrix_record.json).
Twenty-seven metadata-only evidence files include these records, two preflight
groups, eighteen bounded negative-control groups, two unknown-selector
observations, numeric and contract sanitizer observations, and the comparison.
Groups contain at most eight observations, preserving existing intake budgets.
No raw tensor data, device IDs, runtime handles or host paths are serialized.

Observed source commit: `c3ad4d576855bed0e99b7d3ad78f6e6fecd3f8ef`.
Transferred archive SHA-256:
`f0e29fb768b57ec8724deabf461a0e590a7abc3c0ff130ba291f932eebce4787`.
Both records bind the same reviewed program files, the unchanged core residency
planner and overrides, and the prior mixed experiment. Earlier records remain
unchanged. CI executes C11 and sanitizer controls and revalidates the recorded
matrix; it does not execute on a GPU.

The reviewed host used driver 595.84 and NVIDIA Container Toolkit 1.20.0.
The review checked the applicable [driver advisory](https://nvidia.custhelp.com/app/answers/detail/a_id/5821)
and [container advisory](https://nvidia.custhelp.com/app/answers/detail/a_id/5850).
This is not a claim that the host or GPU boundary is free of vulnerabilities.
No experiment containers remained running and GPU utilization/memory returned
to the pre-run baseline.

This is a same-maintainer experiment, not independent reproduction or hardware
attestation. General native admission, arbitrary inputs/programs, dynamic shapes,
other GPU architectures/vendors and performance remain open. See
[RFC 0315](../rfcs/0315-bounded-native-placement-matrix.md) for the security boundary.
The next bounded dimension is native fanout with immutable resident-copy reuse,
under a separately reviewed source/shape contract; no automatic optimization or
performance claim follows from this placement matrix.
