# RFC 0182: Source-To-Intent Research Kernel Ingress Backend Equivalence

## Status

Accepted.

## Context

Kernel Ingress can now prove that realistic module-shaped source buffers pass
through Source Intent, runtime planning, trusted execution, runtime step trace,
and standard runtime evidence bundles.

The next Universal Compute-relevant question is portability: does the same
accepted Source Intent preserve public outputs when planned through a neutral
baseline and through capability-selected trusted simulator backends?

This is not a native performance claim. It is a bounded research proof that the
current hardware-independent interface can survive at least two trusted runtime
placement families without changing frontend intent.

## Decision

Add Source-To-Intent Research Kernel Ingress Backend Equivalence v0:

- `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
- `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_report.v0.schema.json`
- `tests/test_source_to_intent_research_kernel_ingress_backend_equivalence.py`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence.json`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md`

For each accepted Kernel Ingress case, the example compiles the same
Source-Intent-derived `ComputeGraph` twice:

- baseline: `reference-cpu` fallback only;
- candidate: trusted capability-selected `linear-sim` and `vector-sim`
  backends.

It executes both plans through the trusted Runtime Executor and validates the
terminal output metadata with the existing
`runtime_backend_equivalence.data_only.v0` contract. The emitted report stores
only summary metadata and digests.

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

The backend equivalence report is required by:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`

The CI workflow runs:

- `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`

## Consequences

The bounded Source-to-Intent research capability claim can now say that the
current accepted Kernel Ingress slice preserves public outputs across a neutral
`reference-cpu` baseline and capability-selected trusted simulator placements.

This still does not prove general Triton source ingestion, native performance,
hardware certification, arbitrary backend execution, or replacement of vendor
compiler stacks.
