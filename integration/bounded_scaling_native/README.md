# Fixed CPU scaling native conformance

This installed-wheel client emits four fixed C11 programs: vector scaling by a
one-element tensor, matrix scaling by a feature vector, scaled dot-product
attention, and a classifier with affine feature calibration. Independent scalar
equations provide two datasets per graph, replayed twice per native build.

The consumer only generates and checks data. The explicit `operator.sh --c11`
builds and executes the context in restricted static and ASan/UBSan containers.
Install the wheel outside checkout, copy this directory, write its SHA256 as
`sha256:<64 lowercase hex digits>` in `wheel-sha256.txt`, then run:

```sh
python3 -I consumer.py
sh operator.sh --c11
```

Each build requires 16 case runs, 134 entrypoint calls, 92 scalar checks,
118 rejected calls and 677 unchanged-output comparisons. The two pure scaling
graphs require bitwise FP32 equality, including signed zero. Compositions with
Softmax use absolute tolerance `2e-6` plus relative tolerance `2e-5`; classifier
probabilities must be positive, at most one, and sum within `8e-6` of one per row.

All four graphs cover count, extent, pointer, overlap and FP-environment errors,
including short and long descriptors for the compact scaling tensor. Both pure
scaling graphs additionally cover overflow, a subnormal product and nonzero
operands rounding to zero, with the invalid value late in the input. Every
rejected call must leave all public outputs unchanged.

Three intentionally faulty checkers and an invalid invocation must fail in each
build. Ten observations bind installed source, wheel, generated context and image
identities. Inert candidates and synthetic tests do not establish native execution.
No masks, multi-head API, device admission or performance claim is made.

[CI run 35826990657](https://github.com/kirchherr/TUC/actions/runs/35826990657)
observed all ten records at `d09d325`, with the exact counts above in both builds.
The unchanged [receipt](../../docs/evidence/bounded-cpu-scaling-35826990657.json)
and [verification details](../../rfcs/0332-bounded-cpu-scaling.md#observed-execution)
retain the source, wheel, context and image bindings.
