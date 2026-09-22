# Fixed CPU Softmax native conformance

This installed-wheel client emits four fixed C11 programs: row Softmax, an
affine classifier, an unscaled attention calculation, and a composition with
Linear, Bias, ReLU, Mul, Softmax and row Sum. Independent scalar equations
provide two datasets per graph, each replayed twice per native build.

The consumer never launches native code. The explicit `operator.sh --c11`
builds and executes the generated context in the existing restricted Docker
environment, once statically and once with ASan/UBSan. Install the wheel and
copy this directory outside checkout, write its SHA256 in `wheel-sha256.txt`
as `sha256:<64 lowercase hex digits>`, then run:

```sh
python3 -I consumer.py
sh operator.sh --c11
```

Successful observations require 16 case runs, 124 entrypoint calls, 80 numerical
comparisons, 108 rejected calls and 544 unchanged output-sentinel comparisons
per build. Output comparisons use absolute tolerance `2e-6` plus relative
tolerance `2e-5`; direct probability outputs also require positive values at
most one and row mass within `8e-6` of one. These are fixed-corpus acceptance
criteria, not a proof of a universal numerical error bound or bit equality
between different math libraries.

All graphs test descriptor counts/extents, null/misaligned/wrapped pointers,
buffer/descriptor overlaps, NaN/infinity/subnormal inputs, rounding mode,
FTZ/DAZ and exception masks. The one-input Softmax graph omits input-input aliasing.
Only that graph applies the five dedicated arithmetic controls: overflowing
shift, subnormal exponential, exponential rounded to zero, subnormal shift,
and a normal exponential whose normalized quotient becomes subnormal.
Each returned error must preserve all caller output values.

Three faulty checkers must fail: a materially corrupted result, an accepted
invalid descriptor count, and a modified output on a rejected call. An invalid
operator invocation must also fail. Ten bounded observations bind exact source,
graph, installed package, wheel and image identities. `--accept` reconstructs
the entire context and requires complete, exact receipts. Inert candidates and
synthetic test receipts do not establish native execution.
