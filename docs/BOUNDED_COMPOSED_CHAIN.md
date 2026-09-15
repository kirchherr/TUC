# Bounded Composed Chain

This experiment asks whether a nonlinear three-stage computation keeps its
meaning on two real targets:

```text
restricted source -> Source Intent -> matmul -> ReLU -> sum(axis=1)
                                      C11 CPU / CUDA sm86 GPU
```

It matters where ReLU happens. Clamping each matrix product element before
summing differs from clamping the final row sum. The first test case distinguishes
these alternatives; seven deliberately faulty native programs test rejection.

The scope is one reviewed `(33,7) @ (7,5)` chain, ten fixed FP32 input recipes,
and one replay. Three separate function calls or kernel launches retain both
intermediates. An exact rational nonlinear reference supplies the error interval;
an independently rounded oracle checks sequential, non-FMA FP32 arithmetic.
This is not a performance benchmark or a general native backend.

## Reproduce

Pure verification, without native execution:

```sh
PYTHONPATH=.:src python3 examples/bounded_composed_chain.py
```

Explicit Linux operator execution from a reviewed checkout:

```sh
sh scripts/run_bounded_composed_chain.sh --c11
# Only after reviewing an idle sm86 GPU host and its driver/toolkit security:
sh scripts/run_bounded_composed_chain.sh --cuda-reviewed
```

Both scripts emit a private evidence directory. Compare its accepted records:

```sh
PYTHONPATH=.:src python3 examples/bounded_composed_chain.py \
  --compare CPU_EVIDENCE/record.json GPU_EVIDENCE/record.json
```

The Python command only checks metadata and regenerated artifacts. Do not
interpret a constructed metadata record as independent hardware evidence.

## Boundaries

The restricted source is parsed, never imported or executed. Existing prototype
runtime integration is tested separately using its float64 storage model. The
native emitter consumes the checked intent, not the core runtime partition plan.
No runtime registration, plugin loader, general source execution, dynamic shape,
FMA-enabled chain, or performance claim is introduced. RFC 0308-0310 artifacts
and accepted records are unchanged.

See [RFC 0311](../rfcs/0311-bounded-composed-chain.md) for the derivation, threat
model, limits, and acceptance criteria.

## Observations

On 2026-09-14 both the native Linux x86_64 C11 worker and a physical RTX 3060
sm86 CUDA worker passed all ten cases and replay. Each performed 33 generated
calls and 363 scalar checks. Exactly 256 outputs differ numerically from the
binary64 encoding of the exact reference; all satisfy the declared interval
and the separate-rounding oracle. Both targets rejected all seven controls
on the first case. C11 ASan/UBSan passed; CUDA SASS inspection passed.

The observed source commit is
`396a0d21dbfd013bc8b2c62b86e8bbfd42e87e0a`.
The transferred archive SHA-256 is
`ffdfb4bc75671bcf3858190e76e465202e9d0c0091627f16feb319353a82feb1`.
Subsequent acceptance changes only records, tests, CI, and documentation, not
the observed program files. Accepted artifacts in `tests/golden/proofs/`:

- `composed_chain_comparison.json` and two `composed_chain_TARGET_record.json`.
- Two zero-call preflights and `composed_chain_c11_sanitized.json`.
- Fourteen target-specific negative observations, including both ReLU mistakes.

The reviewed host had driver 595.84 and NVIDIA Container Toolkit 1.20.0.
These exceed the fixes in the reviewed [May driver bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5821)
and [June toolkit bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5850).
This check is dated, not a guarantee against other vulnerabilities. No compute
process was active before or after the experiment; GPU usage returned to its
baseline and no experiment container remained. No unrelated service was changed.

This is same-maintainer execution evidence. Independent reproduction and
other hardware vendors remain open. The next integration question is whether
the checked core plan can drive this same bounded native chain, rather than
the dedicated operator hard-coding its three dispatches. That requires a new
reviewed boundary; this experiment does not admit native code into `execute_graph`.
