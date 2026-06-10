# Runtime Candidate Score Evidence

Runtime Candidate Score Evidence v0 is the review artifact for opt-in runtime
candidate score diagnostics.

It verifies that:

- default runtime planning emits no candidate scores
- opt-in runtime planning emits bounded candidate score records
- compiler decision reports carry the same score records, verified by digest
- each operation has exactly one selected candidate
- rejected candidate evidence remains visible

Schema:
`schemas/runtime_candidate_score_evidence_report.v0.schema.json`

Golden:
`tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json`

Example:

```bash
python examples/runtime_candidate_score_evidence.py
```

## Security Boundary

The report is data-only. It consumes already-built runtime planning artifacts and
compiler decision reports; it does not discover plugins, import backend modules,
load dynamic libraries, spawn subprocesses outside the example process, access
devices, touch the network, execute generated artifacts, run JIT code, read host
paths, or read environment variables.

Candidate scores remain diagnostics. They are not automatic global
optimization, benchmark evidence, native performance proof, backend approval, or
runtime execution permission.

## Acceptance

The report passes only when:

- `default_plan_candidate_score_count` is `0`
- `candidate_score_count` is nonzero
- `compiler_decision_candidate_score_count` matches the runtime plan score count
- `compiler_decision_candidate_score_digest` matches the runtime score digest
- every operation has exactly one selected score
- at least one rejected candidate is present
- all derived issues are empty
