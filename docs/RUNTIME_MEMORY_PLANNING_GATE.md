# Runtime Memory Planning Gate

Runtime Memory Planning Gate v0 is the CI-facing check for the current runtime
memory-planning evidence surface.

It runs:

- `build_current_runtime_buffer_lifetime_report()`
- `build_current_runtime_allocation_plan_report()`
- `build_current_runtime_memory_budget_report()`
- `examples/runtime_memory_planning_gate.py`

The gate passes only when:

- Runtime Allocation Plan passes
- Runtime Memory Budget passes
- the Allocation Plan source lifetime metadata digest matches the Buffer
  Lifetime report evaluated by the same gate invocation
- the reports refer to the same graph and operation count across their binding
  checks
- the Memory Budget source allocation metadata digest matches the Allocation
  Plan evaluated by the same gate invocation

Golden output:

```text
tests/golden/runtime_memory_planning_gate/current_gate.txt
```

CI entry:

```text
.github/workflows/ci.yml
```

## Security Boundary

The gate composes bounded data-only reports. It does not allocate memory,
discover plugins, import backend modules, load dynamic libraries, spawn
subprocesses outside the example process, access devices, touch the network,
execute generated artifacts, run JIT code, read host paths, read environment
variables, load raw benchmark output, or authorize executable backend surfaces.

## Review Meaning

The gate is not a memory allocator and not an execution authorization. It is a
merge-time confidence check that allocation-slot evidence and explicit
memory-domain budgets remain internally consistent before TUC accepts future
memory pools, aliasing, device allocation, or allocator behavior.

The allocation digest binding prevents stale memory-budget evidence from being
accepted for a different allocation plan.

The lifetime digest binding prevents stale allocation-plan evidence from being
accepted for a different buffer-lifetime report.
