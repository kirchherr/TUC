# RFC 0329: Bounded CPU multiplication and ReLU-gated MLPs

Status: implemented; installed/native execution observed at `ce70446` on
2026-09-21. Final CI and owner review remain required for acceptance.

## Problem and decision

The bounded CPU interface can project, add and activate tensors, but cannot
combine two computed tensors by multiplying their corresponding elements.
Add exact-shape binary multiplication to the existing neutral elementwise
family. This makes a ReLU-gated MLP executable: two Linear branches produce a
value tensor and an activated gate, their product feeds an output projection.
The seven-operation graph fits the existing budget; output bias adds an eighth.

The operation uses `family=elementwise`, `elementwise_kind=mul`, the existing
ELEMENTWISE capability and metadata/HAC `kernel=mul`. No new operation enum,
backend hook, implicit fusion or target-specific semantic attribute is needed.

## Contract and frontend boundary

Inputs and output are FP32 rank-one or rank-two tensors with identical shapes.
There are exactly two operands and one fresh output. Repeated input identity
(`x*x`) is valid and has one public input binding. Shapes may not broadcast,
including singleton dimensions or a right-hand row vector. No scalar operand,
dtype promotion or arbitrary stride/view is introduced. Work is one multiply
per output element; movement reads the original operands and writes the result.

Source syntax is one assignment `product = left * right`, with both operands
known tensor names. Nested expressions, indexing, member calls, `tl.mul`,
scalars, division, powers and augmented assignment reject. Separate assignments
remain explicit graph nodes. The isolated parser treats user source as AST data
and preserves its existing import closure, protocols and budgets.

The bounded rule is deliberately narrower than the broader promotion and
broadcasting semantics documented by
[Triton](https://triton-lang.org/main/python-api/triton-semantics.html).
This is a supported symbolic source subset, not general Triton compatibility.
The sample is a ReLU-gated MLP; it claims neither GLU/SwiGLU nor framework model
loading, training or autograd support.

## Lowering and numerical behavior

Mul-containing graphs select `tuc.bounded_mul_dag_artifacts.v0`, normalized
`mul` opcode 6, and one selected C11 CPU backend. They compose ordinary and
right-transposed Matmul, Add/Bias, ReLU and row-Sum. Mul takes precedence over
Linear/Add when selecting the artifact path. The four historical DAG modules
and all non-Mul graph emission paths remain unchanged.

Validation reuses hardened record, metadata, partition and existing operation
checks only after proving their typed bounded preconditions. Mul is validated
and emitted explicitly; it is never disguised as another operation. No callback
or external extension authority is introduced. Existing eight-operation,
24-tensor, dimension 1-64 and work/storage/artifact bounds remain.

Each native output element uses one existing checked binary32 multiplication.
Normal-or-zero inputs and rounded results, round-to-nearest ties-to-even,
disabled FTZ/DAZ and masked exceptions remain required. Overflow, subnormal
results and a nonzero product rounded to zero reject. Signed zero is preserved.
Returned validation or evaluation errors leave every output unchanged. Successful
evaluation publishes outputs through sequential copies, not a concurrent transaction.
The trusted simulator follows its separate existing FP64 reference policy.

## Security and validation

Attacker-controlled source, JSON, tensor descriptions and numeric values enter
the existing bounded data boundaries. New tests cover operation ownership,
exact arity/type/shape/dtype, repeated operands, unsupported broadcasting,
oversized dimensions, target rejection and altered artifacts. Pure Mul graphs
also test code generation without relying on a Matmul to emit numeric helpers.

An independent installed consumer owns vector products, repeated-input matrix
squares and seven/eight-operation gated MLPs in two shape profiles, with changing
data. It checks complete graphs, bindings, source/signature/input/program/request
identities, separately rounded FP32 results including signed zero, original file
preservation, cleanup and rejected syntax/numeric cases.

A fixed native harness covers direct entrypoint descriptor/count/extent/alias/
environment failures, exceptional products and poisoned output buffers. Static
and ASan/UBSan builds include checker faults and invalid invocations. This extends
the arithmetic boundary, not a binary-frame parser or a general native API.
Synthetic fixtures establish no native execution observation.

Read-only CI uses existing pinned actions/images and hash-locked dependencies,
builds a wheel offline, installs outside checkout and binds observations to
source, wheel and both consumers. No dependency, publication, credential,
branch-protection, GPU/device or normal-runtime-admission change is made.
Acceptance requires actual observed native execution, final CI and owner review.

## Observed execution

[CI run 35589963541](https://github.com/kirchherr/TUC/actions/runs/35589963541)
passed at `ce704463cb367f7ac435ce8c3521bf16d3cde228`: 251 boundary/protocol tests,
offline wheel installation outside checkout, six isolated source conversions,
twelve CPU calls, 56 bitwise FP32 comparisons, ten source rejections and three
numeric rejections. Static and ASan/UBSan builds each passed 16 successful runs,
131 entrypoint calls, 64 scalar checks, 115 boundary rejections and 459 unchanged
output checks. Ten observations include the three faulty checkers and invalid
invocation for each build. Input-input aliasing is explicitly inapplicable to
the repeated-input square graph's single public input.

The [original combined receipt](../docs/evidence/bounded-cpu-gating-35589963541.json)
is retained without reserialization: 21,959 bytes, SHA256
`72a9e011e1867985cfee1bc2ae32324df2a0003e9a945bbefaad0d2bd2193bd9`.
Artifact `10634510399` contained only `ci-record.json`; its ZIP SHA256
`d50239062a21e046cafa2c3b26a95f52351cff80b2149a9e1d424c27da112691`
matches GitHub metadata and the upload log. Source revision and both consumer
hashes match the checked files. Wheel SHA256 is
`24fd121fd75630fb034af8dad72162fa6ae99adae0b76a97f76004f0144cfd3a`.
These observations establish execution of the fixed CPU corpora, with no
additional device, model-compatibility or performance claim.

Independent local audits reproduced all six source/signature pairs, complete
graphs, public bindings and program digests, plus fifteen input/request pairs.
Separately ordered NumPy FP32 calculations match all 56 actual CLI values,
including four explicit signed-zero cases. The ten source rejections and three
exceptional products also reproduce. All 21 native context files (102,518 bytes),
context/binding digests and ten observations match exact reconstruction. Eight
distinct native graph/dataset cases (32 values) agree with independent FP32
calculations and emitted expectation bits; each runs twice per build. The
single-input alias exclusion and all counters were independently checked.
The artifact contains no wheel or container images; these audits do not claim
to reinstall or rerun them.
