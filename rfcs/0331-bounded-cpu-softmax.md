# RFC 0331: Bounded CPU row Softmax

Status: implementation in progress; actual installed/static/sanitizer execution,
final CI and owner review are required before acceptance.

## Problem and decision

The supported source parser and neutral IR already express Softmax, but the
bounded native CPU path rejects it. This prevents a Linear classifier from
returning probabilities and prevents Matmul-based attention compositions.
Add one existing operation family to the explicit bounded CPU application path:
rank-two FP32 Softmax over axis 1, preserving the input shape.

This slice completes `Linear -> Bias -> Softmax` and
`Q @ K.T -> Softmax -> probabilities @ V`. The second expression is an unscaled,
unmasked attention calculation, not a complete Transformer layer. Existing
source parsing stays in its fixed isolated worker; no new source syntax,
framework loader, dependency or host evaluation is introduced.

## Typed boundary and lowering

Source Intent uses `family="softmax"`, exactly one input and fresh output,
equal rank-two shapes and the sole attribute `axis=1`. Axis must be an exact
integer; booleans, other axes, missing axes, extra attributes and shape/rank
mismatches reject. Existing dimensions 1-64, eight operations, 24 tensors,
1,000,000 logical scalar work units and 256 KiB tensor storage remain.
Softmax accounts for five logical work units per element: maximum scan, shift,
exponential, sum and division. This is resource accounting, not a timing model.

HAC-IR retains the hardware-neutral `SOFTMAX` kind. Capability selection must
explicitly support it. A new CPU-only artifact emitter normalizes the operation
to `softmax_axis1`, opcode 7, under `tuc.bounded_softmax_dag_artifacts.v0`.
It composes existing Matmul, right-transposed Matmul, Add/Bias, Mul, ReLU and
row Sum. Selected CUDA or heterogeneous execution rejects for this extension.
Older emitters and their byte-bound historical evidence remain unchanged.

The installed CLI adds SOFTMAX to its fixed CPU descriptor only for a validated
graph containing Softmax. Existing graph descriptors, program identities and
generated entrypoints therefore remain unchanged. Public Python callers select
an explicit declarative capability; no plugins or executable capabilities load.

## Numerical contract

Each row is evaluated as follows in the existing FE_TONEAREST/SSE2 environment:

1. Initialize the maximum from the first element and scan left to right with
   strict `>` comparisons. Inputs must be normal binary32 values or signed zero.
2. Subtract that maximum from each input with one rounded binary32 subtraction.
   Reject a nonfinite or subnormal result; exact zero is allowed.
3. Apply the pinned platform's C `expf`, store its binary32 result and require
   a strictly positive normal value. Zero and subnormal exponentials reject.
4. Sum exponentials left to right, starting from positive zero, with the
   existing checked binary32 addition. Require a positive normal denominator.
5. Divide each exponential by that denominator with one rounded binary32
   division. Require a strictly positive normal quotient.

No FMA, reassociation, clipping, silent underflow or alternate execution fallback
is introduced. Large equal logits can succeed because the maximum is subtracted.
Opposite finite extremes can overflow the subtraction and reject. Very small
probabilities can produce a subnormal exponential or quotient and reject even
though their input values were valid. This is a bounded numerical domain.

Unlike existing arithmetic-only examples, Softmax results are not promised to
be bit-identical across math libraries. `expf` uses the existing pinned GCC/glibc
build environment. Fixed-corpus conformance compares independent, separately
rounded reference equations using `abs(actual-reference) <= 2e-6 + 2e-5*abs(reference)`.
Direct probability outputs must be positive, at most one, and have row sums
within `8e-6` of one. These are declared acceptance criteria for the tested
corpus, not a proven global error bound or full Triton/PyTorch equivalence.
Subsequent Matmul can amplify numerical differences; composed examples receive
their own full-output comparisons.

Only Softmax-containing entrypoints add `<math.h>` and Softmax policy metadata.
The existing application build already links `-lm`; Dockerfiles, runtime
permissions and the binary protocol require no change. All intermediates remain
owned scratch. A returned error preserves every public output under the existing
live-buffer/no-concurrent-mutation ABI preconditions. Publication is sequential,
not a concurrent transaction. Floating-point exception flags are not preserved.

## Validation and security

The new surfaces are capability/graph admission and generated exponential/division
arithmetic. Typed validation must precede indexing and emission. Tests cover
malformed ranks, axes, metadata, object hooks, aliases, unsupported targets and
resource budgets. Old graph fingerprints must stay fixed, including all six
programs in RFC 0330's retained installed receipt.

A separate standard-library CLI consumer converts six fixed source programs
and evaluates two datasets per program, plus one three-request shared-weight
batch. It owns its equations and checks public bindings, identities, finite
outputs and row mass. Static source/JSON controls and numeric controls reject
with closed diagnostics, empty stdout, preserved files and clean workspaces.

A separate native harness links four graph entrypoints and checks two datasets
with two replays. Static and ASan/UBSan builds each cover 16 successful runs,
80 scalar comparisons, 108 rejected calls and 544 unchanged output comparisons.
Five dedicated arithmetic errors include a normal exponential whose quotient
becomes subnormal. Three intentionally faulty checkers and invalid invocations
must fail. Existing frame-parser/sanitizer suites remain regression requirements.

CI uses pinned read-only actions, existing hash-locked dependencies and offline
wheel builds. Installed clients run outside checkout and preserve original
observations bound to source, wheel, consumers, contexts and image identities.
Synthetic candidates are not native observations. No GPU, production admission,
general model, performance or public release claim is made.

## References

- [Triton's Softmax tutorial](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html)
  describes maximum subtraction and an approximate exponential. TUC uses its
  own explicit bounded CPU contract rather than promising identical GPU results.
- [GNU C Library numerical accuracy](https://sourceware.org/glibc/manual/latest/html_node/Errors-in-Math-Functions.html)
  motivates explicit comparison tolerances and avoiding cross-library bitwise claims.
- [RFC 0329](0329-bounded-cpu-gating.md) and [RFC 0330](0330-bounded-cpu-batch.md)
  supply the composed arithmetic and batch lifecycle used by this slice.
