# Objective Beta Research Claim Gate

Objective Beta Research Claim Gate v0 is the CI-facing gate for the Objective
Beta snapshot. It binds the serialized Objective Beta claim by digest and fails
closed if the claim changes shape, opens source ingestion, enables native
performance claims, or drifts away from the fixed evidence order.

The next reproducibility layer is the
[Objective Beta Reproducibility Capsule](OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md),
which binds this gate and all direct Beta evidence into an independently
replayable eleven-artifact closure.

Run it with:

```bash
python examples/objective_beta_research_claim_gate.py
```

Schema:

```text
schemas/objective_beta_research_claim_gate_report.v0.schema.json
```

Golden:

```text
tests/golden/proofs/objective_beta_research_claim_gate.json
```

## Gate Contract

The gate passes only while:

- `gate_passed = true`.
- `claim_contract = objective_beta.research_claim.digest_snapshot.v0`.
- Objective Alpha, Kernel Ingress, First Real Triton Path, first-slice evidence,
  admission readiness, maintainer approval request, research scope, OCI kernel
  isolation, and OCI release-provenance readiness evidence remain bound in the
  expected order.
- `source_ingestion_admitted = false`.
- `admission_ready = false`.
- `surface_opened = false`.
- `native_performance_claim = false`.
- `vendor_replacement_claim = false`.

## Security Boundary

The gate validates only source-free claim metadata and digests. It does not
execute source, run JIT, touch devices, discover plugins, load generated
artifacts, or serialize raw values.

## Contract

- Claim Doc: `docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md`
- Claim Example: `examples/objective_beta_research_claim.py`
- Claim Schema: `schemas/objective_beta_research_claim_report.v0.schema.json`
- Claim Golden: `tests/golden/proofs/objective_beta_research_claim.json`
- Gate Example: `examples/objective_beta_research_claim_gate.py`
- Gate Schema: `schemas/objective_beta_research_claim_gate_report.v0.schema.json`
- Gate Golden: `tests/golden/proofs/objective_beta_research_claim_gate.json`
- Tests: `tests/test_objective_beta_research_claim_gate.py`
- RFC: `rfcs/0280-objective-beta-research-claim-gate.md`
