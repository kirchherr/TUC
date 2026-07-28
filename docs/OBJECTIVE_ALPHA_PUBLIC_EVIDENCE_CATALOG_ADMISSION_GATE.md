# Objective Alpha Public Evidence Catalog Admission Gate

Objective Alpha Public Evidence Catalog Admission Gate v0 is the machine-checkable
review gate for the public evidence catalog growth surface.

Run it with:

```bash
python examples/objective_alpha_public_evidence_catalog_admission_gate.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json
```

## What It Proves

The gate proves that the current
[Objective Alpha Public Evidence Catalog](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
still passes the fixed v0 admission rules:

- the catalog itself passes;
- the catalog metadata digest is bound into the gate;
- the fixed Objective Alpha Public Proof Bundle remains the stable full anchor;
- the Extension Policy contract and digest are bound;
- the Runtime Backend Equivalence Portfolio digest is bound;
- the Source-To-Intent Kernel Ingress Proof Bundle digest is bound;
- the Source Intent Mixed Runtime Public Proof Bundle digest is bound;
- the Source-To-Intent Research Capability Claim Gate digest is bound;
- the First Real Triton Kernel Path digest is bound;
- the Real Triton First Slice Evidence Portfolio digest is bound;
- the initial governance entry, first runtime-proof entry,
  frontend-runtime-proof entries, and claim-boundary entry are fixed;
- required extension-tier coverage is complete for `governance`,
  `runtime_proof`, `frontend_runtime_proof`, and `claim_boundary`;
- catalog growth is append-only and RFC-bound;
- catalog entries remain digest-only and source-free;
- blocked claims and blocked execution surfaces are preserved.

The companion [Objective Alpha Catalog Acyclicity Gate](OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md)
scans the fixed catalog-entry evidence artifacts and verifies that entries do
not depend on downstream catalog or claim gates. It is emitted by
`examples/objective_alpha_catalog_acyclicity_gate.py`, schema-versioned at
`schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json`, and
has golden evidence at
`tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json`.

## Security Boundary

The gate validates trusted in-memory report objects and emits only bounded
metadata. It does not execute catalog entry points, resolve paths, discover
plugins, access devices, load dynamic libraries, spawn subprocesses, run JIT
code, touch the network, parse source, or authorize generated artifacts.

It does not serialize tensor values, source text, runtime handles, host paths,
device identifiers, backend artifacts, raw timing samples, or raw benchmark
output.

## Contract

- Example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- Schema:
  `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- Golden:
  `tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json`
- Tests: `tests/test_objective_alpha_public_evidence_catalog_admission_gate.py`
- Gate decision:
  `rfcs/0234-objective-alpha-public-evidence-catalog-admission-gate.md`
- Companion acyclicity gate:
  `docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md`
- Companion acyclicity gate decision:
  `rfcs/0276-objective-alpha-catalog-acyclicity-gate.md`
- First runtime-proof entry decision:
  `rfcs/0235-objective-alpha-backend-equivalence-portfolio-catalog-entry.md`
- First frontend-runtime-proof entry decision:
  `rfcs/0237-objective-alpha-kernel-ingress-proof-bundle-catalog-entry.md`
- Source Intent Mixed Runtime Public Proof Bundle catalog-entry decision:
  `rfcs/0254-objective-alpha-source-intent-mixed-runtime-public-proof-catalog-entry.md`
- Catalog extension-tier coverage decision:
  `rfcs/0238-objective-alpha-catalog-extension-tier-coverage.md`
- Capability Claim Gate catalog-entry decision:
  `rfcs/0240-objective-alpha-capability-claim-gate-catalog-entry.md`
- First Real Triton Kernel Path catalog-entry decision:
  `rfcs/0273-objective-alpha-first-real-triton-kernel-path-catalog-entry.md`
- Real Triton First Slice Evidence Portfolio catalog-entry decision:
  `rfcs/0275-objective-alpha-real-triton-first-slice-portfolio-catalog-entry.md`

