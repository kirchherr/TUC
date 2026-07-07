# External Frontend Package Conformance

External Frontend Package Conformance v0 is the data-only contract for frontend
authors who want to emit `source_intent.v0` plain data for TUC.

It is not a plugin system. It does not import candidate packages, discover
entrypoints, execute source, call `@triton.jit`, inspect Python function
objects, access devices, or create generated artifacts.

## Contract

- Report schema:
  `schemas/external_frontend_package_conformance_report.v0.schema.json`
- Report schema version:
  `tuc.external_frontend_package_conformance_report.v0`
- Conformance contract:
  `external_frontend_package_conformance.data_only.v0`
- Package interface contract:
  `external_frontend.source_intent_plain_data.v0`
- Example: `examples/external_frontend_package_conformance.py`
- Golden:
  `tests/golden/frontend/external_frontend_package_conformance_report.json`
- Tests: `tests/test_external_frontend_package_conformance.py`
- RFC: `rfcs/0243-external-frontend-package-conformance.md`

## Meaning

An external frontend package can be considered conformance-ready only when it
provides:

- a bounded package manifest;
- declared capabilities matching the Source Intent plain-data interface;
- digest-only accepted and rejected fixtures;
- passing Source Intent Frontend Conformance;
- explicit public-return coverage;
- fail-closed invalid payload coverage;
- no package import requirement.

The report serializes fixture digests and conformance digests, not raw fixture
payloads. Rejected fixtures may contain hostile keys in memory during tests, but
the public report remains source-free and artifact-free.

## Security Boundary

The report fixes these fields to `false`:

- `package_imported`;
- `plugin_discovery`;
- `direct_source_ingestion`;
- `triton_jit_execution`.

The report must not contain source text, Python source, function objects, host
paths, command lines, environment variables, device identifiers, runtime
handles, backend artifacts, generated code, plugin entrypoints, raw benchmark
output, raw timing samples, or executable permissions.

This conformance evidence satisfies the external frontend package prerequisite
for [Triton Integration Readiness](TRITON_INTEGRATION_READINESS.md), but it
does not grant permission to execute external packages or native backend code.
