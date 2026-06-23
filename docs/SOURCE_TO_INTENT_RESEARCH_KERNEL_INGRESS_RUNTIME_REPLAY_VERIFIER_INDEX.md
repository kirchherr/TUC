# Source-To-Intent Research Kernel Ingress Runtime Replay Verifier Index

Source-To-Intent Research Kernel Ingress Runtime Replay Verifier Index v0
records digest-only bindings from accepted Kernel Ingress research cases to
Runtime Evidence Replay Verifier reports.

It does not add syntax, approve general Triton source ingestion, execute
`@triton.jit`, expose tensor values, reexecute runtime workloads, or make native
performance claims.

## Contract

- Runtime replay verifier index contract:
  `source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.review.v0`
- Runtime replay verifier contract:
  `runtime_evidence_replay_verifier.review.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`
- Runtime Output Closure Index input:
  `examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`
- Runtime Evidence Bundle Index input:
  `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Capability Claim binding:
  `examples/source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

For each accepted Kernel Ingress case, the index builds Runtime Execution
Evidence Bundle and Runtime Execution Output Closure evidence in memory,
serializes both reports, and runs Runtime Evidence Replay Verifier over those
serialized reports. It records only:

- case ID, graph name, kernel name, backend sequence, operation path, and
  terminal output names;
- Runtime Execution Evidence Bundle metadata and report digests;
- Runtime Execution Output Closure metadata and report digests;
- Runtime Execution Receipt, Runtime Output Contract, and Runtime Public Output
  Bundle digests;
- Runtime Evidence Replay Verifier metadata and report digests;
- replay check count, pass status, replay mode, and raw-value policy.

The replay verifier checks eight fixed bindings:

- graph-name equality;
- replayed Runtime Execution Evidence Bundle digest;
- replayed Runtime Execution Receipt digest;
- replayed Runtime Execution Output Closure digest;
- closure binding to Runtime Execution Evidence Bundle;
- closure binding to Runtime Execution Receipt;
- closure binding to Runtime Output Contract;
- closure binding to Runtime Public Output Bundle.

## Security Boundary

The index is digest-only and value-free. It does not embed raw module source,
extracted kernel source, Source Intent payloads, tensor values, generated code,
backend binaries, benchmark data, host paths, command lines, environment
variables, device identifiers, runtime handles, URLs, or plugin material.

The index consumes only bounded serialized JSON reports produced by trusted
in-repository runtime builders. Runtime replay verification is metadata-digest
replay only and does not require runtime reexecution. It does not import user
modules, execute decorators, access devices, load dynamic libraries, call
subprocesses, perform network access, or discover plugins.

## Review Meaning

This artifact proves that Kernel Ingress runtime evidence is not merely
generated once, but can be replay-verified from its serialized, source-free
reports:

```text
kernel ingress runtime matrix
    ->
runtime step trace
    ->
standard Runtime Execution Evidence Bundles
    ->
Runtime Execution Output Closure
    ->
runtime evidence replay verifier
    ->
runtime replay verifier index
    ->
kernel ingress proof bundle
    ->
kernel ingress evidence gate
    ->
capability claim
```

Future accepted Kernel Ingress cases must pass metadata-digest replay
verification before they can strengthen the bounded Universal Compute research
claim.
