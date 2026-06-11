# RFC 0096: Backend Author Readiness Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Gamma

## Summary

Add a schema-versioned Backend Author Readiness report that summarizes the
external backend author path as one deterministic pass/fail artifact.

## Motivation

Backend author onboarding now includes Manifest Claim Review, explicit registry
loading, compiler planning, backend conformance, and trusted lowering. Each
piece has evidence, but maintainers need one compact report that says whether
the complete author path is ready.

## Decision

Add:

- [Backend Author Readiness](../docs/BACKEND_AUTHOR_READINESS.md)
- `src/tuc/backends/author_readiness.py`
- `schemas/backend_author_readiness_report.v0.schema.json`
- `examples/backend_author_readiness.py`
- golden report at
  `tests/golden/backend_author_readiness/external_vector_readiness_report.json`
- focused tests in `tests/test_backend_author_readiness.py`

The report contains the fixed check sequence:

1. `manifest_claim_review`
2. `manifest_registry`
3. `compiler_assignment`
4. `backend_conformance`
5. `assigned_subgraph_lowering`

Issues are derived from failed checks. Authors cannot hand-write a passing
report over failed evidence.

## Security Model

The readiness report is data-only and summary-only. It does not load manifests,
scan directories, discover plugins, import backend modules, instantiate backend
objects, spawn subprocesses, access devices, touch the network, load dynamic
libraries, execute generated artifacts, run JIT code, or authorize runtime
execution.

Report fields are bounded identifiers, statuses, and issue codes. Reports must
not include host paths, source text, command lines, environment variables,
device identifiers, raw benchmark output, generated code, backend artifact
contents, or raw exception strings.

## Consequences

- Backend author onboarding now has one top-level readiness artifact.
- The external-vector toy backend demonstrates the complete readiness path.
- The report strengthens external integration without opening plugin or runtime
  execution surfaces.
- Readiness remains review evidence, not hardware certification.

## References

- [Backend Author Readiness](../docs/BACKEND_AUTHOR_READINESS.md)
- [Backend Author Certification](../docs/BACKEND_AUTHOR_CERTIFICATION.md)
- [Manifest Claim Review](../docs/MANIFEST_CLAIM_REVIEW.md)
- `examples/external_backend_author_path.py`
- `examples/backend_author_readiness.py`
