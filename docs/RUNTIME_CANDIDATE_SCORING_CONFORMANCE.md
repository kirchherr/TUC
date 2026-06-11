# Runtime Candidate Scoring Conformance

Runtime Candidate Scoring Conformance v0 verifies that the runtime planner's
observable candidate selection behavior matches
[Runtime Candidate Scoring Policy](RUNTIME_CANDIDATE_SCORING_POLICY.md).

Schema:
`schemas/runtime_candidate_scoring_conformance_report.v0.schema.json`

Golden:
`tests/golden/runtime_candidate_scoring_conformance/current_conformance_report.json`

Example:

```bash
python examples/runtime_candidate_scoring_conformance.py
```

## Covered Cases

The report runs five bounded in-memory planning cases:

1. `transfer_score_latency_prefers_lower`
2. `layout_conversion_bytes_recorded`
3. `transfer_bytes_tiebreaker`
4. `preferred_memory_domain_match_tiebreaker`
5. `backend_name_tiebreaker`

Together they cover the active policy order:

1. `transfer_score`
2. `layout_conversion_bytes`
3. `transfer_bytes`
4. `preferred_memory_domain_match`
5. `backend_name_tiebreaker`

The cases are deliberately small. They are not benchmarks and they do not claim
global optimality. Their purpose is to catch accidental comparator drift before
candidate scoring becomes richer.

The CI-facing
[Runtime Candidate Scoring Gate](RUNTIME_CANDIDATE_SCORING_GATE.md) requires
this conformance report to pass.

## Security Boundary

The conformance report is data-only. It constructs typed `ComputeGraph` and
`BackendCapability` fixtures in memory, calls the existing deterministic
planner with `include_candidate_scores=True`, and serializes bounded report
fields.

It does not discover plugins, import backend modules, load dynamic libraries,
spawn subprocesses outside the example process, access devices, touch the
network, execute generated artifacts, run JIT code, read host paths, read
environment variables, load benchmark output, or approve executable backend
surfaces.

## Review Use

Use this report before changing candidate score comparator semantics. A change
that modifies the selected backend, case order, active component coverage, or
schema contract is a runtime planning behavior change and should update the
policy, this conformance report, the golden evidence, and reviewer-facing
roadmap notes together.
