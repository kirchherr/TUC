# Proof Of Backend Equivalence

Proof of Backend Equivalence is a TUC proof type for showing that the same
hardware-independent compute intent preserves observable terminal-output
semantics across distinct trusted backend placements.

It is a correctness and portability proof slice. It is not a native execution
claim, not a native performance claim, and not a replacement claim for CUDA,
ROCm, XLA, TVM, IREE, or vendor compiler stacks.

## Claim Shape

```text
same compute intent
  + same declared inputs
  + same output contract
  + trusted baseline execution
  + trusted candidate execution
  + bounded output comparison
  + metadata-only evidence
  = backend equivalence PASS
```

The baseline is neutral. The current research baseline is `reference-cpu`.

The candidate is capability-selected. Current Source-To-Intent Kernel Ingress
research evidence uses trusted simulator placements such as `linear-sim` and
`vector-sim`. Runtime-level historical fixtures also cover a specialized
accelerator simulator, but no single simulator is the proof center.

## Required Evidence

A Backend Equivalence proof needs:

- identical graph or Source Intent case identity for baseline and candidate;
- identical external input inventory;
- identical output contract and public output aliases;
- trusted Runtime Executor conformance for every backend in both runs;
- explicit baseline and candidate backend sequences;
- bounded shape, dtype, and tolerance comparison of terminal outputs;
- raw tensor values omitted from serialized evidence;
- schema-versioned report metadata and stable comparison digests;
- evidence-gate binding to exact artifact IDs, not only evidence kinds.

## Current Artifacts

Runtime-level backend equivalence:

```text
docs/RUNTIME_BACKEND_EQUIVALENCE.md
examples/runtime_backend_equivalence.py
examples/runtime_vector_backend_equivalence.py
examples/runtime_mixed_backend_equivalence.py
examples/runtime_backend_equivalence_portfolio.py
tests/golden/runtime_backend_equivalence/current_report.json
tests/golden/runtime_backend_equivalence/vector_sim_report.json
tests/golden/runtime_backend_equivalence/mixed_accelerators.json
tests/golden/runtime_backend_equivalence/portfolio_report.json
```

Source-To-Intent Kernel Ingress backend equivalence:

```text
docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md
docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md
examples/source_to_intent_research_kernel_ingress_backend_equivalence.py
examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py
tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence.json
tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json
```

Gate bindings:

```text
docs/RUNTIME_EVIDENCE_GATE.md
docs/RUNTIME_EVIDENCE_FLOW.md
docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md
tests/golden/proofs/runtime_evidence_gate.txt
tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt
```

## What It Proves

- A compute-intent fixture can be executed by a neutral baseline and a distinct
  capability-selected trusted simulator placement.
- The observable terminal-output contract can remain equivalent across those
  placements.
- Backend choice can be made visible through evidence instead of hidden inside
  implicit fallbacks.
- Public proof artifacts can remain value-free while still binding the
  comparison result to graph identity, output contracts, backend sequences, and
  evidence digests.

## What It Does Not Prove

- It does not prove native device execution.
- It does not prove real device residency, allocation handles, stream behavior,
  cache behavior, tensor-core use, or physical layout ownership.
- It does not prove native performance parity or benchmark acceptance.
- It does not prove arbitrary backend plugins are safe.
- It does not prove broad source-parser correctness.
- It does not allow hardware-specific performance facts to become HAC-IR
  semantics.

## Secure-By-Design Boundary

Backend Equivalence reports are data-only. They must not serialize:

- raw tensor values;
- tensor-value digests;
- device identifiers;
- runtime handles;
- allocation handles;
- host paths;
- environment variables;
- command lines;
- generated code;
- backend binaries;
- plugin entrypoints;
- raw benchmark samples.

The comparison may inspect runtime arrays only inside the trusted in-process
Runtime Executor boundary. Serialized evidence must remain bounded, typed, and
reviewable.

## Reviewer Checklist

A Backend Equivalence proof should be rejected if:

- baseline and candidate runs are not tied to the same graph or Source Intent
  case;
- the candidate backend is selected by an implicit fallback instead of explicit
  capability evidence;
- output contracts differ between runs;
- raw values or value digests appear in public artifacts;
- backend sequences are absent or ambiguous;
- trusted executor conformance is missing;
- the proof claims native performance, native residency, or vendor parity;
- the report is not bound by the relevant evidence gate.
