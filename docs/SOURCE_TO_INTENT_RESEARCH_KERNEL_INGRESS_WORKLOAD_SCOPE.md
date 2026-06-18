# Source-To-Intent Research Kernel Ingress Workload Scope

Source-To-Intent Research Kernel Ingress Workload Scope v0 binds accepted
Kernel Ingress shape-profile evidence to diagnostic workload-scope review data.

It is a performance-boundary artifact, not a benchmark and not a native
performance proof.

## Contract

- Binding contract:
  `source_to_intent_research_kernel_ingress_workload_scope.performance_boundary.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_workload_scope_report.v0.schema.json`
- Source evidence:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- Workload-scope contract:
  `schemas/workload_scope_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_workload_scope.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_workload_scope.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_workload_scope.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

The report derives workload scopes from the accepted Kernel Ingress
shape-profile backend-equivalence evidence.

It records only:

- source evidence contract, schema version, and digest;
- workload-scope report schema version and digest;
- accepted profile IDs: `base`, `alternate`;
- accepted operation families: `elementwise`, `matmul`, `reduction`,
  `softmax`;
- diagnostic workload scopes with stable IDs, operation family, shape profile
  ID, dtype policy, problem-size bounds, and correctness-reference ID;
- blocked native-performance claim status.

The current report contains 20 workload scopes derived from:

- four accepted Kernel Ingress cases;
- two declared shape profiles;
- the operation families covered by each case.

## Security Boundary

The report is metadata-only and value-free. It does not embed raw module
source, extracted kernel source, Source Intent payloads, tensor values,
benchmark results, raw timing samples, generated code, backend binaries, host
paths, command lines, environment variables, device identifiers, or plugin
material.

It does not run benchmarks, access devices, inspect host hardware, import user
modules, execute decorators, load dynamic libraries, call subprocesses, perform
network access, discover plugins, or execute generated artifacts.

## Review Meaning

This artifact connects the practical Kernel Ingress proof to the performance
proof boundary:

```text
Kernel Ingress Shape-Profile Backend Equivalence
    -> source evidence digest
    -> Workload Scope Report v0
    -> Kernel Ingress Workload Scope binding
    -> Performance Proof Readiness marks workload_scope present
```

The claim remains blocked. This report only says that future performance
proposals now have bounded workload scopes for the current Kernel Ingress
research slice. It does not satisfy benchmark methodology, native baseline
comparison, planner-overhead evidence, break-even workload-size evidence,
leaky-abstraction evidence, executable-backend security review, or benchmark
artifact acceptance.
