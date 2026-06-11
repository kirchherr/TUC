# Runtime Candidate Scoring Policy

Runtime Candidate Scoring Policy v0 is the versioned review contract for the
current candidate-selection comparator.

Schema:
`schemas/runtime_candidate_scoring_policy.v0.schema.json`

Golden:
`tests/golden/runtime_candidate_scoring_policy/current_policy_report.json`

Example:

```bash
python examples/runtime_candidate_scoring_policy.py
```

## Active Comparator Order

Policy v0 documents the current deterministic sort order:

1. `transfer_score`, minimize
2. `layout_conversion_bytes`, minimize
3. `transfer_bytes`, minimize
4. `preferred_memory_domain_match`, prefer true
5. `backend_name_tiebreaker`, lexical ascending

This matches the current rule-based runtime planner. The policy report does not
change placement behavior.

The current planner behavior is checked by
[Runtime Candidate Scoring Conformance](RUNTIME_CANDIDATE_SCORING_CONFORMANCE.md).

## Blocked Components

The following components are intentionally blocked:

- `noise_penalty`
- `error_budget_margin`
- `calibration_confidence`
- `benchmark_score`

They may be added only after separate data models, schemas, golden evidence,
and security review exist. They must not enter HAC-IR as backend-specific
semantics or hidden optimization controls.

## Security Boundary

The policy is data-only. It does not discover plugins, import backend modules,
load dynamic libraries, spawn subprocesses outside the example process, access
devices, touch the network, execute generated artifacts, run JIT code, read host
paths, read environment variables, or use benchmark output.

The policy also keeps `automatic_global_optimization_enabled` and
`noise_error_budget_components_enabled` fixed to `false` for v0.
