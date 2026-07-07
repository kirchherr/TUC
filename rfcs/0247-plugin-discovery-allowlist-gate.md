# RFC 0247: Plugin Discovery Allowlist Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies
`plugin_discovery_allowlist_gate` as the required gate for the
`plugin_discovery` surface.

Package Import Sandbox Gate already proves that package-shaped data can be
reviewed without importing packages. That is not enough to discover plugins.
Plugin discovery can execute entrypoint loaders, inspect registries, scan
filesystems, import modules, run plugin code, load dynamic libraries, access
devices, or derive capability claims from behavior rather than data.

## Decision

Add Plugin Discovery Allowlist Gate v0.

The gate binds digest-only evidence for:

- External Frontend Package Conformance;
- Package Import Sandbox Gate;
- Plugin Discovery Allowlist Model;
- Real Triton Integration Admission Gate.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required allowlist controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for plugin discovery, entrypoint discovery, registry
  scan, filesystem scan, frontend package import, Python import, plugin code
  execution, plugin loading, capability claims from code, network access,
  subprocess execution, dynamic library loading, and device access.

## Security Constraints

The gate must not:

- discover plugins;
- discover or load entrypoints;
- scan plugin registries;
- scan filesystems or host paths;
- import frontend packages;
- import Python modules on behalf of candidate plugins;
- execute plugin code;
- derive capability claims from plugin code;
- access the network;
- run subprocesses;
- load dynamic libraries;
- access devices;
- serialize discovered plugins, entrypoint records, imported modules, plugin
  code, host paths, command lines, environment values, device identifiers,
  runtime handles, generated code, backend artifacts, raw timing samples, or
  executable permissions.

Every future plugin discovery proposal must preserve this gate or replace it
with a stricter successor RFC and sandbox proof.

## Evidence

- Implementation:
  `src/tuc/frontend/plugin_discovery_allowlist_gate.py`
- Example: `examples/plugin_discovery_allowlist_gate.py`
- Report schema:
  `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/plugin_discovery_allowlist_gate_report.json`
- Tests: `tests/test_plugin_discovery_allowlist_gate.py`
- Documentation:
  `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`

## Consequences

TUC now has a third dedicated Real Triton Integration surface gate. It makes
plugin discovery requirements reviewable while keeping real plugin discovery
closed, data-only, and import-free.
