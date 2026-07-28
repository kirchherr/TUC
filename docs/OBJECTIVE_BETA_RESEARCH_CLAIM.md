# Objective Beta Research Claim

Objective Beta Research Claim v0 is the successor research snapshot after
Objective Alpha. It does not replace Alpha; it proves that Alpha remains bound
while the newer realistic Kernel Ingress and first Real Triton slice evidence
are also reviewable as one source-free, digest-only milestone.

Run it with:

```bash
python examples/objective_beta_research_claim.py
```

Schema:

```text
schemas/objective_beta_research_claim_report.v0.schema.json
```

Golden:

```text
tests/golden/proofs/objective_beta_research_claim.json
```

## What It Binds

Objective Beta binds:

- Objective Alpha Research Claim Gate.
- Source-To-Intent Research Kernel Ingress Proof Bundle.
- First Real Triton Kernel Path.
- Real Triton First Slice Evidence Portfolio.
- Real Triton First Slice Admission Readiness Gate.
- Real Triton First Slice Maintainer Approval Request.
- Research Scope Claim Gate.

The claim records `claim_passed = true` for the bounded research scope while
keeping `source_ingestion_admitted = false`, `admission_ready = false`,
`surface_opened = false`, `native_performance_claim = false`, and
`vendor_replacement_claim = false`.

## Meaning

Objective Beta is the first top-level snapshot where the project can say:

```text
Objective Alpha proof remains valid.
Realistic Kernel Ingress evidence is bound.
The first Real Triton path is reviewable.
The first source-ingestion slice is review-ready.
Admission still remains fail-closed until external approval exists.
```

That is the correct research posture for TUC: stronger evidence, still bounded
claims.

## Security Boundary

The claim reads only fixed Golden evidence artifacts and emits bounded metadata
and SHA-256 digests. It does not execute source, import frontend packages,
discover plugins, run Triton JIT, access devices, load dynamic libraries, spawn
subprocesses, touch the network, emit generated artifacts, serialize source
text, serialize Source Intent payloads, serialize tensor values, or grant
source-ingestion admission.

## Contract

- Example: `examples/objective_beta_research_claim.py`
- Schema: `schemas/objective_beta_research_claim_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_beta_research_claim.json`
- Tests: `tests/test_objective_beta_research_claim.py`
- Gate: `docs/OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md`
- Gate Example: `examples/objective_beta_research_claim_gate.py`
- Gate Schema: `schemas/objective_beta_research_claim_gate_report.v0.schema.json`
- Gate Golden: `tests/golden/proofs/objective_beta_research_claim_gate.json`
- RFC: `rfcs/0279-objective-beta-research-claim.md`
- Gate RFC: `rfcs/0280-objective-beta-research-claim-gate.md`