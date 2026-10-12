# RFC 0340: Explicit Bounded Model Application Runtime

- Status: Implemented candidate; native evidence pending
- Date: 2026-10-12
- Depends on: RFC 0339

## Decision

The existing explicit isolated Linux C11 handle gains `run_frame(request)`.
It revalidates the original graph, capabilities, application and owned context,
then checks the exact binary frame before process launch. Only a complete,
checked successful response is returned. The existing named-input `run` and
new frame method share one execution path, lifecycle lock, fixed Docker command,
pinned image identity, output/time budgets, process error handling and cleanup.

`validate_bounded_c11_request` exposes the existing pure frame gate without
execution. Program identity, request hash, exact type/size/magic, finite normal
or signed-zero FP32 input values are required. This frame gate knows a CPU
program, not model parameters: model-specific admission remains mandatory.

`run_bounded_model_application` fully validates the original model, capabilities,
bundle, variable input and portable request before any build. It explicitly
builds through the existing Linux C11 runtime, requires the same program digest,
runs the exact admitted frame, decodes through RFC 0339 and closes the handle
on both success and failure. No caller-selected source, command, image,
endpoint, environment or plugin override is added. CUDA/mixed contexts reject.

## Security and evidence boundary

Calling the runtime adapter explicitly starts the existing admitted build/run
boundary. Import, model parsing and pure preparation remain inert. Existing
Linux x86-64 platform, workspace ownership, context identity, network isolation,
read-only execution, non-root process, resource limits and cleanup apply.
Bad frames reject before process launch. Failed responses produce no result.
The runtime closes its build resources even when protocol validation fails.

RFC 0339 receipts retain `native_execution_observed=false`: receipt bytes are
not execution provenance, even when returned by a trusted execution call.
Mocked tests and synthetic process responses do not constitute native evidence.
A separately retained execution record and independent numerical comparison
are required before making observed execution claims. No such evidence is
added by this RFC's mocked tests.

## Acceptance

1. Named-input and binary-frame calls use the same isolation and protocol gate.
2. Invalid types, lengths, magic, program identity, digest and rehashed subnormal
   payloads reject before process launch; closed handles reject.
3. Model requests are checked before building; the exact validated frame is
   passed to the existing execution boundary.
4. Successful model responses retain signed-zero output bits and request
   identity. Failed responses release build resources.
5. Existing runtime, application and model protocol regression tests pass.

## Non-claims

No new generally executable backend, resident-weight/session contract, model
format compatibility, performance, CUDA execution, authentication or observed
native correctness evidence is introduced. Actual installed Linux execution
and independent numerical comparison remain pending.
