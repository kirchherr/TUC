# Runtime Memory Budget

Runtime Memory Budget v0 is a data-only report that checks a Runtime Allocation
Plan against explicit memory-domain budgets.

Schema:
`schemas/runtime_memory_budget_report.v0.schema.json`

Golden:
`tests/golden/runtime_memory_budget/current_report.json`

Example:

```bash
python examples/runtime_memory_budget.py
```

## What It Records

The report records:

- source Allocation Plan contract and issue count
- source Allocation Plan metadata digest
- explicit budgets per memory domain
- reserved bytes per used memory domain
- peak live bytes per used memory domain
- pass/fail status for each used domain
- derived issues for missing or exceeded budgets

## Why It Exists

Runtime Allocation Plan v0 proves planned slot bindings. Runtime Memory Budget
v0 adds a resource-exhaustion boundary before TUC grows real memory pools,
device allocation, alias analysis, or allocator behavior.

The source Allocation Plan metadata digest binds a budget report to the
allocation-plan evidence from which its usages were derived. This prevents a
stale or forged budget report from being accepted as review evidence for a
different allocation plan.

Budgets are explicit data. The report does not ask the host or device how much
memory exists and does not infer capacity from hardware-specific APIs.

## Security Boundary

The report is data-only. It consumes a bounded `RuntimeAllocationPlanReport`
plus explicit `RuntimeMemoryDomainBudget` values, derives all usages and issues,
and serializes deterministic JSON.

It does not allocate memory, query devices, discover plugins, import backend
modules, load dynamic libraries, spawn subprocesses outside the example
process, touch the network, execute generated artifacts, run JIT code, read
host paths, read environment variables, load benchmark output, or authorize
executable backend surfaces.

## Current Limitations

- Budgets are example/static review data, not discovered hardware capacity.
- Peak live bytes are conservative and operation-index based.
- No memory pools, allocator handles, stream overlap, synchronization, or
  device allocation is modeled.
- A passing budget report does not mean execution is authorized.
