# RFC 0184: Source-To-Intent Research Kernel Ingress Workload Scope

## Status

Accepted.

## Context

Kernel Ingress Backend Equivalence Shape Profiles proves that the current
accepted module-shaped Source Intent preserves public outputs and reference
correctness across `base` and `alternate` declared tensor shape profiles.

That evidence is useful for the Universal Compute research path, but it should
not accidentally become a native performance claim. The next practical step is
to bind those proven shape profiles to the existing diagnostic Workload Scope
Report so future performance proposals can only refer to bounded, reviewed
operation-family and shape-profile scopes.

## Decision

Add Source-To-Intent Research Kernel Ingress Workload Scope v0:

- `examples/source_to_intent_research_kernel_ingress_workload_scope.py`
- `schemas/source_to_intent_research_kernel_ingress_workload_scope_report.v0.schema.json`
- `tests/test_source_to_intent_research_kernel_ingress_workload_scope.py`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_workload_scope.json`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md`

The report validates the Kernel Ingress shape-profile evidence, derives
diagnostic `WorkloadScope` entries from the accepted cases, emits a digest of
the standard `workload_scope_report.v0`, and keeps native performance claims
blocked.

The report contains 20 scopes:

- four accepted Kernel Ingress cases;
- two declared shape profiles;
- one scope per covered operation family in each profile case.

## Security Boundary

The report must remain metadata-only and value-free. It must not contain raw
module source, Python source, `@triton.jit`, Source Intent payloads, tensor
values, benchmark output, raw timing samples, generated code, backend binaries,
command lines, host paths, environment variables, device identifiers, plugin
manifests, or raw comparison outputs.

The report must not import user modules, execute decorators, run benchmarks,
access devices, discover plugins, call subprocesses, perform network access,
load dynamic libraries, or execute generated artifacts.

## Evidence Wiring

The CI workflow runs:

- `examples/source_to_intent_research_kernel_ingress_workload_scope.py`

The Performance Proof Readiness report may now mark `workload_scope` present
for the current blocked native-performance proposal while keeping every other
required performance-proof evidence item missing.

## Consequences

Future performance proposals have a concrete workload-scope boundary tied to
the current Kernel Ingress proof. This is progress toward a falsifiable
performance-proof process, but it still does not prove native performance,
planner benefit, dynamic-shape performance, native baseline comparison,
benchmark methodology, leaky-abstraction coverage, executable-backend
security, or benchmark artifact acceptance.
