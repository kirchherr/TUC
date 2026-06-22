# RFC 0202: Backend Capability Coverage Matrix

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Gamma

## Summary

TUC adds a pure-data Backend Capability Coverage report that records which
backend capability descriptions cover the current neutral operation families.

The report is schema-versioned, deterministic, and execution-free. It sits
between capability authoring and backend conformance.

## Motivation

Backend conformance proves that a trusted in-process backend object behaves
consistently with its declared capability. Before reaching that point, reviewers
also need a simple data-only answer to a smaller question:

```text
Do the current capability descriptions cover the operation families that TUC
claims in the proof path?
```

Without this view, capability progress is scattered across registry diagnostics,
author-readiness reports, conformance reports, and examples.

## Decision

Add `tuc.backends.capability_coverage` with:

- `BackendCapabilityCoverageReport`
- `BackendCapabilityCoverageRow`
- `BackendCapabilityCoverageIssue`
- `build_backend_capability_coverage_report(...)`
- `assert_backend_capability_coverage(...)`
- deterministic JSON serialization and dump helpers

Add:

- `examples/backend_capability_coverage.py`
- `docs/BACKEND_CAPABILITY_COVERAGE.md`
- `schemas/backend_capability_coverage_report.v0.schema.json`
- golden test evidence under `tests/golden/backend_capability_coverage/`

## Security Model

The coverage report consumes `BackendCapability` data only. It does not:

- import backend plugins
- instantiate third-party backend code
- run lowering
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- read benchmark outputs

The report carries the Runtime Executor blocked execution surfaces to make this
boundary visible.

## Consequences

- Reviewers can see MVP operation-family coverage in one artifact.
- Capability gaps are reported before backend conformance or runtime execution.
- Backend authors get a clearer pre-conformance target.
- HAC-IR remains neutral because hardware facts still live in capability data,
  not in the compute-intent layer.

## Alternatives Considered

1. Use backend conformance alone.

   Rejected because conformance requires trusted backend objects and lowering
   behavior. Coverage should be available from declarative capability data.

2. Put coverage inside the registry.

   Rejected because registry diagnostics are per operation. The matrix is a
   review artifact across operation families and backend sets.

3. Treat missing coverage as runtime fallback.

   Rejected because fallback hides capability-model gaps and weakens
   inspectability.

## Follow-Up

1. Add CI-facing gate composition only if coverage becomes a required release
   artifact.
2. Extend rows when future operation families are accepted into HAC-IR.
3. Keep native performance claims separate from capability coverage.
