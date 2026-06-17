# RFC 0180: Source-To-Intent Research Kernel Ingress Runtime Step Trace

## Status

Accepted.

## Context

The Kernel Ingress runtime matrix proves that accepted research cases are bound
to runtime plans, execution traces, backend sequences, and correctness digests.
The next practical gap is operation-level visibility: reviewers should be able
to inspect the concrete runtime step path without reading raw source, replaying
Triton, or inspecting tensor values.

## Decision

Add Source-To-Intent Research Kernel Ingress Runtime Step Trace v0:

- `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- `schemas/source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0.schema.json`
- `tests/test_source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_step_trace.json`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md`

The trace records source-free metadata for each accepted Kernel Ingress case:

- case ID and kernel name;
- operation path;
- planned and executed backend per step;
- public input and output tensor names;
- output dtype and shape metadata;
- runtime plan and execution trace digests;
- Kernel Ingress and Runtime Matrix report digests.

The v0 accepted paths are:

- `matmul -> elementwise`
- `softmax -> reduction`
- `matmul -> reduction`
- `matmul -> softmax -> reduction -> elementwise`

## Security Boundary

The artifact remains metadata-only. It must not contain raw module source,
Python source, `@triton.jit`, Source Intent payloads, tensor values, generated
code, backend binaries, command lines, host paths, environment variables,
device identifiers, plugin manifests, or benchmark output.

The trace uses trusted simulator backends through the trusted Runtime Executor.
It must not import user modules, execute decorators, access devices, discover
plugins, call subprocesses, perform network access, or load dynamic libraries.

## Evidence Wiring

The step trace is required by:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`

The CI workflow runs:

- `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`

## Consequences

Accepted Kernel Ingress cases now need operation-level runtime trace evidence
before they can support the bounded Universal Compute research capability
claim.

This still does not prove general Triton source ingestion, native performance,
hardware certification, or replacement of vendor compiler stacks.
