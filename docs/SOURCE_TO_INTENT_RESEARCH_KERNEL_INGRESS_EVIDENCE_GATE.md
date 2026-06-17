# Source-To-Intent Research Kernel Ingress Evidence Gate

Source-To-Intent Research Kernel Ingress Evidence Gate v0 is the CI-facing gate
for the realistic Triton-module-shaped Kernel Ingress research slice.

It does not add syntax, approve general Triton source ingestion, or authorize
production parsing.

## Contract

- Gate contract:
  `source_to_intent_research_kernel_ingress_evidence_gate.ci.v0`
- Example:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_evidence_gate.py`
- Runtime Matrix input:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Runtime Step Trace input:
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Runtime Coverage Policy input:
  `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
- Runtime Backend Alignment input:
  `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
- Global Evidence Gate binding:
  `examples/source_to_intent_research_evidence_gate.py`
- Global Proof Bundle binding:
  `examples/source_to_intent_research_proof_bundle.py`
- Capability claim consumer:
  `examples/source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`

## What It Gates

The gate validates and binds:

- Kernel Ingress E2E evidence;
- Kernel Ingress Runtime Matrix evidence;
- Kernel Ingress Runtime Step Trace evidence;
- Kernel Ingress Runtime Coverage Policy evidence;
- Kernel Ingress Runtime Backend Alignment evidence;
- Kernel Ingress Boundary Budget evidence;
- Kernel Ingress Rejection Coverage evidence;
- Kernel Ingress Diagnostics evidence;
- Kernel Ingress Conformance Gate evidence;
- Kernel Ingress Idiom Alignment evidence;
- Kernel Ingress Proof Bundle evidence.

It verifies that the Kernel Ingress Proof Bundle contains the exact digests for
the artifacts evaluated by the same gate invocation.

## Security Boundary

The gate consumes already-rendered metadata-only evidence. It does not import
Triton modules, evaluate decorators, execute `@triton.jit`, access files, access
devices, load plugins, run subprocesses, generate artifacts, or lower source
text to compiler artifacts.

The gate output is source-free and contains only digests, stable identifiers,
coverage counts, parser status, and pass/fail status.

The current gate binds four accepted Kernel Ingress runtime cases and three
unique backend sequences: `linear-sim->vector-sim`,
`vector-sim->vector-sim`, and
`linear-sim->vector-sim->vector-sim->vector-sim`.

## Review Meaning

This gate is the merge-facing audit for Kernel Ingress:

```text
kernel ingress evidence
runtime matrix
runtime step trace
runtime coverage policy
runtime backend alignment
boundary budget
rejection coverage
diagnostics
conformance
idiom alignment
proof bundle
    ->
kernel ingress evidence gate
    ->
research capability claim
```

Future Kernel Ingress syntax changes must update this gate before the expanded
syntax can count as accepted research scope, and must update the Research
Capability Claim before the high-level supported claim can expand.
