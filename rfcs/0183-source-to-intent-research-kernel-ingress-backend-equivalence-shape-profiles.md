# RFC 0183: Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles

## Status

Accepted.

## Context

Kernel Ingress Backend Equivalence proves that each accepted
module-shaped Source Intent preserves public outputs across a neutral
`reference-cpu` baseline and capability-selected trusted simulator placement.

That proof is still anchored to one fixture shape per accepted case. For the
Universal Compute research claim, the next practical question is whether the
same frontend intent remains valid across small problem-size changes without
moving hardware details into the frontend.

This is not a dynamic-shape system and not a native performance claim. It is a
bounded research proof that the current hardware-independent Source Intent can
be re-ingested with explicit declared shape profiles and still preserve public
outputs across trusted backend placements.

## Decision

Add Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles
v0:

- `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0.schema.json`
- `tests/test_source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md`

For each accepted Kernel Ingress case, the example compiles the same
Source-Intent-derived `ComputeGraph` under two explicit shape profiles:

- `base`
- `alternate`

For each profile it executes:

- baseline: `reference-cpu` fallback only;
- candidate: trusted capability-selected `linear-sim` and `vector-sim`
  backends.

It validates both runs against reference correctness and then validates the
terminal outputs with the existing `runtime_backend_equivalence.data_only.v0`
contract. The emitted report stores only summary metadata and digests.

## Security Boundary

The report must remain metadata-only and value-free. It must not contain raw
module source, Python source, `@triton.jit`, Source Intent payloads, tensor
values, generated code, backend binaries, command lines, host paths,
environment variables, device identifiers, plugin manifests, benchmark output,
or raw comparison outputs.

The comparison must use only the fixed trusted Runtime Executor registry. It
must not import user modules, execute decorators, access devices, discover
plugins, call subprocesses, perform network access, load dynamic libraries, or
execute generated artifacts.

## Evidence Wiring

The shape-profile backend equivalence report is required by:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`

The CI workflow runs:

- `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`

## Consequences

The bounded Source-to-Intent research capability claim can now say that the
current accepted Kernel Ingress slice preserves public outputs and reference
correctness across a neutral `reference-cpu` baseline, capability-selected
trusted simulator placements, and two explicit shape profiles.

This still does not prove general Triton source ingestion, arbitrary dynamic
shape support, native performance, hardware certification, arbitrary backend
execution, or replacement of vendor compiler stacks.
