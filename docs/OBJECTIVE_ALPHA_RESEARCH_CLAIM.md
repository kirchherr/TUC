# Objective Alpha Research Claim

Objective Alpha Research Claim v0 is the compact digest-only snapshot of the
current Universal Compute research claim.

It answers the reviewer question:

```text
What does Objective Alpha currently prove, and which claims remain blocked?
```

Run it with:

```bash
python examples/objective_alpha_research_claim.py
python examples/objective_alpha_research_claim_gate.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_research_claim_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_research_claim.json
```

## What It Binds

The claim snapshot binds these artifacts by SHA-256 metadata digest:

- Objective Alpha Public Proof Bundle.
- Objective Alpha Public Proof Bundle Gate.
- Objective Alpha Evidence Extension Policy.
- Objective Alpha Public Evidence Catalog.
- Objective Alpha Public Evidence Catalog Admission Gate.
- Source Intent Mixed Runtime Public Proof Bundle.

## Supported Claim

The supported scope is:

```text
objective_alpha_public_bundle_catalog_and_mixed_runtime_proof
```

The supported research claim is that the current Objective Alpha slice shows
hardware-independent compute intent flowing through capability-planned trusted
runtime execution, preserving public semantics across a mixed
`reference-cpu` versus `systolic-sim + vector-sim` proof path, while public
evidence remains digest-only and RFC-bound. The current public evidence surface is 16 fixed bundle entries plus 6 catalog entries, for 22 public evidence entries.

## Blocked Claims

The report keeps these claims blocked:

- native performance parity;
- vendor compiler replacement;
- broad source code parsing;
- arbitrary third-party backend execution;
- device access;
- generated artifact execution;
- production Triton integration.

## Security Boundary

The report serializes only bounded claim metadata and SHA-256 digests. It does
not serialize raw source, Source Intent payload bodies, tensor values, runtime
handles, device identifiers, host paths, commands, generated code, backend
artifacts, raw timing samples, raw benchmark output, or full supporting reports.

It does not execute catalog entry points, import frontend packages, discover
plugins, run Triton JIT, access devices, load dynamic libraries, spawn
subprocesses, touch the network, parse source, or authorize generated artifacts.

## Contract

- Example: `examples/objective_alpha_research_claim.py`
- Schema: `schemas/objective_alpha_research_claim_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_research_claim.json`
- Tests: `tests/test_objective_alpha_research_claim.py`
- Gate: [Objective Alpha Research Claim Gate](OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md)
- Gate doc path: `docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md`
- Gate example: `examples/objective_alpha_research_claim_gate.py`
- Gate schema: `schemas/objective_alpha_research_claim_gate_report.v0.schema.json`
- Gate golden: `tests/golden/proofs/objective_alpha_research_claim_gate.json`
- Gate RFC: `rfcs/0256-objective-alpha-research-claim-gate.md`
- RFC: `rfcs/0255-objective-alpha-research-claim.md`
