# RFC 0310: Bounded Reduction FMA Variant

- Status: Implemented; native acceptance pending
- Scope: Paired fixed-corpus native experiment following RFC 0309

## Decision

Retain RFC 0309's inputs, rational-reference intervals and baseline code.
Add explicit FMA lowering of the same allowlisted Source Intent and run both
variants in each native worker. A distinct execution-policy artifact permits
FMA for this candidate only. Do not rewrite the no-FMA baseline contract or
claim its full policy is identical to the candidate's policy.

[Bounded FMA Variant](../docs/REDUCTION_FMA_VARIANT.md) contains the unchanged
bound's justification, operator procedure and limits. C11 uses `fmaf`; CUDA
uses `__fmaf_rn` and checks emitted SASS. Automatic contraction and fast math
remain disabled. No general source/IR/runtime admission is added.

## Acceptance

1. Both policies' independently structured exact-rational simulations agree
   with the unchanged intervals and predict observable output differences.
2. Actual C11 and physical sm86 CUDA pass paired ten-case execution plus
   replay: 44 generated calls and 726 scalar checks per target. Each policy's
   outputs match its own oracle and both fit the same error budget.
3. Six compiled negative controls fail, including `separate-as-fma`, which
   must fail the policy check despite staying within the numerical budget.
4. C11 passes ASan/UBSan. GPU SASS contains candidate FFMA but no baseline
   projection FFMA, and neither worker contains PTX fallback.
5. Data-only records bind source, corpus, both code variants, baseline
   contract, interval artifact, execution policy, program files and image.

## Security And Proof Impact

This inherits the explicit RFC 0309 native exception and budgets. No raw
runtime values, value hashes, handles, paths, host identities or timings are
serialized. Artifact hashes identify reviewed fixed fixtures, not private
runtime tensor contents. No untrusted dimensions or symbols reach codegen.
Strict bounded JSON and regular-file readers remain. Native code is isolated
with pinned images, no network/host mounts, non-root, read-only root, dropped
capabilities, no-new-privileges, seccomp and deadlines. CUDA uses one sm86
device and 1,856 bytes of tensor buffers, excluding context/host tables.
Host driver exposure and incomplete recovery from hangs remain residual risks.

Existing Objective Alpha proof IDs/versions, HAC-IR, runtime plans and traces
are unchanged. Prior evidence is not regenerated. Hosted CI executes the
C11 pair and only revalidates recorded GPU data. No credentials, publishing,
dependencies, services or other workloads change.

## Limits

Same-maintainer, fixed-corpus evidence; shared oracle risk; C11 library
semantics rather than a CPU instruction claim; no all-input equivalence,
cross-vendor support, production admission, performance or universal hardware
claim. Independent reproduction remains open.
