# Research Scope Claim Gate

Research Scope Claim Gate v0 is the project-level boundary that keeps TUC's
current claim explicitly research-scoped.

Run it with:

```bash
python examples/research_scope_claim_gate.py
```

The report is schema-versioned at:

```text
schemas/research_scope_claim_gate_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/research_scope_claim_gate.json
```

## What It Proves

The gate proves that the current project claim is still:

- a narrow research proof for hardware-independent compute intent;
- bound to Objective Alpha, Source-To-Intent capability, performance-boundary,
  and source-ingestion admission evidence by digest;
- metadata-only and source-free;
- not a production compiler claim;
- not a CUDA, ROCm, XLA, TVM, or IREE replacement claim;
- not a native performance, real-hardware execution, arbitrary source
  ingestion, external plugin execution, or generated-artifact execution claim.

It also records `time_horizon_claim = no_timeline_claim`, so the report does not
pretend to forecast when a production-grade compiler stack would exist.

## Bound Evidence

The gate binds these top-level artifacts:

- `objective_alpha_research_claim_gate`
- `source_to_intent_research_capability_claim_gate`
- `performance_proof_interpretation`
- `source_ingestion_admission_gate`

Each artifact is referenced by evidence ID, contract, status, source-free flag,
scope-support flag, and SHA-256 digest. No tensor values, source bodies,
runtime handles, device IDs, host paths, commands, generated code, backend
artifacts, or benchmark samples are serialized.

## Security Boundary

The gate validates already-produced metadata. It does not parse source, ingest
Triton or PyTorch programs, import packages, discover plugins, run generated
artifacts, access devices, call native backends, execute subprocesses, or open
network or filesystem surfaces.

## Contract

- Module: `src/tuc/research_scope_claim_gate.py`
- Example: `examples/research_scope_claim_gate.py`
- Schema: `schemas/research_scope_claim_gate_report.v0.schema.json`
- Golden: `tests/golden/proofs/research_scope_claim_gate.json`
- Tests: `tests/test_research_scope_claim_gate.py`
- RFC: `rfcs/0267-research-scope-claim-gate.md`
