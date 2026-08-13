# RFC 0272: First Real Triton Kernel Path

## Status

Accepted.

## Context

TUC's Source-To-Intent Kernel Ingress work already proves realistic
Triton-module-shaped research fixtures through controlled source handling,
runtime execution, backend equivalence, and evidence gates. Reviewers still need
a compact artifact that shows the first practical end-to-end path without
reading the full Kernel Ingress bundle.

The project must also avoid diluting the research claim into a production
compiler claim. A narrow proof for one MVP case is preferable to a broad claim
about arbitrary Triton input.

## Decision

Add `examples/first_real_triton_kernel_path.py` as a digest-bound, source-free
proof report for the `research_module_mvp_pipeline` / `mvp_pipeline` case.

The report MUST bind:

- Kernel Ingress e2e evidence.
- Kernel Ingress Runtime Matrix evidence.
- Kernel Ingress Backend Equivalence Shape Profiles evidence.
- Kernel Ingress Proof Bundle evidence.
- Kernel Ingress Evidence Gate output.
- Source Ingestion Pre-Claim Acyclicity Gate evidence.
- Source Ingestion Admission Gate evidence.

The report MUST publish only metadata, expected operation families, backend
sequence, terminal output names, trace-step count, artifact contracts, artifact
digests, supported claims, blocked claims, and blocked execution surfaces.

## Security Requirements

The report MUST NOT serialize:

- raw module source;
- extracted kernel source;
- Source Intent payloads;
- raw tensor values;
- runtime handles;
- device identifiers;
- host paths;
- command lines;
- generated code;
- backend artifacts;
- native benchmark output.

The report MUST NOT execute `@triton.jit`, import Triton modules, access
devices, discover plugins, execute generated artifacts, or admit direct source
ingestion.

## Non-Claims

This RFC does not claim arbitrary Triton source ingestion, production parser
readiness, native backend execution, native performance parity, CUDA
replacement, or runtime-handle residency.

## Artifacts

- Example: `examples/first_real_triton_kernel_path.py`
- Schema: `schemas/first_real_triton_kernel_path_report.v0.schema.json`
- Golden: `tests/golden/frontend/first_real_triton_kernel_path.json`
- Tests: `tests/test_first_real_triton_kernel_path.py`
- Doc: `docs/FIRST_REAL_TRITON_KERNEL_PATH.md`
- RFC path: `rfcs/0272-first-real-triton-kernel-path.md`

## Consequences

The new proof gives reviewers one practical top-level artifact for the bounded
research path while keeping the larger Kernel Ingress proof bundle and evidence
gate as the underlying authority.

Future expansion to broader source syntax MUST first update the underlying
Kernel Ingress, diagnostics, conformance, rejection, runtime, equivalence, and
admission evidence. This proof cannot be widened by editing only its public
claim text.
