# Executable Backend Security Review Report

Executable Backend Security Review Report is a diagnostic artifact for reviewing
future proposals that want to introduce executable backend surfaces, device
access, generated-artifact execution, dynamic-library loading, subprocesses,
network access, plugin discovery, native code, or cache access.

It does not execute backend artifacts, access devices, discover plugins, load
dynamic libraries, run subprocesses, read host paths, inspect environment
variables, or approve native performance claims.

## Contract

- Report schema:
  `schemas/executable_backend_security_review_report.v0.schema.json`
- Report schema version:
  `tuc.executable_backend_security_review_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API:
  `build_executable_backend_security_review_report(proposal_name, reviews=())`
- Dump API: `dump_executable_backend_security_review_report(report)`
- Example: `examples/executable_backend_security_review_report.py`
- Tests: `tests/test_executable_backend_security_review_report.py`
- Schema tests: `tests/test_executable_backend_security_review_schema.py`

The report is not an execution approval. It records bounded review metadata that
future native performance proposals can reference.

## Review Fields

Each review entry is data-only and bounded:

- `review_id`: stable review identifier
- `reviewed_surface`: one of `backend_artifact_execution`, `cache_access`,
  `device_access`, `dynamic_library_loading`, `generated_code_execution`,
  `native_code_execution`, `network_access`, `plugin_discovery`, or
  `subprocess_execution`
- `threat_model_id`: threat model identifier
- `sandbox_model_id`: sandbox model identifier
- `resource_budget_id`: resource budget identifier
- `provenance_id`: review provenance identifier
- `review_status`: `not_reviewed`, `reviewed_not_approved`, or
  `approved_by_maintainers`
- `fuzzing_evidence_id`: fuzzing, property-test, sanitizer, or negative-test
  evidence identifier
- `review_digest`: `not_supplied` or a `sha256:` digest

The report intentionally accepts identifiers and digests, not host paths,
command lines, environment variables, backend artifact contents, generated code,
native source contents, dynamic-library paths, device identifiers, secrets, or
raw benchmark output.

## Security Boundary

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not load, inspect, or execute the reviewed surface. It is a
bounded review surface for already produced security evidence.

`executable_backend_security_review_ready` means only that at least one bounded
review entry is present, every entry is `approved_by_maintainers`, every entry
names threat-model, sandbox, resource-budget, provenance, and fuzzing evidence,
and every entry supplies a digest.

It does not mean TUC may execute backend artifacts or make native performance
claims. Execution remains blocked until a dedicated implementation RFC,
sandboxing model, tests, and maintainer approval are accepted.

## Still Blocked

These remain blocked after this report exists:

- executable backend artifact execution
- device access
- dynamic-library loading
- subprocess execution
- network access
- plugin auto-discovery
- native code execution
- generated-code execution
- treating a security review as benchmark proof
- native performance parity claims
