# Objective Alpha Public Proof Bundle

Objective Alpha Public Proof Bundle v0 gives reviewers one digest-only JSON
artifact for the first public TUC proof path.

Run it from the repository root:

```bash
python examples/objective_alpha_public_proof_bundle.py
```

The bundle links these trusted in-repository evidence entry points:

- `python examples/proof_of_execution.py`
- `python examples/runtime_evidence_matrix.py`
- `python examples/runtime_evidence_gate.py`
- `python examples/proof_of_backend_equivalence.py`
- `python examples/runtime_execution_output_closure.py`
- `python examples/runtime_transfer_trace_index.py`
- `python examples/runtime_transfer_trace_replay_verifier.py`
- `python examples/runtime_backend_equivalence_transfer_binding.py`
- `python examples/runtime_layout_conversion_trace_index.py`
- `python examples/runtime_layout_conversion_trace_replay_verifier.py`
- `python examples/runtime_backend_equivalence_layout_binding.py`
- `python examples/runtime_allocation_reconciliation.py`
- `python examples/runtime_memory_planning_gate.py`
- `python examples/research_onboarding_evidence.py`

Each entry is represented by a SHA-256 digest. The bundle does not embed raw
proof output, tensor values, timing samples, source text, backend artifacts, or
host paths.

## Non-Claims

The bundle proves the current Objective Alpha correctness and inspectability
path is present and internally bound. It does not claim native performance
parity, vendor compiler replacement, broad source parsing, arbitrary third-party
backend execution, device access, or generated-artifact execution.

## Security Boundary

The example runs only trusted in-repository proof/evidence builders, including
Proof Of Backend Equivalence, Runtime Execution Output Closure, transfer trace
index, replay, and binding, layout trace index, replay, and binding,
allocation reconciliation, and Runtime Memory Planning Gate as separate
digest-only entries. The bundle model accepts only fixed evidence
IDs, fixed entry points, fixed artifact kinds,
passed status, digest-only raw output policy, and SHA-256 digests.

Schema and fixtures:

- Schema: `schemas/objective_alpha_public_proof_bundle.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_public_proof_bundle.json`
- Example: `examples/objective_alpha_public_proof_bundle.py`
- Tests: `tests/test_objective_alpha_public_proof_bundle.py`
- Gate: [Objective Alpha Public Proof Bundle Gate](OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md)
- Gate doc: `docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md`
- Gate schema: `schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json`
- Gate example: `examples/objective_alpha_public_proof_bundle_gate.py`
- Decisions: `rfcs/0206-objective-alpha-public-output-closure-entry.md`,
  `rfcs/0224-proof-of-backend-equivalence-entrypoint.md`,
  `rfcs/0225-runtime-layout-conversion-trace-index.md`,
  `rfcs/0226-objective-alpha-transfer-evidence-entries.md`,
  `rfcs/0227-objective-alpha-backend-equivalence-proof-entry.md`,
  `rfcs/0228-objective-alpha-layout-evidence-entries.md`,
  `rfcs/0229-objective-alpha-allocation-reconciliation-entry.md`
