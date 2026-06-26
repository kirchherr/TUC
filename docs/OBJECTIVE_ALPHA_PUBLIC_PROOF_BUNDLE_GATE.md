# Objective Alpha Public Proof Bundle Gate

Objective Alpha Public Proof Bundle Gate v0 is a data-only audit report for the
first public TUC proof bundle.

Run it from the repository root:

```bash
python examples/objective_alpha_public_proof_bundle_gate.py
```

The gate answers one narrow review question:

```text
Does the current Objective Alpha Public Proof Bundle still expose the accepted
fixed evidence entries, fixed entry points, fixed artifact kinds, digest-only raw
output policy, and blocked non-claims?
```

The fixed invariants also make Runtime Transfer Trace Index and Runtime Layout
Conversion Trace Index explicit public bundle entries, so reviewers can see that
trace-order and layout-transition evidence remain directly exposed rather than
only implied by replay or binding reports.

## Contract

- Report schema:
  `schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json`
- Report schema version:
  `tuc.objective_alpha_public_proof_bundle_gate_report.v0`
- Evidence contract:
  `objective_alpha.public_proof_bundle_gate.data_only.v0`
- Example: `examples/objective_alpha_public_proof_bundle_gate.py`
- Golden:
  `tests/golden/proofs/objective_alpha_public_proof_bundle_gate_report.json`
- Source bundle: `examples/objective_alpha_public_proof_bundle.py`
- Decision: `rfcs/0230-objective-alpha-public-proof-bundle-gate.md`

## Security Boundary

The gate validates an in-memory trusted bundle model and emits only bounded
metadata: bundle digest, entry count, entry IDs, entry points, artifact kinds,
required invariants, claim flags, blocked claims, blocked execution surfaces,
and derived issue status.

It does not execute bundle entry point strings, resolve paths, discover plugins,
access devices, run JIT code, spawn subprocesses, touch the network, load dynamic
libraries, parse source, or authorize native execution.

It does not serialize tensor values, runtime handles, host paths, command lines,
device identifiers, backend artifacts, generated code, source text, raw timing
samples, or raw benchmark output.

## Review Meaning

This gate is not an additional numeric correctness proof. It is a stable review
surface that keeps the public Objective Alpha proof bundle from drifting while
the project keeps adding evidence below it.