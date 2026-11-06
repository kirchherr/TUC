# RFC 0340: Explicit Bounded Model Application Runtime

- Status: Implemented candidate; fixed installed native evidence passed
- Date: 2026-10-12
- Depends on: RFC 0339

Integration: [PR #136](https://github.com/kirchherr/TUC/pull/136) merged at
`83c12b31b32cd0ee52ba317a635a898b07a7998c` after both complete 7,589-test
validations and the exact-head installed native observation passed. The owner
authorized a one-time review-rule exception; repository rules were unchanged.

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
native correctness evidence is introduced. Installed Linux execution and independent standard-library numerical audit
passed for three fixed contexts (18 FP32 scalars and four rejection controls)
at `59ad813`. This is bounded same-project evidence, not independent
organizational reproduction. The original record is retained in
`integration/bounded_model_application/observed-ci-59ad813.json`.


## Observed acceptance

[Installed Linux job](https://github.com/kirchherr/TUC/actions/runs/38277950014/job/114907922282)
passed at source `59ad8139813ac5eb7b891907b3d74ebb06059a67`. It executed three
contexts against an installed wheel outside the checkout, rejected four invalid
or overflowing calls, and cleaned all owned workspaces. The separate auditor
ran under `python -I -S`, confirmed 18 bit-exact FP32 outputs and model/request/
response identities without importing TUC, and was replayed locally against the
original recorded bytes. Wheel SHA-256:
`918eed0420667ed38c12ea2bd38e2bbb519511978d35c95cde6ce13ac795f11d`.
Protocol receipts still make no provenance claim; the retained CI observation
records the trusted execution event separately.

## Review correction, 2026-10-14

The separate auditor now rejects malformed opaque digest fields even when
request and result hashes are recomputed. It also checks that variable input
changes preserve bundle/compilation identities, parameter changes alter both,
and backend identity stays fixed across all three cases. These remain bounded
consistency checks, not independent compilation or provenance authentication.
The original observation is unchanged; its original auditor source is retained
under `integration/bounded_model_application/archive/` with the recorded hash.

## Offline evidence distribution

`scripts/build_model_application_audit_kit.py` packages an exact committed Git
snapshot of the current auditor, original CI packet and archived original
auditor and the project's LICENSE/NOTICE, together with README, source commit
and internal checksums. It creates
only a new output, reads bounded regular blobs rather than working-tree files,
uses fixed stored ZIP metadata and never executes packaged sources. No compiler
or runtime API, target, native command, plugin or admission changes follow.

The existing read-only native workflow replays the extracted kit outside the
checkout under Python `-I -S` before retaining the ZIP and external checksum.
This is distribution and reproduction readiness, not independently controlled
reproduction or authentication. The
[acceptance handoff](../docs/BOUNDED_MODEL_APPLICATION_HANDOFF.md) records the
fixed completed path and the remaining external acceptance.
