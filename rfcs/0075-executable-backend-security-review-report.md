# RFC 0075: Executable Backend Security Review Report

Status: Accepted

## Summary

TUC adds a diagnostic Executable Backend Security Review Report for reviewing
future proposals that introduce executable backend surfaces.

## Motivation

TUC's current architecture deliberately avoids plugin discovery, dynamic
libraries, subprocesses, device access, generated-artifact execution, and native
code execution. That is the correct baseline for a secure compiler project.

Future native performance proposals may eventually require real executable
backends or device access. Those surfaces must not appear as incidental fields
inside benchmark reports, backend manifests, HAC-IR, runtime plans, or compiler
decision reports. They need a dedicated bounded review contract.

## Decision

Add
[Executable Backend Security Review Report](../docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)
with:

- `schemas/executable_backend_security_review_report.v0.schema.json`
- `build_executable_backend_security_review_report(proposal_name, reviews=())`
- `dump_executable_backend_security_review_report(report)`
- report schema version `tuc.executable_backend_security_review_report.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report contains only bounded identifiers, review status, evidence IDs, and
digest status. It does not contain executable artifacts, host paths, command
lines, environment variables, device identifiers, native source contents, or
generated code.

## Security Boundary

The report must not:

- execute backend artifacts
- access devices
- discover plugins
- import backend modules
- run subprocesses
- load dynamic libraries
- touch the network
- read host paths
- read environment variables
- inspect generated code or native source contents
- approve native performance claims

Unknown keys fail closed through JSON Schema and runtime validation.

## Readiness Semantics

`executable_backend_security_review_ready` means only:

- at least one bounded review entry is present
- every entry is `approved_by_maintainers`
- every entry names threat-model, sandbox, resource-budget, provenance, and
  fuzzing or negative-test evidence
- every entry supplies a `sha256:` digest

It does not grant execution permission by itself. Executable backend
implementation remains blocked until a separate implementation RFC, sandboxing
model, tests, and maintainer approval are accepted.

## Consequences

Future native performance proposals gain a reviewable security-evidence
contract before executable backend or device surfaces can be considered.

The current project remains blocked from native performance claims until the
full Performance Proof Boundary and Performance Proof Readiness report pass.

## Artifacts

- `schemas/executable_backend_security_review_report.v0.schema.json`
- `examples/executable_backend_security_review_report.py`
- `docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md`
- `tests/test_executable_backend_security_review_report.py`
- `tests/test_executable_backend_security_review_schema.py`
