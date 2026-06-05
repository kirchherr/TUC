# Compiler Decision Report

The compiler decision report records backend-selection facts that are useful
before runtime partitioning becomes more sophisticated.

It is a pure-data report. It does not execute backend code.

## Purpose

`CompilerDecisionReport` explains, for each operation:

- Which backend was selected by the partition plan.
- Which registered backend capabilities were evaluated.
- Whether each backend accepted or rejected the operation.
- Which reason code explains the support decision.

The report bridges backend capability diagnostics and compiler-level review.
It helps maintainers see not just the final assignment, but also the rejected
candidates that shaped that decision.

## API

Every `CompilationResult` includes a decision report:

```python
result = compile_graph(graph, backend_capabilities)

report = result.decision_report
projection = report.operation("projection")
```

It can also be dumped deterministically:

```python
print(result.dump_decision_report())
```

Example:

```text
compiler.decisions @mlp {
  operation projection kind=matmul selected=linear-sim {
    linear-sim supported=true reason="accepted" detail="capability accepts operation kind, layout, and error budget"
  }
}
```

## Security Model

Decision reports are generated from:

- Validated `ComputeGraph` operation data.
- Registry-owned `BackendCapability` data.
- The already-created `PartitionPlan`.

They do not:

- Import backend modules.
- Call backend `lower`.
- Spawn subprocesses.
- Load dynamic libraries.
- Open devices.
- Execute artifacts.
- Include host paths, device identifiers, imported module names, or backend
  execution output.

This keeps compiler explainability separate from backend execution and plugin
lifecycle concerns.

## Future Use

The report is intentionally small now. Future cost-model and heterogeneous
runtime work can add:

- Candidate scores.
- Transfer-cost reasoning.
- Noise/robustness tradeoffs.
- Calibration requirements.
- Rejected rewrite or partition alternatives.

Those additions should remain deterministic and reviewable.
