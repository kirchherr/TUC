# Runtime Planning Explanation

Runtime Planning Explanation v0 is a data-only report that summarizes why a
runtime `PartitionPlan` placed each operation where it did.

It is intentionally not a new planner. It reads the accepted plan and records:

- backend sequence
- selection kind
- assignment reason
- transfer and layout-conversion bytes
- produced layout and memory domain
- candidate-score visibility when scores were explicitly requested

## Artifact

The executable examples are:

```text
examples/runtime_planning_explanation.py
examples/runtime_mixed_planning_explanation.py
```

The deterministic goldens are:

```text
tests/golden/runtime_planning_explanation/systolic_report.json
tests/golden/runtime_planning_explanation/mixed_backend_equivalence_report.json
```

The schema is:

```text
schemas/runtime_planning_explanation_report.v0.schema.json
```

## Security Boundary

The report consumes an existing `PartitionPlan` object. It does not:

- import backend plugins
- discover backend entry points
- call backend lowering
- execute runtime kernels
- spawn subprocesses
- load dynamic libraries
- touch devices
- read benchmark output

It includes the Runtime Executor blocked execution surfaces to make clear that
planning explanation is review evidence, not execution permission.

## Relationship To Existing Planning Evidence

Runtime plan dumps are human-readable text fixtures. Compiler decision reports
show accepted and rejected capability diagnostics. Candidate Score Evidence
proves opt-in score visibility.

Runtime Planning Explanation sits beside those artifacts and gives reviewers a
compact schema-versioned summary of the accepted plan:

```text
PartitionPlan -> Runtime Planning Explanation
```

For the systolic proof graph, the report shows:

- `systolic_projection` selected through `preferred_for`
- `host_activation` selected through explicit `fallback`
- `blocked -> row_major` layout-conversion bytes are visible
- candidate scores are recorded for the selected systolic placement

This strengthens runtime planning explainability without changing placement
behavior or adding hardware-specific facts to HAC-IR.

Runtime Evidence Matrix and Runtime Evidence Gate now bind matching
backend-equivalence planning explanations under exact artifact IDs:
`runtime_planning_explanation_systolic` for the fallback-bearing systolic
slice and `runtime_planning_explanation_mixed` for the mixed accelerator
slice. The systolic binding checks the `systolic-sim,reference-cpu` candidate
sequence, recorded candidate-score visibility, and explicit fallback. The mixed
binding checks the `systolic-sim,vector-sim,vector-sim,vector-sim` candidate
sequence, recorded candidate-score visibility, no fallback, and visible
layout-conversion movement.
