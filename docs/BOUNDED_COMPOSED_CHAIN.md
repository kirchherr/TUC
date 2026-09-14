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

Native runs have not yet been accepted for this source revision.
