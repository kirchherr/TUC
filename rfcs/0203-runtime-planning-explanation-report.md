# RFC 0203: Runtime Planning Explanation Report

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Delta

## Summary

TUC adds a schema-versioned Runtime Planning Explanation report for accepted
`PartitionPlan` objects.

The report summarizes backend sequence, selection kind, assignment reason,
movement bytes, produced layout, memory domain, fallback count, and candidate
score visibility without changing planner behavior.

## Motivation

Runtime plan dumps, compiler decision reports, and candidate-score evidence
already make planning inspectable. Reviewers still need a compact machine-readable
answer to:

```text
Why did this operation run on this backend?
```

The new report turns that question into a bounded data artifact.

## Decision

Add `tuc.runtime.planning_explanation` with:

- `RuntimePlanningExplanationReport`
- `RuntimePlanningExplanationStep`
- `RuntimePlanningExplanationIssue`
- `build_runtime_planning_explanation_report(...)`
- `assert_runtime_planning_explanation(...)`
- deterministic JSON serialization and dump helpers

Add:

- `examples/runtime_planning_explanation.py`
- `docs/RUNTIME_PLANNING_EXPLANATION.md`
- `schemas/runtime_planning_explanation_report.v0.schema.json`
- deterministic golden evidence for the systolic proof plan

## Security Model

The report consumes only an already-built `PartitionPlan`.

It does not import backend plugins, discover entry points, call lowering,
execute kernels, spawn subprocesses, load dynamic libraries, touch devices, or
read benchmark output. It keeps the Runtime Executor blocked execution surfaces
visible in the report.

## Consequences

- Runtime planning explainability becomes schema-versioned evidence.
- Fallback assignments are visible as fallback, not hidden success.
- Layout-conversion and transfer bytes remain explicit.
- Candidate scores stay opt-in diagnostics rather than implicit global
  optimization.

## Alternatives Considered

1. Rely only on runtime-plan text dumps.

   Rejected because text dumps are useful for humans but weaker as composable
   evidence.

2. Parse compiler decision-report text.

   Rejected because the accepted `PartitionPlan` already contains the canonical
   planning facts.

3. Add new planner behavior.

   Rejected because this step is evidence-only. The planner remains
   deterministic and rule-based.

## Follow-Up

1. Add future planning explanation goldens only when a proof graph adds new
   placement or movement evidence.
2. Keep this report bound to the Runtime Evidence Matrix only if it becomes a
   required gate artifact.
3. Extend selection kinds only through RFC review.
