# Package Import Sandbox Gate

Package Import Sandbox Gate v0 is the dedicated Real Triton Integration surface
gate for `frontend_package_import`.

It defines sandbox requirements for future external frontend packages without
admitting package import. The current report is data-only and does not import
Python packages, discover entrypoints, execute package code, access the
network, read the filesystem, inspect environment variables, run subprocesses,
load dynamic libraries, or emit Source Intent from imported code.

## Contract

- Report schema:
  `schemas/package_import_sandbox_gate_report.v0.schema.json`
- Report schema version:
  `tuc.package_import_sandbox_gate_report.v0`
- Gate contract:
  `package_import_sandbox_gate.data_only.v0`
- Example: `examples/package_import_sandbox_gate.py`
- Golden:
  `tests/golden/frontend/package_import_sandbox_gate_report.json`
- Tests: `tests/test_package_import_sandbox_gate.py`
- RFC: `rfcs/0246-package-import-sandbox-gate.md`

## Meaning

The gate binds digest-only evidence for:

- External Frontend Package Conformance;
- Package Import Sandbox Model;
- Real Triton Integration Admission Gate;
- Source Ingestion Quarantine Gate.

The current status is:

- `gate_status = sandbox_requirements_only`;
- `sandbox_boundary_established = true`;
- `admission_effect = does_not_admit_frontend_package_import`;
- `frontend_package_import = false`;
- `python_import = false`.

This means TUC has reviewable sandbox requirements for package import, not a
package import implementation.

## Required Controls

The gate requires:

- deterministic package manifests only;
- Source Intent fixtures only;
- digest-only public evidence;
- package input treated as untrusted;
- no frontend package import;
- no Python import;
- no entrypoint discovery;
- no plugin discovery;
- no network access;
- no filesystem access;
- no environment access;
- no subprocess execution;
- no dynamic library loading;
- import side effects blocked;
- sanitized diagnostics only;
- fail-closed violations.

## Security Boundary

The report must not contain imported modules, Python function objects, package
code, raw source, host paths, command lines, environment variables, device
identifiers, runtime handles, plugin entrypoints, generated code, backend
artifacts, raw benchmark output, raw timing samples, or executable
permissions.

Future frontend package integration may only move beyond this gate after a
separate implementation RFC defines an actual sandbox, import isolation,
resource limits, provenance, negative tests, and maintainer approval.

## Next Surface Gate

[Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md) is the
next dedicated Real Triton Integration surface gate. Its canonical doc path is
`docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`, its entry point is
`examples/plugin_discovery_allowlist_gate.py`, and its schema is
`schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`.

That gate keeps plugin discovery, entrypoint discovery, registry scans,
filesystem scans, plugin code execution, frontend package import, Python
import, network access, subprocess execution, dynamic library loading, device
access, and capability claims from plugin code blocked while defining the
manifest-ID allowlist requirements for future review.
