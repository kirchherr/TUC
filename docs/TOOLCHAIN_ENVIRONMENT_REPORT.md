# Toolchain Environment Report

Toolchain Environment Report is a diagnostic artifact for reviewing the
versioned software environment associated with future benchmark evidence.

It does not run benchmarks, inspect host hardware, read environment variables,
scan installed packages, execute backend artifacts, access devices, discover
plugins, load dynamic libraries, run subprocesses, store host paths, or claim
native performance parity.

## Contract

- Report schema: `schemas/toolchain_environment_report.v0.schema.json`
- Report schema version: `tuc.toolchain_environment_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_toolchain_environment_report(proposal_name, components=())`
- Dump API: `dump_toolchain_environment_report(report)`
- Example: `examples/toolchain_environment_report.py`
- Tests: `tests/test_toolchain_environment_report.py`
- Schema tests: `tests/test_toolchain_environment_schema.py`

The report is not a native performance proof. It records explicit versioned
toolchain component metadata that future benchmark artifacts can reference.

## Component Fields

Each toolchain component entry is data-only and bounded:

- `component_id`: stable component identifier
- `component_kind`: `python_runtime`, `python_package`, `native_compiler`,
  `device_runtime`, `device_driver`, `container_image`, or `operating_system`
- `version_id`: stable version identifier
- `provenance_id`: stable provenance identifier
- `component_digest`: `not_supplied` or a `sha256:` digest

The report intentionally accepts identifiers and digests, not host paths,
environment variables, command lines, package-manager output, hardware serials,
device IDs, backend binaries, generated code, or device details.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, secrets, hardware serials, device identifiers,
generated artifacts, plugin entrypoints, backend binaries, dynamic-library
paths, cache paths, native code, shell commands, package-manager output, or
backend artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code, run discovery commands, or load
benchmark artifacts. It is a toolchain inventory review surface only.

## Current Status

The current report can identify bounded toolchain components and whether their
digests are supplied.

`toolchain_environment_ready` means only that at least one bounded component is
present and no toolchain-specific issue remains. Native performance claims
remain blocked in v0.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- benchmark artifact acceptance as proof
- raw benchmark result ingestion
- host package or device discovery during proof review
- native benchmark execution
- executable backend benchmarking without a dedicated security RFC
- device access, generated-artifact execution, dynamic-library loading, or
  subprocess execution as part of proof review
