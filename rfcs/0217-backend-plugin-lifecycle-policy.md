# RFC 0217: Backend Plugin Lifecycle Policy

Status: Accepted

## Context

TUC already supports backend capability manifests, manifest claim review,
backend author readiness, trusted in-process prototype executors, and
diagnostic executable backend security review metadata.

That is enough for research-grade capability onboarding. It is not enough to
discover, import, load, or execute external backend plugins.

The next secure-by-design boundary is a small, explicit policy artifact that
records the current lifecycle state before anyone can mistake capability data
for executable plugin permission.

## Decision

Add Backend Plugin Lifecycle Policy v0 with:

- report model `src/tuc/backends/plugin_lifecycle.py`;
- schema `schemas/backend_plugin_lifecycle_policy_report.v0.schema.json`;
- example `examples/backend_plugin_lifecycle_policy.py`;
- golden `tests/golden/backend_plugin_lifecycle_policy/current_report.json`;
- tests `tests/test_backend_plugin_lifecycle_policy.py`;
- policy contract `backend_plugin_lifecycle_policy.blocking.v0`.

The current policy is an accepted blocking policy. It keeps:

- backend plugin discovery disabled;
- generated artifact execution disabled;
- native plugin ABI loading disabled;
- external plugin execution blocked;
- sandbox model status `accepted_data_only_model` after RFC 0218.

The policy records nine requirements before executable backend plugins can be
proposed for enablement:

- capability manifest claim review;
- backend author evidence gate;
- trusted executor contract;
- plugin lifecycle RFC;
- sandbox model;
- artifact provenance;
- resource budget;
- fuzzing and negative-test evidence;
- maintainer approval.

All nine are currently satisfied by existing review surfaces after RFC
0222. Executable plugin surfaces remain disabled by policy.

## Security Boundary

The policy is data-only. It does not scan directories, discover plugins, import
modules, load dynamic libraries, execute generated artifacts, access devices,
spawn subprocesses, touch the network, inspect environment variables, read host
paths, or load benchmark artifacts.

It records stable identifiers only. It does not record Python module names,
entry points, commands, device identifiers, source code, generated artifacts,
native library paths, secrets, or raw benchmark output.

## Consequences

Future executable backend proposals now have a concrete entry condition:
change the lifecycle policy only after sandbox, provenance, resource-budget,
negative-test or fuzzing, and maintainer-approval evidence exist. After RFC
0222, the data-only lifecycle evidence chain is complete, while executable
behavior remains behind a separate implementation gate.

This protects the Universal Compute research claim. Backends can still enter
TUC as declarative capability data, while executable behavior remains behind an
explicit lifecycle gate.
