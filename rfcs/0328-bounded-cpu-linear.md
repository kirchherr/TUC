# RFC 0328: Bounded CPU Linear with transposed right-hand weights

Status: implemented; installed/native execution observed at `b0085167` on
2026-09-21. Owner review and final-revision CI remain required for acceptance.

## Problem and decision

RFC 0327 supports affine and MLP graphs, but ordinary Matmul expects weights
in `[K,N]` order. Applications storing one output feature per weight row
currently have to reorder their values before supplying them to TUC. Introduce
an explicit hardware-neutral Matmul mode for `X[M,K] * W[N,K]^T -> Y[M,N]`.
Bias remains a separate existing Add; an affine layer is two operations and a
two-layer MLP remains five operations.

This layout matches the weight orientation documented for
[PyTorch Linear](https://docs.pytorch.org/docs/2.14/generated/torch.nn.Linear.html).
It does not introduce a PyTorch dependency, model loader, FX capture, autograd,
or numerical-parity claim against an unspecified external library.

## Semantic contract

Source Intent retains `family=matmul` and the existing MATMUL capability. The
optional attribute `rhs_transposed` is a canonical presence flag: its only
accepted value is exact boolean `true`; absence retains ordinary Matmul.
Explicit false, numbers, strings and other values reject. The attribute belongs
only to Matmul and carries unchanged into metadata, TLIR and HAC-IR.

The transposed mode requires two rank-two FP32 tensors, inner dimensions equal
at index one, and a fresh output with shape `[lhs[0],rhs[0]]`. Actual tensors
remain contiguous row-major data with their declared physical shapes. The flag
describes the mathematical operand interpretation, not a target layout request,
view, stride, alias or materialized transpose. Repeated input identity is valid.

The explicit isolated parser recognizes only
`p = tl.dot(x, tl.trans(weight))` as an additional source form. Both tensors
must be known names. `tl.trans` takes exactly one positional name and no keyword
arguments. Standalone/LHS transpose, arbitrary nested calls, double transpose,
indexing, member calls, `.T`, axis lists and additional dot options reject.
This narrow rank-two interpretation agrees with
[Triton's default trans operation](https://triton-lang.org/main/python-api/generated/triton.language.trans.html).
User source remains AST data within the existing isolated worker.

Existing dimensions 1-64, eight-operation/24-tensor bounds, mandatory terminal
returns, one-million scalar-work and storage/metadata/artifact budgets remain.
Work is `2*M*N*K`; movement reads the original operand extents and writes the
result. No intermediate transposed tensor is introduced.

## Lowering and numerical behavior

Graphs with this mode use a distinct `tuc.bounded_linear_dag_artifacts.v0`
manifest and normalized `matmul_rhs_transposed` operation. One selected C11 CPU
backend is required; CUDA/mixed placement rejects explicitly. New graphs can
combine transposed/ordinary Matmul with existing Add/Bias, ReLU and row-Sum.
The original DAG and Add emitters remain byte-identical; graphs without this
attribute retain their previous emission path and bytes.

Native evaluation visits `k` in ascending order, reads weights at
`column*K+k`, rounds the product and each accumulated sum separately to binary32,
and uses the existing checked multiplication/addition helpers. Contraction and
reassociation remain disabled. Finite normal-or-zero inputs, intermediates and
outputs are required; overflow/subnormal results reject before output
publication. Existing extent, alias, environment and cleanup guards continue.
The trusted simulator separately follows its existing FP64 reference policy.

## Validation and security

Pure boundary tests cover exact attribute ownership/type, rank/shape/SSA,
source syntax, work limits, physical binding shapes, repeated operands,
unsupported placement and changed artifacts. Nonsquare cases distinguish
correct transposed indexing from ordinary Matmul indexing; singleton dimensions
exercise boundary indexing. Existing graph, proof and emitted-source tests
protect the old paths.

An independent installed client owns affine, MLP and mixed-orientation source
graphs in two shape profiles, changing input/weight datasets, complete expected
graph documents and ordered FP32 references. It checks source/signature/input/
graph/program/request identities, unchanged originals, cleanup, exact negative
diagnostics and native overflow/subnormal rejection. A separate fixed native
harness runs static and ASan/UBSan builds over direct entrypoint descriptor,
count, extent, numeric, alias and environment cases, with poisoned outputs and
checker-fault controls. Pure protocol fixtures establish no native execution.

The new workflow is read-only, reuses existing pinned actions/images and
hash-locked dependencies, builds a wheel offline and installs outside checkout.
Actual observations bind source revision, wheel, consumers and generated
contexts. No new runtime command, dependency, dynamic loader, cache authority,
credential, publication, device or general admission is introduced.

Owner review and observed installed/native execution are required for acceptance.

## Observed execution

[CI run 35569935472](https://github.com/kirchherr/TUC/actions/runs/35569935472)
passed at `b0085167016242b30b6d4873d27d0e43f5c1677d`: 241 boundary/protocol tests,
an offline wheel installed outside checkout, six isolated source conversions,
twelve native CPU calls, 60 bitwise FP32 checks, ten source rejections and two
numeric rejections. Static and ASan/UBSan entrypoint builds each passed 16 runs,
132 calls, 56 scalar checks, 116 expected boundary rejections and 406 unchanged
output checks. The ten observations include three faulty checkers and invalid
invocation for each build.

The [original combined receipt](../docs/evidence/bounded-cpu-linear-35569935472.json)
is retained without reserialization. Its SHA256 is
`e000a22c89f04fcf8bcda18397b6a6c19d3c290074d790e81de2aeaa49759fdc`.
Artifact `10626015214` contained only `ci-record.json`; its ZIP SHA256
`52a4d6eb2d052c40d5e1a90ee5e5d2b23366260a8d82375dff0c51f7268f72c3`
matches the GitHub artifact metadata and upload log. The receipt binds both
consumer hashes, source revision and wheel SHA256
`274d3268d0e3325d3065389bb4fe2c04f249a15990fb9033946aaf930a4f641a`.
These observations cover the fixed CPU corpora only; they establish no GPU,
arbitrary-source, external-library parity or performance claim.

Independent local audits reproduced all six source/signature/graph/program
bindings, fourteen input/request digests, ten parser rejections and both numeric
controls. All 60 recorded CLI outputs match separately ordered NumPy FP32
calculations bit-for-bit. All 21 native context files (98,264 bytes), both
context/binding digests and ten observations also reproduce exactly. Eight
distinct native graph/dataset cases match independent FP32 arithmetic and the
emitted expectation bits; the workflow executes each twice per build. The
artifact contains no wheel or container images; these audits do not claim to
reinstall or rerun them.
