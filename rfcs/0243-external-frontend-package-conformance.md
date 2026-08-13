# RFC 0243: External Frontend Package Conformance

## Status

Accepted as data-only frontend integration evidence.

## Context

Triton Integration Readiness had one remaining required prerequisite:
external frontend package conformance. TUC needs a credible way for external
frontend authors to prove that they can emit `source_intent.v0` plain data
without turning frontend integration into a plugin, import, source execution, or
JIT surface.

## Decision

Add External Frontend Package Conformance v0.

The conformance path accepts:

- a bounded package manifest;
- Source Intent plain-data fixtures supplied as in-memory test data;
- the existing Source Intent Frontend Conformance report.

The conformance report emits only:

- package manifest metadata;
- manifest digest;
- fixture payload digests;
- checked case names and counts;
- Source Intent Frontend Conformance report digest;
- blocked execution surfaces;
- fixed `false` flags for package import, plugin discovery, direct source
  ingestion, and Triton JIT execution.

## Security Constraints

The conformance path must not:

- import candidate frontend packages;
- discover plugins or entrypoints;
- evaluate decorators;
- execute `@triton.jit`;
- compile bytecode;
- inspect Python function objects;
- read source files by path;
- access devices;
- access the network;
- run subprocesses;
- load dynamic libraries;
- emit metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend
  decisions, backend artifacts, generated artifacts, raw timing data, runtime
  handles, device identifiers, host paths, or command lines.

Every accepted fixture must pass Source Intent Intake and Source Intent
Frontend Conformance. Rejected fixtures must fail closed. The public report
must not serialize raw fixture payloads or raw source text.

## Evidence

- Implementation:
  `src/tuc/frontend/external_frontend_package_conformance.py`
- Example: `examples/external_frontend_package_conformance.py`
- Report schema:
  `schemas/external_frontend_package_conformance_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/external_frontend_package_conformance_report.json`
- Tests: `tests/test_external_frontend_package_conformance.py`
- Documentation: `docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md`

## Consequences

Triton Integration Readiness can mark `external_frontend_package_conformance`
as satisfied. The readiness report may become `ready` as a data-only review
condition while direct source ingestion and Triton JIT execution remain blocked
by policy.
