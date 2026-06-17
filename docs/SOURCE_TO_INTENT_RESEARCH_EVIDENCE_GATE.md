# Source-To-Intent Research Evidence Gate

Source-To-Intent Research Evidence Gate v0 binds the current research parser
evidence chain by digest.

It does not open the default source parser path and does not authorize source
text as compiler input.

## Contract

- Gate contract: `source_to_intent_research_evidence_gate.ci.v0`
- Example: `examples/source_to_intent_research_evidence_gate.py`
- Execution bridge example:
  `examples/source_to_intent_research_execution_bridge.py`
- Execution bridge docs:
  [Source-To-Intent Research Execution Bridge](SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md)
- Preflight bridge example:
  `examples/source_to_intent_research_preflight_bridge.py`
- Preflight bridge docs:
  [Source-To-Intent Research Preflight Bridge](SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md)
- Idiom alignment example:
  `examples/source_to_intent_research_idiom_alignment.py`
- Idiom alignment docs:
  [Source-To-Intent Research Idiom Alignment](SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT.md)
- Source runtime smoke example:
  `examples/source_to_intent_research_source_runtime_smoke.py`
- Source runtime smoke docs:
  [Source-To-Intent Research Source Runtime Smoke](SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md)
- Kernel ingress example:
  `examples/source_to_intent_research_kernel_ingress.py`
- Kernel ingress docs:
  [Source-To-Intent Research Kernel Ingress](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md)
- Kernel ingress runtime matrix example:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Kernel ingress runtime matrix docs:
  [Source-To-Intent Research Kernel Ingress Runtime Matrix](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md)
- Kernel ingress runtime coverage policy example:
  `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
- Kernel ingress runtime coverage policy docs:
  [Source-To-Intent Research Kernel Ingress Runtime Coverage Policy](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md)
- Kernel ingress runtime backend alignment example:
  `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
- Kernel ingress runtime backend alignment docs:
  [Source-To-Intent Research Kernel Ingress Runtime Backend Alignment](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md)
- Kernel ingress boundary budget example:
  `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
- Kernel ingress boundary budget docs:
  [Source-To-Intent Research Kernel Ingress Boundary Budget](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md)
- Kernel ingress rejection coverage example:
  `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
- Kernel ingress rejection coverage docs:
  [Source-To-Intent Research Kernel Ingress Rejection Coverage](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md)
- Kernel ingress conformance gate example:
  `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
- Kernel ingress conformance gate docs:
  [Source-To-Intent Research Kernel Ingress Conformance Gate](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md)
- Kernel ingress diagnostics example:
  `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
- Kernel ingress diagnostics docs:
  [Source-To-Intent Research Kernel Ingress Diagnostics](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md)
