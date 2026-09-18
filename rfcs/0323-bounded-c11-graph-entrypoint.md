# RFC 0323: Bounded C11 Graph Entrypoint

Status: implemented slice under validation; owner review required.

## Problem and decision

RFC 0321 makes bounded compilation available to installed applications. RFC 0322
executes one such application, but its conformance client still constructs the C
dispatch and owned storage. An application author should not need to implement
that machinery for every CPU graph.

Add `tuc.compiler.bounded_c11.emit_bounded_c11_entrypoint(module, bindings,
compilation)`. It revalidates the complete bounded Source Intent compilation,
reconstructs trusted inputs, and emits a self-contained graph entrypoint for an
all-C11 plan. A separate backend emitter owns checked scalar arithmetic and C
source generation. No backend-to-compiler import or executable Python callback
is introduced. The old primitive generators, consumers and evidence stay intact.

## Artifact boundary

The frozen `BoundedC11Entrypoint` contains `header`, `source`, `manifest_json`
and `entrypoint_symbol`. Its `files()` returns fresh in-memory mappings named
`entrypoint.h`, `entrypoint.c` and `entrypoint.json`.
`validate_bounded_c11_entrypoint(module, bindings, compilation, artifact)`
reconstructs the expected artifact and compares bounded exact-type fields.

Only selected C11 operations, host slots and zero transfers are accepted.
Unused capabilities can remain digest-bound; they do not create executable
targets. Existing bounds remain: at most eight operations, 24 tensors,
dimensions 1–64, one million logical scalar steps, 256 KiB owned tensor storage,
64 KiB metadata and 256 KiB emitted artifact text. These arithmetic counts do
not claim native instruction count or include validation overhead.

The manifest binds original source, capabilities, HAC-IR, original artifacts,
ordered public I/O, checked source texts, storage and numeric policy. The exported
symbol and graph-specific header guards/macros derive from a full SHA-256 digest.
Common ABI declarations have one versioned guard. Internal helpers are static,
so different emitted graphs can be linked into one application without symbol
collisions. Identical graph artifacts still define the same external function.

## C ABI and caller obligations

The generated header declares two descriptor types:

```c
struct tuc_c11_input { const float *data; size_t elements; };
struct tuc_c11_output { float *data; size_t elements; };
```

The digest-named function takes the input descriptor array and its count, then
the output descriptor array and its count. Descriptor order follows the public
Python bindings exactly, including explicit return aliases. Counts and element
extents must be exact; there are no runtime shapes, names, strides, callbacks,
graph selectors or workspace parameters.

Closed statuses are `TUC_C11_OK`, `TUC_C11_ARGUMENT`, `TUC_C11_NUMERIC` and
`TUC_C11_ENVIRONMENT` with values zero through three respectively.

Before input reads, the function checks counts, null pointers, alignment, exact
extents and overflow-safe address ranges. It snapshots descriptors, rejects all
tensor data overlap (including input/input), all data overlapping either descriptor
array, and overlapping descriptor arrays. Input data is copied into bounded fixed local arrays.
No heap, variable-length arrays or shared global scratch are used.

Every operation and all result checks finish before output publication. If the
function returns an error, all caller output bytes remain unchanged. This is not
atomic publication to concurrent observers. The caller must supply live,
correctly allocated readable/writable storage and descriptor arrays and prevent
concurrent mutation. Integer address checks cannot prove pointer validity or
isolate malicious native callers. Pointer interval reasoning is limited to the
reviewed Linux x86-64 flat-address ABI.

## Numerical contract

The target requires binary32 evaluation, SSE2, round-to-nearest, disabled FTZ/DAZ,
masked SSE floating exceptions, no contraction, no fast-math and compilation with
`-frounding-math`. The function
checks the environment without changing it. Floating exception flags may be
raised by attempted arithmetic; they are not cleared or restored by this API.

Inputs and every separately rounded multiplication/addition must be finite
normal binary32 or zero. Classification uses integer bits copied with `memcpy`,
so a signaling NaN can reject before a floating evaluation. Checked helpers are
new emission; the earlier unchecked primitive text is unchanged. Checking only
the final tensor would miss a subnormal product hidden by a later normal sum.

The entrypoint additionally rejects a product rounded to zero when both operands
are nonzero. Products with a zero operand and exact cancellation to zero remain
valid. Signed zeros compare numerically equal. Overflow, non-finite values,
subnormal values and nonzero-product underflow return a numeric error before
any caller output is written. This is a checked narrow numeric contract, not a
guarantee for arbitrary FP32 programs or a tolerance/error-budget claim.

## Conformance and security

A new standalone installed-wheel client compiles the RFC 0321 application and
a second Matmul/Sum graph. Both emitted entrypoints are linked into one static
binary and one ASan/UBSan binary. The client calls the public graph ABI only;
it contains no per-operation dispatch. Independent scalar FP32 references
check three corpora and two replays for each graph.

The fixed negative suite tests arity, null pointers, extents, alignment, overlap,
descriptor overlap, address overflow, NaN/Inf/subnormal values, numeric overflow,
hidden subnormal products and additions, product underflow and unsuitable floating environments.
Every rejected call checks unchanged output sentinels. Three driver falsifications
test incorrect results, wrong statuses and modified sentinels; unexpected process
arguments reject before work. Native crashes and sanitizer errors cannot count
as expected failures.

The default Python client is inert. A separate explicit operator uses pinned,
offline container builds and non-root, read-only, no-network, no-mount bounded
execution. A compiled context digest binds every receipt to wheel, source,
artifacts and build/isolation scripts. Acceptance rejects stale receipts and
malformed/oversized metadata. No native parser or deserializer is introduced.

## Limits of acceptance

This artifact API does not compile, load or run its source, discover plugins,
register a runtime backend, contact dev001 or execute CUDA. The new fixed CPU
conformance exception does not transfer earlier GPU approvals or establish
ordinary native runtime admission, performance or independent reproduction.
Passing CI applies to its exact reviewed revision and closed native cases.
