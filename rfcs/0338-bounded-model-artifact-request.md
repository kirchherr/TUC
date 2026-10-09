# RFC 0338: Bounded Model Artifact Requests

- Status: Implemented candidate
- Date: 2026-10-09

## Context

RFC 0337 transfers capability-planned model artifacts and fixed parameters,
but leaves concrete variable inputs outside that portable representation.
A downstream application needs an invocation identity that binds both kinds
of input to the exact bundle before crossing a separate execution boundary.

## Decision

Contract `tuc.bounded_model_artifact_request.v0` is canonical ASCII JSON with
one terminating newline. It carries bundle, model, model-compilation and
backend-binding digests, plus all fixed and variable input tensor positions,
shapes and exact little-endian FP32 bits in ascending tensor-index order.
A SHA-256 request digest covers the canonical payload without its digest field.

Creation validates the bundle against the original model and capabilities,
then reuses the existing model input gate for exact variable names, lengths
and finite normal-or-zero FP32 values. Fixed parameters cannot be overridden.
Inspection checks the closed request structure, canonical bytes, exact bundle
bindings, fixed bits, FP32 validity and request digest. Full validation
additionally recreates the request from the original model, capabilities,
bundle and variable inputs and requires constant-time byte equality.

Changing variable inputs changes only the request identity. Changing fixed
parameters or backend capabilities changes the bundle context and request
identity. Signed zero is preserved. Inspection establishes integrity and
consistency with the supplied bundle; it does not authenticate an origin.
SHA-256 identities are not signatures or evidence of execution.

## Security boundary

Requests are bounded inert data. All inputs are untrusted. The request limit
is 2 MiB, with at most 65,536 total fixed plus variable elements. Existing
model and bundle limits constrain tensor names, counts, shapes and extents;
the JSON scanner additionally bounds nesting, tokens and numeric text.
Duplicate keys, unexpected fields, noncanonical encoding, malformed hex,
nonfinite/subnormal values, parameter substitution and context drift fail
with `model_artifact_request_rejected`. Diagnostics expose no input values.

No filesystem, network, native compilation, subprocess, device, plugin,
runtime or generated-code execution is introduced. Persistence and execution
remain separate caller-owned trust decisions.

## Acceptance

1. Deterministic canonical requests preserve signed-zero FP32 bits and exact
   input tensor positions.
2. Changes to variable inputs, parameters and capabilities are correctly bound;
   original-context validation rejects substitutions even with recomputed hashes.
3. Negative tests reject malformed JSON, invalid FP32 bits, wrong extents,
   fixed overrides, noncanonical bytes and resource-budget violations.
4. A public-API consumer covers CPU, CUDA and mixed plans with two variable
   inputs per plan and a fixed-parameter change.
5. An installed wheel reproduces the committed closed, source-free report.
6. The API performs no persistence or execution.

## Non-claims and next boundary

This is not a runtime, transport, model-format adapter, authentication service,
performance claim or proof of CPU/CUDA result equivalence. A later application
bridge must explicitly admit validated bundle/request data at its existing
build and execution boundary and bind resulting output evidence to the request.
