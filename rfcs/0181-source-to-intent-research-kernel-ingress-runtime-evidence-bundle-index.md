# RFC 0181: Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index

## Status

Accepted.

## Context

RFC 0180 made Kernel Ingress runtime execution inspectable at the operation
step level. The next practical gap is architectural reuse: Kernel Ingress
should not grow its own runtime proof vocabulary when TUC already has a
standard Runtime Execution Evidence Bundle for tensor-store evidence, input
manifests, output manifests, reference correctness, and execution receipts.

## Decision

Add Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index v0:

- `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- `schemas/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0.schema.json`
- `tests/test_source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.json`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md`

The index builds a standard `runtime_execution_evidence_bundle.data_only.v0`
report for each accepted Kernel Ingress case, validates that bundle, and emits
only digest/count metadata.

## Security Boundary

The index must remain digest-only and value-free. It must not contain raw
module source, Python source, `@triton.jit`, Source Intent payloads, tensor
values, generated code, backend binaries, command lines, host paths,
environment variables, device identifiers, plugin manifests, or benchmark
output.

The index uses trusted simulator backends through the trusted Runtime Executor
path. It must not import user modules, execute decorators, access devices,
discover plugins, call subprocesses, perform network access, or load dynamic
libraries.

## Evidence Wiring

The index is required by:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`

The CI workflow runs:

- `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`

## Consequences

Accepted Kernel Ingress cases now need to pass the same standard runtime
evidence bundle path as core proof-of-execution cases before they can support
the bounded Universal Compute research capability claim.

This still does not prove general Triton source ingestion, native performance,
hardware certification, or replacement of vendor compiler stacks.