- Kernel ingress idiom alignment example:
  `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
- Kernel ingress idiom alignment docs:
  [Source-To-Intent Research Kernel Ingress Idiom Alignment](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md)
- Kernel ingress proof bundle example:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel ingress proof bundle docs:
  [Source-To-Intent Research Kernel Ingress Proof Bundle](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md)
- Kernel ingress evidence gate example:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Kernel ingress evidence gate docs:
  [Source-To-Intent Research Kernel Ingress Evidence Gate](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md)
- Golden: `tests/golden/frontend/source_to_intent_research_evidence_gate.txt`
- Tests: `tests/test_source_to_intent_research_evidence_gate.py`
- CI entry: `.github/workflows/ci.yml`

The gate binds:

- Source-To-Intent Research Readiness
- Source-To-Intent Research Parser Conformance Gate
- Source-To-Intent Research Diagnostics
- Source-To-Intent Research Preflight Bridge
- Source-To-Intent Research Execution Bridge
- Source-To-Intent Research Idiom Alignment
- Source-To-Intent Research Source Runtime Smoke
- Source-To-Intent Research Kernel Ingress
- Source-To-Intent Research Kernel Ingress Conformance Gate
- Source-To-Intent Research Kernel Ingress Diagnostics
- Source-To-Intent Research Kernel Ingress Idiom Alignment
- Source-To-Intent Research Kernel Ingress Proof Bundle
- Source-To-Intent Research Kernel Ingress Evidence Gate

Kernel Ingress Runtime Matrix, Kernel Ingress Runtime Coverage Policy, Kernel
Ingress Runtime Backend Alignment, Kernel Ingress Boundary Budget, and Kernel
Ingress Rejection Coverage are bound through the Kernel Ingress Proof Bundle
and focused Kernel Ingress Evidence Gate.

Each input artifact is hashed with SHA-256 and the digest is emitted in the
gate output.

## Required Checks

The gate passes only when:

- Research Readiness is `ready`.
- `SOURCE_TO_INTENT_REQUIRED_EVIDENCE` includes
  `source_to_intent_research_diagnostics`.
- Research Readiness marks both
  `source_intent_frontend_conformance_gate` and
  `source_to_intent_research_diagnostics` present.
- Research Parser Conformance Gate passes for the accepted parser sources.
- Research Diagnostics passes for the same accepted parser sources.
- Research Preflight Bridge passes for the accepted and rejected parser
  diagnostic cases.
- Research Preflight Bridge validates Preflight rejection and parser semantic
  rejection as distinct stages before its digest is accepted.
- Research Execution Bridge passes for the same accepted parser sources.
- Research Execution Bridge validates as a structured v0 contract before its
  digest is accepted.
- Research Idiom Alignment passes for the same accepted parser sources.
- Research Idiom Alignment validates accepted parser operation families
  against Triton Idiom Coverage before its digest is accepted.
- Research Source Runtime Smoke passes for the same accepted parser sources.
- Research Source Runtime Smoke validates the full source-buffer to runtime
  smoke path before its digest is accepted.
- Research Kernel Ingress passes for the accepted module-shaped source cases,
  including the Kernel-Ingress-specific `matmul_reduction` fixture.
- Research Kernel Ingress validates module import prelude and kernel extraction
  as data before its digest is accepted.
- Research Kernel Ingress Conformance Gate passes for accepted module-source
  outputs and rejected Source Intent escape cases.
- Research Kernel Ingress Conformance Gate validates that Kernel Ingress has no
  privileged bypass around Source Intent Frontend Conformance.
- Research Kernel Ingress Diagnostics passes for the accepted and rejected
  module-shaped source cases.
- Research Kernel Ingress Diagnostics validates stable rejection reason IDs
  before its digest is accepted.
- Research Kernel Ingress Idiom Alignment passes for the accepted
  module-shaped source cases.
- Research Kernel Ingress Idiom Alignment validates accepted Kernel Ingress
  operation families against Triton Idiom Coverage before its digest is
  accepted.
- Research Kernel Ingress Proof Bundle validates the Kernel Ingress E2E,
  runtime-matrix, runtime-coverage-policy, runtime-backend-alignment,
  boundary-budget, rejection-coverage, diagnostics, conformance, and
  idiom-alignment artifacts before its digest is accepted.
- Research Kernel Ingress Evidence Gate validates the focused Kernel Ingress
  proof slice, Runtime Matrix, Runtime Coverage Policy, Runtime Backend
  Alignment, and exact Proof Bundle digest bindings before its digest is
  accepted.
- Diagnostics covers the whitelisted rejected source cases.
- Parser status remains `research_explicit_only`.
- Default parser status remains `default_parser_blocked`.
- Parser output policy remains `source_intent.v0_plain_data_only`.
- Metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime-plan, and
  backend-decision outputs remain blocked at the parser boundary.

## Security Boundary

The gate consumes already-rendered evidence or in-memory report objects. It
does not parse source text, import frontend modules from user code, evaluate
decorators, execute `@triton.jit`, read source files by path, access devices,
load plugins, run subprocesses, emit generated artifacts, or lower source text
to compiler artifacts.

The gate output is source-free. It must not contain raw source text, Source
Intent payloads, exception text, Python source snippets, device handles,
runtime tensors, host paths, environment variables, plugin entrypoints, or
subprocess output.

## Review Meaning

This gate makes the current parser research proof harder to drift:

```text
Research Readiness
    +
Research Parser Conformance Gate
    +
Research Diagnostics
    ->
Research Preflight Bridge
    ->
Research Execution Bridge
    +
Research Idiom Alignment
    +
Research Source Runtime Smoke
    +
Research Kernel Ingress
    +
Research Kernel Ingress Conformance Gate
    +
Research Kernel Ingress Diagnostics
    +
Research Kernel Ingress Idiom Alignment
    +
Research Kernel Ingress Proof Bundle
    includes Research Kernel Ingress Runtime Matrix
    includes Research Kernel Ingress Runtime Coverage Policy
    includes Research Kernel Ingress Runtime Backend Alignment
    includes Research Kernel Ingress Boundary Budget
    includes Research Kernel Ingress Rejection Coverage
Research Kernel Ingress Evidence Gate
    ->
Digest-bound source-free parser research evidence
```

Future parser syntax must update the diagnostics evidence, readiness evidence,
the execution bridge contract, Kernel Ingress evidence, Kernel Ingress Idiom
Alignment evidence, Kernel Ingress Boundary Budget evidence, Kernel Ingress
Rejection Coverage evidence, Kernel Ingress Runtime Matrix evidence, Kernel
Ingress Runtime Coverage Policy evidence, Kernel Ingress Runtime Backend
Alignment evidence, Kernel Ingress Proof Bundle evidence, Kernel Ingress
Evidence Gate evidence, and this gate before the expanded syntax can count as
accepted research parser scope.
