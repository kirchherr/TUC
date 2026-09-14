# RFC 0308: Bounded Reduction Shapes

## Status

Implemented and natively observed on 2026-09-14; merge review pending.
Both C11 and physical sm86 CUDA passed all twenty cases plus replay and three
wrong-code controls. C11 also passed ASan/UBSan. The tested source identity
and actual observations are listed in `docs/BOUNDED_REDUCTION_SHAPES.md`.

## Decision

Lower the same inert Matmul-plus-axis-1-Sum source with a second reviewed shape:
A[33,7], B[7,5], projection[33,5], y[33]. A pure emitter admits exactly the
baseline and odd-shape Source Intent digests, validates typed semantics before
emission and preserves baseline C11/CUDA output bytes. No arbitrary shapes,
source execution or normal-runtime admission are added.

The odd-shape CUDA plan requires six 32-thread projection blocks and two
32-thread reduction blocks, with logical-item guards. Execute twenty bounded
quarter-integer vectors plus baseline replay per target. Allocate 1,856 tensor
bytes once and reuse buffers, poisoning logical outputs before each run so
incomplete coverage cannot pass through stale values.

Require separately compiled missing-sum, wrong-stride and incomplete-coverage
rejections on both targets. The incomplete CPU variant omits row 32; the GPU
variant launches only one block. C11 also requires ASan/UBSan. GPU coverage
poisoning is not a sanitizer or an out-of-bounds memory-safety proof.

## Security Exception And Limits

This remains a separate explicit native operator experiment using the controls
from RFCs 0306/0307: digest-pinned toolchains, no PTX/JIT, no network or host
mounts, read-only root, non-root user, no capabilities, no-new-privileges,
seccomp, bounded resources and deadlines. Device access still reaches trusted
host drivers. No new dependencies, plugins, source intake or core backend API.

Records bind source, emitted code, corpus and reviewed program files. They are
same-maintainer observations, not independently signed attestations. Metadata
validation can detect drift but cannot authenticate a dishonest operator.
Previous records and emitters remain unchanged. Shared native reference code
is checked against rational Python and NumPy references. Performance,
arbitrary FP32 values, dynamic shapes, cross-vendor support and production
readiness remain excluded.

See `docs/BOUNDED_REDUCTION_SHAPES.md` for reproduction and acceptance.
