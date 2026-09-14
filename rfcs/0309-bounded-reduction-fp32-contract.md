# RFC 0309: Bounded Reduction FP32 Contract

- Status: Implemented; native acceptance pending
- Scope: Separate fixed-corpus native experiment following RFC 0308

## Decision

Keep the reviewed 33x7 times 7x5 lowering unchanged. Exercise actual FP32
rounding with ten fixed input cases plus replay and an a priori, per-output
absolute error budget. The complete contract and derivation are in
[Bounded FP32 Reduction Contract](../docs/REDUCTION_FP32_CONTRACT.md).

Use exact rational input recipes, integer ties-even binary32 conversion,
exact rational references and gamma13 * sum(abs(products)) bounds. Serialize
acceptance intervals inward to binary64. Native code rejects nonfinite and
out-of-interval outputs; it requires a nonzero rounding witness. Do not
equate two individually acceptable results with bitwise equality.

## Security And Proof Impact

No core IR, parser, planner or runtime API changes. No arbitrary input files,
plugins, imports or native execution in the pure verifier. Existing strict
bounded JSON and regular-file readers are reused. Artifact bytes, contract,
corpus, reused generated code, harnesses, image and operator procedure are
bound in records. Legacy records are not regenerated.

Native execution is the same explicit exception as RFC 0308: pinned images,
no build/run network, no host mounts, non-root, dropped capabilities,
no-new-privileges, seccomp and bounded processes/memory/deadlines. GPU access
remains a host-driver risk, one sm86 device, SASS-only, no JIT. Four tensor
buffers total 1,856 bytes; context and host tables are additional. No changes
to credentials, publishing, dependencies, host services or other workloads.

## Acceptance

1. Numerical tests independently check exact references, ties-even rounding,
   normal-range intermediates, cancellation and interval boundary rejection.
2. Both native targets pass zero-call preflight, ten cases plus replay and
   show rounding; C11 also passes ASan/UBSan.
3. Five compiled negative controls fail: missing sum, wrong stride, incomplete
   coverage, finite over-budget perturbation and infinity injection.
4. Strict data-only records compare against the same contract, with actual
   source provenance. Hosted CI executes C11 and only replays stored GPU data.

## Limitations

Same-maintainer observations, common oracle-table risk, finite fixed corpus,
no arbitrary FP32/shape support, no input-conversion accuracy guarantee,
signed-zero numerical equality only, no performance or production claim.
Objective Alpha proof identity and general admission gates stay unchanged.
An FMA-enabled implementation is a separate next experiment, not silently
enabled by this contract.
