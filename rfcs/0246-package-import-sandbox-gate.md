# RFC 0246: Package Import Sandbox Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies `package_import_sandbox_gate` as
the required gate for the `frontend_package_import`, `python_import`, and
`network_access` import-adjacent surfaces.

External Frontend Package Conformance already proves that package-shaped
metadata and Source Intent fixtures can be reviewed without package import.
That is not enough to import real Python packages. Imports can execute module
top-level code, discover entrypoints, access files, read environment variables,
trigger dynamic libraries, access networks, or start subprocesses.

## Decision

Add Package Import Sandbox Gate v0.

The gate binds digest-only evidence for:

- External Frontend Package Conformance;
- Package Import Sandbox Model;
- Real Triton Integration Admission Gate;
- Source Ingestion Quarantine Gate.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required sandbox controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for package import, Python import, package code
  execution, external package loading, entrypoint discovery, plugin discovery,
  network access, filesystem access, environment access, subprocess execution,
  dynamic library loading, and Source Intent from import.

## Security Constraints

The gate must not:

- import external frontend packages;
- import Python modules on behalf of candidate packages;
- execute package code;
- discover package or plugin entrypoints;
- inspect Python function objects;
- access the network;
- access filesystems or host paths;
- read environment variables;
- run subprocesses;
- load dynamic libraries;
- access devices;
- emit Source Intent from imported code;
- serialize imported modules, function objects, package code, host paths,
  command lines, environment values, device identifiers, runtime handles,
  generated code, backend artifacts, raw timing samples, or executable
  permissions.

Every future package import proposal must preserve this gate or replace it with
a stricter successor RFC and sandbox proof.

## Evidence

- Implementation:
  `src/tuc/frontend/package_import_sandbox_gate.py`
- Example: `examples/package_import_sandbox_gate.py`
- Report schema:
  `schemas/package_import_sandbox_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/package_import_sandbox_gate_report.json`
- Tests: `tests/test_package_import_sandbox_gate.py`
- Documentation:
  `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`

## Consequences

TUC now has a second dedicated Real Triton Integration surface gate. It makes
package import requirements reviewable while keeping external frontend package
integration data-only and import-free.
