# Runtime Memory Planning Gate

Runtime Memory Planning Gate v0 is the CI-facing check for the current runtime
memory-planning evidence surface.

It runs:

- `build_current_runtime_buffer_lifetime_report()`
- `build_current_runtime_allocation_plan_report()`
- `build_current_runtime_memory_budget_report()`
- `build_runtime_allocation_request_manifest_report()`
- `build_runtime_allocation_admission_report()`
- `build_runtime_allocation_receipt_report()`
- `build_runtime_allocation_reconciliation_report()`
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
- the Runtime Allocation Request Manifest passes and is bound to the Allocation
  Plan and Memory Budget evaluated by the same gate invocation
- Runtime Allocation Admission passes and is bound to the Request Manifest and
  Memory Budget evaluated by the same gate invocation
- Runtime Allocation Receipt passes and is bound to the Allocation Admission
  evaluated by the same gate invocation
- Runtime Allocation Reconciliation passes and is bound to the same Allocation
  Admission and Allocation Receipt evaluated by the same gate invocation

Schema coverage:

```text
schemas/runtime_allocation_request_manifest_report.v0.schema.json
schemas/runtime_allocation_admission_report.v0.schema.json
schemas/runtime_allocation_receipt_report.v0.schema.json
schemas/runtime_allocation_reconciliation_report.v0.schema.json
```

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
expose pointers, expose runtime handles, discover plugins, import backend modules, load dynamic
libraries, spawn subprocesses outside the example process, access devices,
touch the network, execute generated artifacts, run JIT code, read host paths,
read environment variables, load raw benchmark output, or authorize executable
backend surfaces.

## Review Meaning

The gate is not a memory allocator and not an execution authorization. It is a
merge-time confidence check that allocation-slot evidence and explicit
memory-domain budgets remain internally consistent before TUC accepts future
memory pools, aliasing, device allocation, or allocator behavior.

The allocation digest binding prevents stale memory-budget evidence from being
accepted for a different allocation plan.

The lifetime digest binding prevents stale allocation-plan evidence from being
accepted for a different buffer-lifetime report.

The allocation-request manifest binding prevents stale future allocator request
evidence from being accepted for a different Allocation Plan or Memory Budget.

The allocation-admission binding prevents allocator-admission evidence from being
accepted unless it is tied to the same Request Manifest and Memory Budget.

The allocation-receipt binding prevents dry-run allocator receipt evidence from
being accepted unless it is tied to the same Allocation Admission.

The allocation-reconciliation binding prevents stale or inconsistent Admission/Receipt ledgers from being accepted before any real allocator surface is introduced.
