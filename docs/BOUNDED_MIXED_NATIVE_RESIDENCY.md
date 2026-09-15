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

Implementation and malformed-plan tests are present. Actual native acceptance
is pending. Previous observations are not reused as evidence for mixed execution.

See [RFC 0314](../rfcs/0314-bounded-mixed-native-residency.md) for resource limits,
native isolation requirements and acceptance criteria. Independent reproduction,
general native admission, arbitrary programs/inputs/shapes, multi-device execution
and performance remain unproven.
