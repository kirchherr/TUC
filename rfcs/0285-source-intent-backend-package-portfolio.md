# RFC 0285: Source Intent Backend Package Portfolio v0

Status: Accepted

## Summary

Join the canonical Source Intent plain-data boundary to the accepted
Multi-Package Execution Portfolio. Require no-fallback external package
planning, trusted simulator projection, explicit layout conversion, public
output closure, independent reference correctness, and backend equivalence in
one digest-only proof.

## Motivation

RFC 0284 proved that two external capability packages can jointly own a graph
and execute through trusted projections. The existing Source Intent
mixed-runtime proof showed that neutral frontend data can reach built-in
simulators. These were still separate proof entrances.

The Universal Compute thesis needs the joined statement: neutral frontend
intent can reach independently described capability domains without granting
source text or external package code execution authority.

## Decision

Add:

- `docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md`
- `examples/source_intent_backend_package_portfolio.py`
- `schemas/source_intent_backend_package_portfolio_report.v0.schema.json`
- `tests/golden/frontend/source_intent_backend_package_portfolio_report.json`
- `rfcs/0285-source-intent-backend-package-portfolio.md`

The accepted proof path is:

```text
source_intent.v0 plain data
  -> Source Intent metadata
  -> ComputeGraph and HAC-IR
  -> external-systolic -> external-vector
  -> systolic-sim -> vector-sim
  -> public output api_activated
  -> reference correctness and backend equivalence
  -> PASS
```

The source plan must contain exactly the two external package backends and no
fallback. The projected plan must contain exactly the two trusted simulators.
The `projection` boundary must retain one `blocked -> row_major` conversion.

## Input Boundary

Input is already decoded JSON-like data accepted by Source Intent Intake.
Source text, AST objects, bytecode, Python modules, decorators, callables,
backend selectors, device selectors, paths, commands, and plugin entry points
remain outside this contract.

The accepted module contains only `matmul` followed by identity `elementwise`
with explicit tensor declarations and one public return alias. Extending the
syntax or operation semantics requires a separate reviewed change.

## Trust Decisions

- External packages remain attacker-controlled data.
- Each package must pass Integration Package conformance.
- Exact maintainer-owned package, capability, binding, and executor-contract
  digests authorize projection.
- Packages cannot select or provide their executors.
- Portfolio composition requires the exact disjoint two-package set.
- The source plan must match canonical recompilation from admitted capability
  data before it can be projected.
- Only fixed in-repository trusted simulators execute.

## Evidence Invariants

- Ten evidence artifacts have stable IDs, contracts, order, and SHA-256
  metadata digests.
- Source and trusted backend sequences remain visible.
- Fallback assignment count is zero.
- Layout conversion count is one.
- Public and terminal output names remain explicit.
- Independent reference correctness and backend equivalence both pass.
- Package identities and exact package digests remain visible.
- Source payloads and raw tensor values are omitted.
- Source, package, plugin, native, and physical-device execution flags remain
  false.
- The schema rejects additional properties at every object boundary.

## Security Consequences

The proof does not expand any executable trust boundary. Source Intent remains
execution-free. Package loading remains bounded data parsing. Projection uses a
fixed allowlist and exact digests. Runtime execution remains limited to trusted
reference implementations. Public serialization excludes source and values.

Negative tests cover backend authority in Source Intent, direct source-text
input, package identity drift, unknown report properties, fallback drift, and
package-digest drift.

## Alternatives Rejected

### Add the existing proofs to another evidence catalog

Rejected as the primary step because catalog composition would prove only that
two reports coexist. This RFC requires one live end-to-end execution path.

### Allow Source Intent to name package backends

Rejected because placement authority belongs to capability planning, not
hardware-neutral intent.

### Execute external package implementations

Rejected because capability portability can be researched without opening
dynamic import, native library, plugin, JIT, subprocess, or device surfaces.

### Claim native heterogeneous performance

Rejected because trusted simulator execution establishes semantic portability,
not physical residency, native code generation, or performance parity.

## Consequences

TUC now has one reviewable vertical proof from neutral frontend intent through
external capability ownership to heterogeneous trusted execution and semantic
closure. This advances the research thesis materially while keeping the next
unproven boundaries explicit: admitted source ingestion, executable sandboxed
backends, physical devices, and native performance evidence.
