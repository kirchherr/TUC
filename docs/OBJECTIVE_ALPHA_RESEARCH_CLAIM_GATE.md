# Objective Alpha Research Claim Gate

Objective Alpha Research Claim Gate v0 is the CI-facing binding for the current
Objective Alpha Research Claim snapshot.

Run it with:

```bash
python examples/objective_alpha_research_claim_gate.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_research_claim_gate_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_research_claim_gate.json
```

## What It Proves

The gate proves that the current Objective Alpha Research Claim still binds the
expected claim contract, evidence IDs, claim digest, claim metadata digest,
entry counts, supported claims, blocked claims, and required invariants.

It fails closed if the claim digest drifts, if evidence IDs reorder, if public
bundle or catalog counts change from the current 16 + 6 = 22 public evidence surface, or if native performance, vendor replacement,
or broad source parser claims are enabled.

## Security Boundary

The gate validates serialized claim-report data and emits bounded metadata. It
does not execute catalog entry points, parse source, import frontend packages,
discover plugins, run Triton JIT, access devices, load dynamic libraries, spawn
subprocesses, touch the network, or authorize generated artifacts.

## Contract

- Example: `examples/objective_alpha_research_claim_gate.py`
- Schema: `schemas/objective_alpha_research_claim_gate_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_research_claim_gate.json`
- Tests: `tests/test_objective_alpha_research_claim_gate.py`
- Claim: [Objective Alpha Research Claim](OBJECTIVE_ALPHA_RESEARCH_CLAIM.md)
- RFC: `rfcs/0256-objective-alpha-research-claim-gate.md`
