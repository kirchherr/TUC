# RFC 0222: Backend Plugin Maintainer Approval

- Status: Accepted
- Area: Backend plugins, lifecycle policy, security
- Created: 2026-06-24
- Supersedes: None
- Related: RFC 0217, RFC 0218, RFC 0219, RFC 0220, RFC 0221

## Context

Backend Plugin Lifecycle Policy had one remaining unsatisfied requirement:
maintainer approval. Sandbox model evidence, artifact provenance, resource
budget evidence, and fuzz/negative-test evidence are now accepted as data-only
contracts, but the lifecycle must still record an explicit maintainer decision
before future executable plugin enablement proposals can be considered.

## Decision

Add Backend Plugin Maintainer Approval v0 with:

- report model `src/tuc/backends/maintainer_approval.py`;
- schema
  `schemas/backend_plugin_maintainer_approval_report.v0.schema.json`;
- example `examples/backend_plugin_maintainer_approval.py`;
- golden
  `tests/golden/backend_plugin_maintainer_approval/current_report.json`;
- tests `tests/test_backend_plugin_maintainer_approval.py`;
- approval contract `backend_plugin_maintainer_approval.data_only.v0`.

The current approval record accepts the lifecycle evidence gate only. It binds
the accepted sandbox model, artifact provenance, resource budget, and
fuzz/negative-test contracts, keeps all executable surfaces blocked, and
requires a separate implementation RFC before any actual plugin execution,
dynamic-library loading, device access, or native ABI work can start.

Backend Plugin Lifecycle Policy now treats `maintainer_approval` as satisfied by
this accepted data-only evidence contract.

## Security Boundary

The maintainer approval report is data-only. It does not query GitHub, resolve
identities, read local approval files, import modules, load artifacts, execute
plugins, access devices, inspect environment variables, spawn subprocesses, or
touch the network.

The report intentionally omits names, email addresses, tokens, URLs, source
text, paths, commands, module names, dynamic-library paths, generated artifact
contents, raw benchmark output, raw fuzz corpus inputs, and artifact bytes.

## Consequences

TUC now has a complete data-only backend plugin lifecycle evidence chain.

This does not enable executable plugins. Future implementation proposals still
need explicit RFCs, concrete sandbox enforcement, runtime gate changes, CI
coverage, and security review before plugin discovery, artifact execution, or a
native plugin ABI can be enabled.
