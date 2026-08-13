# RFC 0211: Source-To-Intent Research Kernel Ingress Runtime Replay Verifier Index

Status: Accepted

## Context

Kernel Ingress research now binds accepted Triton-module-shaped cases through
runtime matrix evidence, step traces, standard Runtime Execution Evidence
Bundles, Runtime Execution Output Closure, backend equivalence, shape-profile
equivalence, runtime coverage policy, and trusted executor alignment.

Runtime Evidence Replay Verifier separately proves that serialized Runtime
Execution Evidence Bundle and Runtime Execution Output Closure reports can be
replayed as metadata-digest evidence without runtime reexecution.

The missing practical bridge is to require the Kernel Ingress path to produce
that same replay-verifiable evidence.

## Decision

Add a Runtime Replay Verifier Index for accepted Kernel Ingress research cases:

- `examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`
- `schemas/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0.schema.json`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json`
- `tests/test_source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md`

The report records only digest bindings and counts for four accepted cases:

- `matmul_elementwise`
- `softmax_reduction`
- `matmul_reduction`
- `mvp_pipeline`

The index is bound into:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`
- `.github/workflows/ci.yml`

## Security Boundary

The slice uses already-accepted Kernel Ingress research fixtures, trusted
in-repository runtime builders, Runtime Execution Evidence Bundle, Runtime
Execution Output Closure, and Runtime Evidence Replay Verifier.

It does not serialize source text, Source Intent payloads, tensor values, host
paths, commands, backend artifacts, device identifiers, runtime handles, URLs,
generated code, timing samples, or plugin entry points.

It does not add general Triton source ingestion, production parsing, plugin
discovery, device access, JIT execution, dynamic imports, dynamic library
loading, generated-artifact execution, network access, subprocess execution, or
runtime reexecution during replay verification.

## Consequences

Kernel Ingress evidence now proves that accepted research cases can produce
standard runtime evidence, close public outputs, and replay-verify those
serialized evidence reports by metadata digest. This strengthens the bounded
Universal Compute research claim without claiming CUDA replacement, native
performance parity, or general source parser completeness.
