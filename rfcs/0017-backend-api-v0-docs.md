# RFC 0017: Backend API v0.1 Documentation

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds a Backend API v0.1 authoring guide for external prototype backend
authors.

The guide documents:

- `BackendCapability`
- `Backend`
- `LoweringResult`
- Backend capability manifests.
- Transfer-cost profile manifests.
- HAC-IR and HS-IR contract dependencies.
- Security rules and current limitations.

## Motivation

TUC's backend surface has become concrete enough to explain to external
authors, but the project must avoid implying that arbitrary third-party backend
code can be loaded safely. The correct v0.1 message is capability-first and
documentation-first: declare what a backend can accept, let TUC create
inspectable plans, and lower only through explicitly constructed trusted
prototype objects.

## Decision

Add:

- `docs/BACKEND_API.md`
- `examples/backend_api_v0.py`

Update README, architecture, development environment, security baseline, and
roadmap status to reference the Backend API v0.1 guide.

## Security Model

Backend API v0.1 is not a plugin ABI.

It does not add:

- Auto-discovery.
- Python import hooks.
- Subprocess execution.
- Dynamic library loading.
- Device enumeration.
- Artifact execution.
- Network access.

Capability manifests and transfer-cost profiles remain schema-versioned,
bounded, duplicate-key rejecting, and unknown-field rejecting. Backend lowering
is allowed only for trusted in-process objects constructed by the caller, and
those backends must validate `capability.supports(operation)` before emitting
artifacts.

## Consequences

- External authors have a clear starting point.
- The backend story stays aligned with HAC-IR and HS-IR contracts.
- TUC avoids opening a plugin attack surface before a dedicated sandbox and
  threat model exist.
- Future backend certification can build on a documented v0.1 baseline.

## Follow-Up

1. Add a backend author certification checklist.
2. Add a negative-test template for malformed capabilities and unsupported ops.
3. Define a plugin lifecycle only through a separate security RFC.
4. Add artifact sandboxing before any generated backend output can execute.
