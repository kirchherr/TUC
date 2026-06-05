# RFC 0018: Backend Author Certification

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds a Backend Author Certification checklist and executable negative-test
template for prototype backend contributors.

## Motivation

Backend API v0.1 is now documented, but external authors need a concrete review
bar before adding backend-specific code. The most important early failure mode
is opening an execution surface through manifests, capability checks, plugin
fields, or lower-time shortcuts.

## Decision

Add:

- `docs/BACKEND_AUTHOR_CERTIFICATION.md`
- `tests/test_backend_author_negative_template.py`

Update Backend API, README, development environment, security baseline, and
roadmap status to reference the certification path.

## Security Model

The certification checklist keeps backend onboarding declarative:

- Capability manifests remain pure data.
- Plugin-like fields are rejected.
- Duplicate keys and unknown schemas are rejected.
- False `preferred_for` claims are rejected.
- Unsupported layouts are not accepted by capability checks.
- Backend lowering must reject unsupported operations before artifact emission.

This RFC does not add plugin discovery, subprocess execution, dynamic library
loading, device access, artifact execution, network access, or sandboxing.

## Consequences

- Backend authors have a copyable negative-test baseline.
- Maintainers have a consistent review checklist.
- TUC strengthens the backend boundary without expanding the runtime surface.

## Follow-Up

1. Add backend conformance fixtures once more operation semantics stabilize.
2. Add artifact sandboxing RFC before any backend artifact can execute.
3. Add plugin lifecycle RFC before external packages can be discovered.
4. Add native sanitizer and fuzzing gates before native backend code is loaded.
