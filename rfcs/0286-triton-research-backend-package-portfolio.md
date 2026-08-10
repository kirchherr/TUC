# RFC 0286: Triton Research Backend Package Portfolio v0

Status: Accepted

## Summary

Connect the fixed realistic Triton module-source research slice to the exact
two-package execution portfolio. Require execution-free parsing, canonical
Source Intent re-intake, no-fallback package planning, trusted simulator
projection, explicit layout conversion, public-output closure, independent
reference correctness, and backend equivalence in one live proof.

## Motivation

RFC 0285 joined Source Intent plain data to external package capability
ownership. Earlier Kernel Ingress proofs established that a tiny realistic
Triton-like module could be parsed as bounded data and executed through built-in
simulators. The two paths remained separate.

The strongest current research question is whether actual syntax can traverse
the entire interface while preserving all trust boundaries. Answering that
question adds more value than another catalog or aggregate gate.

## Decision

Add:

- `docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md`
- `examples/triton_research_backend_package_portfolio.py`
- `schemas/triton_research_backend_package_portfolio_report.v0.schema.json`
- `tests/golden/frontend/triton_research_backend_package_portfolio_report.json`
- `rfcs/0286-triton-research-backend-package-portfolio.md`

Refactor the Source Intent package portfolio example to expose one reusable
function that accepts an already validated `SourceIntentModule`, a plain input
dictionary, and a plain independent-reference dictionary. The function retains
the exact package admission, canonical planning, trusted projection, runtime,
public-output, correctness, and equivalence boundaries of RFC 0285. Dictionary
subclasses and custom mappings are rejected.

The accepted proof path is:

```text
bounded Triton module text
  -> Kernel Ingress and research parser
  -> source_intent.v0
  -> HAC-IR
  -> external-systolic -> external-vector
  -> systolic-sim -> vector-sim
  -> public output y
  -> reference correctness + backend equivalence
  -> PASS
```

## Fixed Source Contract

V0 binds the existing `research_matmul_elementwise` module. It contains exactly
two approved imports, one `@triton.jit` function, and the already admitted
`tl.dot`, `tl.where`, and `tl.store` syntax. Shape authority is supplied through
the bounded manifest `a: 4x8`, `b: 8x2`, and `y: 4x2`.

Module and extracted-kernel digests, byte and line counts, AST node count and
depth, import count, parser status, Source Intent digest, operation families,
and return semantics are fixed in evidence.

## Trust Model

- Source text is attacker-controlled data.
- The module is bounded before AST parsing.
- Imports and decorators are inspected structurally and never executed.
- Only one function is extracted; top-level statements are rejected.
- Research parser output is plain data and is independently revalidated by
  Source Intent Intake.
- External packages remain attacker-controlled capability data.
- Package execution authority comes only from exact maintainer-owned digest
  bindings to fixed trusted simulators.
- Runtime values remain internal and public evidence remains metadata-only.

## Evidence Invariants

- Twelve artifacts have exact IDs, contracts, order, and SHA-256 digests.
- Source module and extracted-kernel identities are digest-bound.
- Source text and Source Intent payload bodies are omitted.
- Source plan is exactly `external-systolic -> external-vector`.
- Trusted plan is exactly `systolic-sim -> vector-sim`.
- Fallback assignment count is zero.
- One `blocked -> row_major` conversion remains explicit.
- Public output is `y`; terminal tensor is `activated`.
- Reference correctness and backend equivalence pass.
- Source, import, decorator, JIT, package-code, plugin, native-device, and raw
  value execution or serialization flags remain false.
- Production source ingestion admission remains false.

## Security Consequences

This RFC does not widen production Source Ingestion Admission. It exercises an
explicit research entrypoint with a fixed syntax and shape slice. It introduces
no import, JIT, plugin, native library, subprocess, network, device, generated
artifact, or package implementation execution.

Negative tests reject disallowed imports, unsupported decorators, top-level
file access, custom input mappings, unknown evidence fields, source-admission
claim drift, and package-digest drift.

## Alternatives Rejected

### Promote the existing Source Intent proof without source syntax

Rejected because it would leave the parser-to-external-capability connection
untested.

### Enable general Triton source ingestion

Rejected because one fixed research slice does not establish parser coverage,
production sandboxing, dependency isolation, or arbitrary source safety.

### Import Triton and inspect a live function

Rejected because module import and decorator evaluation would execute
attacker-controlled code before canonical validation.

### Execute external package implementations

Rejected because capability portability and semantic placement can be proved
through fixed trusted projections without opening plugin or native-code attack
surfaces.

## Consequences

TUC now demonstrates one continuous path from realistic bounded syntax through
the hardware-neutral interface into independently described heterogeneous
capabilities and semantically equivalent execution. Remaining claims stay
explicit: broader syntax, production source admission, sandboxed executable
backends, physical devices, and native performance are not yet proven.
