# RFC 0072: Toolchain Environment Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Epsilon

## Summary

TUC adds a diagnostic Toolchain Environment Report for reviewing the versioned
software environment associated with future benchmark evidence.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, raw timing sample storage, host package discovery, environment
variable ingestion, plugin discovery, dynamic libraries, subprocess execution,
native code storage, or hardware-specific HAC-IR semantics.

## Motivation

RFC 0063 and RFC 0064 require versioned toolchain environment evidence before
future native performance proposals can pass readiness. Benchmark numbers are
not reproducible unless the relevant toolchain components are explicitly
versioned and reviewable.

TUC needs a data-only way to state which runtime, package, compiler, driver,
device runtime, container, and OS identities belong to a benchmark proposal
without letting host paths, environment variables, package-manager output, or
hardware details enter the compiler boundary.

## Decision

Add [Toolchain Environment Report](../docs/TOOLCHAIN_ENVIRONMENT_REPORT.md)
with:

- `schemas/toolchain_environment_report.v0.schema.json`
- `build_toolchain_environment_report(proposal_name, components=())`
- `dump_toolchain_environment_report(report)`
- report schema version `tuc.toolchain_environment_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report records bounded component identifiers, component kind, version
identifier, provenance identifier, and optional SHA-256 digest status.

## Component Kinds

The v0 report tracks:

- `python_runtime`
- `python_package`
- `native_compiler`
- `device_runtime`
- `device_driver`
- `container_image`
- `operating_system`

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, secrets, hardware serials, device identifiers,
generated artifacts, plugin entrypoints, backend binaries, dynamic-library
paths, cache paths, native code, shell commands, package-manager output, or
backend artifact contents.

The report must not execute backend artifacts.
The report must not run host discovery commands.
The report must not load benchmark artifacts.
The report must not access devices.
The report must not add hardware-specific performance knobs to HAC-IR.

The schema is fail-closed with `additionalProperties: false` on every object.

## Evidence

The implementation adds:

- `schemas/toolchain_environment_report.v0.schema.json`
- `examples/toolchain_environment_report.py`
- `docs/TOOLCHAIN_ENVIRONMENT_REPORT.md`
- `tests/test_toolchain_environment_report.py`
- `tests/test_toolchain_environment_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Future benchmark evidence has an explicit toolchain inventory surface.
- Toolchain review remains separate from host discovery and benchmark execution.
- Host paths, environment variables, package-manager output, and hardware
  identifiers remain outside the compiler boundary.
- Native performance claims remain blocked until the rest of the performance
  proof evidence exists.

## Rejected Alternatives

1. Collect toolchain data automatically from the host.

   Rejected because host discovery creates command execution, path leakage, and
   environment-variable exposure risks.

2. Store raw package-manager output.

   Rejected because v0 needs bounded review data, not unbounded host output.

3. Treat a valid toolchain inventory as a performance proof.

   Rejected because toolchain evidence does not supply workload scope,
   methodology, native baseline provenance, benchmark artifacts,
   planner-overhead analysis, leaky-abstraction review, correctness goldens, or
   executable-backend security review.
