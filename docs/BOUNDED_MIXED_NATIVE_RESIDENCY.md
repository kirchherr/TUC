# Bounded Mixed Native Residency

This experiment uses the new opt-in core residency planner for one fixed source
program, comparing all-C11 execution with a genuinely mixed native placement:

```text
host inputs -> GPU Matmul -> download projection -> CPU ReLU
            -> upload activation -> GPU Sum -> download and publish output
```

The planner consumes typed HAC-IR and the compiler's partition assignments.
It creates one ordered schedule for external bindings, copies, compute and
terminal publication. The worker consumes that schedule. It does not infer
residency from physical memory technology: separate named address spaces require
copies even when their physical memory kinds are identical or unknown.

## Reproduce

```sh
PYTHONPATH=.:src python3 examples/bounded_mixed_native.py
sh docker/mixed-native/operator.sh --c11
# Explicitly reviewed idle sm86 GPU host only:
sh docker/mixed-native/operator.sh --cuda-reviewed
PYTHONPATH=.:src python3 examples/bounded_mixed_native.py \
  --compare CPU_EVIDENCE/record.json MIXED_EVIDENCE/record.json
```

The first command verifies artifacts without native execution. The operator
builds and runs reviewed fixed code in bounded containers; no general runtime
registration, arbitrary native plan intake or JIT is introduced.

## Contract

Both placements share source intent, HAC-IR, generated arithmetic and the old
FP32 oracle: ten cases plus replay, 363 scalar checks. The expected mixed run
uses 22 GPU calls and 11 CPU calls. Its 33 uploads total 18964 bytes, and its
22 downloads total 8712 bytes. C11 requires 33 CPU calls and no copies.

These are explicit logical copy bytes, not total memory traffic, latency or
performance. The mixed schedule reserves 5032 logical tensor bytes across its
host and accelerator slots; C11 reserves 2516. Caller-owned inputs/output are
bound, not allocated. Buffers are not reused, and initialization, oracle storage,
CUDA context and driver memory are excluded from these logical storage figures.

Compiler partition estimates remain prototype estimates. The new residency
schedule uses explicit spaces and keeps performance claims absent. Core planning
supports immutable row-major fanout with cached resident copies, but this native
experiment admits only its exact three-operation graph and two placements.

## Validation Status

Native C11 and physical sm86 mixed CPU/GPU execution passed on 2026-09-15.
Each target completed ten cases plus replay, 33 generated calls, 363 scalar
checks and 256 rounding witnesses. C11 also passed ASan/UBSan.

| Observed completed work | All-C11 | GPU / CPU / GPU |
| --- | ---: | ---: |
| CPU calls | 33 | 11 |
| GPU calls | 0 | 22 |
| Schedule steps | 66 | 121 |
| Upload calls / bytes | 0 / 0 | 33 / 18964 |
| Download calls / bytes | 0 / 0 | 22 / 8712 |

Fourteen negative controls passed on C11 and fifteen on the mixed target. Six
malformed schedules reject before native calls or buffer allocation. Missing
publication fails after computation. Omitting the projection download fails
after the first GPU call, before the CPU consumer: no download and no CPU call
are reported. Seven numerical wrong-code controls also reject on both targets.

The [comparison](../tests/golden/proofs/mixed_native_comparison.json) binds the
[C11 record](../tests/golden/proofs/mixed_native_c11_record.json) and the
[mixed record](../tests/golden/proofs/mixed_native_mixed_record.json). Thirty-five
accepted artifacts include both preflights, C11 sanitizer execution and all
twenty-nine rejection observations. They contain no raw tensor values, device
IDs, runtime handles or host paths. The mixed numerical child explicitly names
`mixed` and binds both generated code digests. Both new numeric children use
`tuc.bounded_mixed_numeric_observation.v0`; the old chain observation schema is
not widened or reinterpreted. The FP32 mathematical and ordered evaluation
contracts are unchanged.

Observed final source commit: `354dd4aa7398c5398b6556d542b8aab006bbbfce`.
Transferred archive SHA-256:
`79ab6368c3ac33f97da288e7081f033631e036568b72a1399fc50c0d6dcfacc7`.
Both records bind the new program files, including the core residency planner,
and the unchanged previous I/O proof program. Previous observations were not
reused. These are same-maintainer observations, not hardware attestation.

The full core typecheck passes in a separate pinned, networkless execution
container. CI executes the C11 path and revalidates recorded mixed evidence;
it does not execute on a GPU. Existing default runtime behavior is unchanged.

The next useful dimension is another bounded mixed placement of the same graph,
chosen through reviewed capability/placement inputs and compared against this
same numerical oracle. Performance work remains separate from correctness.

See [RFC 0314](../rfcs/0314-bounded-mixed-native-residency.md) for resource limits,
native isolation requirements and acceptance criteria. Independent reproduction,
general native admission, arbitrary programs/inputs/shapes, multi-device execution
and performance remain unproven.
