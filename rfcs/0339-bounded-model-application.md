# RFC 0339: Bounded Model Application Protocol Bridge

- Status: Implemented candidate
- Date: 2026-10-09

## Context

RFC 0338 binds concrete model input bits to a portable capability-planned
bundle. The existing RFC 0324 CPU application protocol separately binds binary
requests and checked responses to a generated C11 program. Applications need
an explicit connection between these identities before using either boundary.

## Decision

`prepare_bounded_model_application` requires original model bytes, explicit
backend bindings, bundle bytes, variable input bytes and request bytes. It
fully revalidates the RFC 0338 context, requires every declared backend binding
to target C11, regenerates the existing checked CPU application, and encodes
fixed plus variable input bits in its manifest-defined order. It returns inert
application data, a binary request frame, input values and original identities.
No CUDA-to-CPU substitution or capability fallback is permitted.

`decode_bounded_model_application_response` recreates preparation from the
original bytes and checks the caller-supplied response through the existing
C11 protocol decoder. Only a complete successful response with exact program
and binary-request identities is accepted. Error status, bad exit code,
nonfinite/subnormal output, length drift and replay against changed inputs
fail closed. Public output positions, shapes and FP32 bits remain explicit.

The canonical result receipt uses contract
`tuc.bounded_model_application_result.v0`. It binds bundle, model, model
compilation, backend, model request, C11 program, binary request, response hash
and output bits, with a SHA-256 digest over its payload. Receipt validation
recomputes the entire result from original request and response bytes.

## Security boundary

All input bytes and response bytes are untrusted. Existing model, bundle,
request, application, frame and numeric budgets apply unchanged. Receipt
validation accepts only exact bytes up to 1 MiB and compares them to the
regenerated canonical result without parsing caller-supplied receipt JSON.
Every failure uses `model_application_rejected`, without raw values or paths.
Caller-constructed prepared/result objects confer no validation authority.

The bridge imports no runtime and performs no filesystem/network access,
subprocess launch, device access, plugin discovery or native compilation or
execution. A caller may separately use the existing explicit isolated Linux
C11 build/run boundary. This RFC does not widen that boundary.

Protocol consistency is not execution provenance or numerical correctness.
Every receipt sets `native_execution_observed` to false because the bridge
cannot determine where caller-supplied response bytes came from. Synthetic
responses and recomputed digests cannot promote this claim.

## Acceptance

1. Deterministic preparation preserves signed zero and exact fixed/variable
   FP32 input bits in the existing binary protocol.
2. Changes to parameters or variable inputs retain the graph's C11 program
   but change model-request and binary-request identities; replay rejects.
3. CUDA and mixed capability contexts reject at the CPU boundary.
4. Malformed/failed responses and noncanonical, rehashed or substituted
   receipts reject; output positions/shapes/bits are retained exactly.
5. The installed-wheel consumer reproduces a closed source-free report with
   three CPU input contexts and explicit synthetic-response/nonexecution flags.
6. Adjacent application, model, bundle, request and compiler tests remain green.

## Non-claims and next work

No observed native execution, runtime handle, resident weights, signing,
authentication, general model-format compatibility, performance or CUDA result
equivalence is provided. An execution integration must preserve provenance
through the separately admitted runtime and independently compare results;
protocol receipts alone are insufficient evidence of either property.
