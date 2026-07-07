# Plugin Discovery Allowlist Gate

Plugin Discovery Allowlist Gate v0 is the dedicated Real Triton Integration
surface gate for `plugin_discovery`.

It defines allowlist requirements for future frontend plugin discovery without
admitting discovery. The current report is data-only and does not discover
plugins, discover entrypoints, scan registries, scan filesystems, import
frontend packages, import Python modules, execute plugin code, derive
capability claims from code, access the network, run subprocesses, load dynamic
libraries, or access devices.

## Contract

- Report schema:
  `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`
- Report schema version:
  `tuc.plugin_discovery_allowlist_gate_report.v0`
- Gate contract:
  `plugin_discovery_allowlist_gate.data_only.v0`
- Example: `examples/plugin_discovery_allowlist_gate.py`
- Golden:
  `tests/golden/frontend/plugin_discovery_allowlist_gate_report.json`
- Tests: `tests/test_plugin_discovery_allowlist_gate.py`
- RFC: `rfcs/0247-plugin-discovery-allowlist-gate.md`

## Meaning

The gate binds digest-only evidence for:

- External Frontend Package Conformance;
- Package Import Sandbox Gate;
- Plugin Discovery Allowlist Model;
- Real Triton Integration Admission Gate.

The current status is:

- `gate_status = allowlist_requirements_only`;
- `allowlist_boundary_established = true`;
- `admission_effect = does_not_admit_plugin_discovery`;
- `plugin_discovery = false`;
- `entrypoint_discovery = false`;
- `registry_scan = false`.

This means TUC has reviewable allowlist requirements for plugin discovery, not
a plugin discovery implementation.

## Required Controls

The gate requires:

- allowlist entries are manifest IDs, not executable entrypoints;
- capability claims are data-only;
- digest-only public evidence;
- plugin input treated as untrusted;
- no plugin discovery;
- no entrypoint discovery;
- no registry scan;
- no filesystem scan;
- no frontend package import;
- no Python import;
- no plugin code execution;
- no network access;
- no subprocess execution;
- no dynamic library loading;
- no device access;
- sanitized diagnostics only;
- fail-closed violations.

## Security Boundary

The report must not contain discovered plugins, plugin code, imported modules,
raw source, host paths, command lines, environment variables, device
identifiers, runtime handles, plugin entrypoints, generated code, backend
artifacts, raw benchmark output, raw timing samples, or executable
permissions.

Future plugin discovery may only move beyond this gate after a separate
implementation RFC defines a manifest-only allowlist, import isolation,
entrypoint mediation, resource limits, provenance, negative tests, and
maintainer approval.

## Next Surface Gate

[Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md) is the
next dedicated Real Triton Integration surface gate. Its canonical doc path is
`docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`, its entry point is
`examples/triton_jit_execution_sandbox_gate.py`, and its schema is
`schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`.

That gate keeps Triton JIT execution, kernel launch, generated artifact
execution, device access, kernel-cache access, backend binary emission,
frontend package import, Python import, plugin discovery, network access,
subprocess execution, and dynamic library loading blocked while defining the
sandbox requirements for future review.
