# Backend Plugin Fuzz Negative Tests

Backend Plugin Fuzz Negative Tests v0 is the data-only evidence contract for
future executable backend plugin negative-test and fuzz-seed coverage.

It records which rejection classes are covered by deterministic repository
tests and seed identifiers. It does not run fuzzers, execute artifacts, import
plugins, load dynamic libraries, or grant execution permission.

## Contract

- Report schema:
  `schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_fuzz_negative_tests_report.v0`
- Negative-test contract:
  `backend_plugin_fuzz_negative_tests.data_only.v0`
- Negative-test policy:
  `fuzz_negative_tests.required_cases.no_execution.v0`
- Example:
  `examples/backend_plugin_fuzz_negative_tests.py`
- Golden:
  `tests/golden/backend_plugin_fuzz_negative_tests/current_report.json`
- Tests:
  `tests/test_backend_plugin_fuzz_negative_tests.py`
- RFC:
  [RFC 0221](../rfcs/0221-backend-plugin-fuzz-negative-tests.md)

## Current Decision

The fuzz and negative-test model is accepted as data-only evidence:

- `negative_tests_status: accepted_data_only_test_evidence`
- `seed_policy: deterministic_seed_ids_only`
- `execution_permission: not_granted`
- `execution_allowed: false`
- `evidence_ready: true`

This satisfies the `fuzz_negative_tests` requirement in
[Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md), but it
does not make plugins executable. Maintainer approval now exists as data-only
lifecycle evidence; any executable plugin behavior still requires a separate
implementation RFC and explicit policy change.

## Required Case Kinds

The current evidence requires deterministic coverage for:

- forbidden execution-surface identifiers
- invalid artifact digests
- oversized resource budgets
- duplicate evidence records
- fail-closed schemas for forbidden surface keys

Each case records a stable `case_id`, `case_kind`, `evidence_id`, `seed_id`,
blocked execution surface, expected rejection result, and review status. These
are identifiers only, not raw fuzz inputs or artifact contents.

## Security Boundary

The report is data-only. It does not scan directories, resolve entry points,
import modules, load dynamic libraries, execute generated artifacts, access
devices, spawn subprocesses, read host paths, inspect environment variables,
touch the network, load benchmark artifacts, read artifact bytes, run fuzzers,
or collect raw timing samples.

The schema is fail-closed with `additionalProperties: false` on every object.
It records only bounded identifiers and omits source text, module names, host
paths, command lines, device identifiers, dynamic-library paths, generated
artifact contents, secrets, raw benchmark output, raw fuzz corpus inputs, URLs,
and artifact bytes.

## Review Meaning

A passing fuzz/negative-test report means TUC has accepted a deterministic
inventory of rejection classes that must stay covered before future plugin
enablement can be proposed.

It does not mean TUC has a sandbox implementation, an executable plugin ABI,
maintainer approval, native fuzz infrastructure, sanitizer coverage, runtime
enforcement, native performance claims, or permission to execute backend
artifacts. Those require separate implementation evidence and changes to the lifecycle policy.
