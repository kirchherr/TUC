# Runtime Manual Override Policy

TUC does not implement runtime manual placement overrides yet.

This policy defines the rules that must exist before TUC adds any override
object, config file, command-line flag, frontend hint, or optimizer control that
can influence backend placement.

## Purpose

Manual overrides are future declarative planning constraints. They may help a
maintainer, backend author, or proof fixture force a known placement scenario so
that runtime planning, transfer costs, and decision reporting can be reviewed.

They must not become a way to smuggle hardware-specific semantics into HAC-IR or
to bypass backend capability validation.

## Allowed Shape

A future override object may only be accepted if it is:

- Schema-versioned with an explicit `schema_version`.
- Bounded in total size, rule count, string length, and nesting depth.
- Operation-scoped by default, using operation names that already exist in a
  validated graph.
- Written as declarative data, not executable code.
- Limited to backend names that already exist in an explicit
  `BackendRegistry`.
- Expressed as one of a small set of typed actions such as `require_backend`,
  `prefer_backend`, or `deny_backend`.
- Recorded in compiler decision reports and runtime-plan dumps when it affects
  candidate selection or final placement.

Graph-wide overrides are not part of the initial policy. They require a
dedicated RFC because they can hide broad placement changes.

## Hard Limits

Manual overrides cannot:

- Change mathematical semantics.
- Change operation kind, tensor shape, dtype, graph topology, layout semantics,
  or error-budget meaning.
- Add backend capabilities or modify existing capability data.
- Bypass `BackendRegistry.diagnose_operation_support`.
- Force an operation onto a backend that did not already appear as an accepted
  backend candidate.
- Change HAC-IR attributes or introduce hardware-specific facts into HAC-IR.
- Hide fallback behavior or semantic degradation.
- Execute backend code.
- Discover plugins.
- Import modules.
- Spawn subprocesses.
- Load dynamic libraries.
- Access devices.
- Execute generated artifacts.
- Touch the network.
- Read host paths, environment variables, secrets, credentials, or runtime
  filesystem state.

## Planning Order

A future implementation must preserve this order:

1. Validate the graph and all IR boundary data.
2. Lower TLIR to HAC-IR and validate HAC-IR neutrality.
3. Load explicit backend capability data through existing safe paths.
4. Run backend support diagnostics.
5. Validate manual overrides as bounded declarative data.
6. Apply overrides only to already accepted backend candidates.
7. Fail closed if the override leaves no valid candidate.
8. Record accepted and rejected override effects in the compiler decision
   report.
9. Emit deterministic runtime-plan dumps for the final assignment.

Overrides are never evaluated before validation, and they never create new
capability facts.

## Fail-Closed Rejection Cases

An override must be rejected before planning continues when it contains:

- Unknown or unsupported `schema_version`.
- Unknown fields.
- Unknown operation names.
- Unknown backend names.
- Duplicate rules for the same operation and action.
- Contradictory `require_backend` and `deny_backend` actions.
- Unbounded wildcard, regex, glob, or selector behavior.
- Backend requirements not present in accepted support diagnostics.
- Deny rules that remove every valid candidate.
- Attempts to change graph semantics, HAC-IR facts, layouts, error budgets, or
  capability data.
- Any reference to plugins, imports, subprocesses, dynamic libraries, devices,
  generated artifacts, network access, host paths, or environment variables.

Diagnostics must be structured, bounded, and free of host-specific paths or
secret material.

## Review And Test Gate

Before executable override support can be added, the implementation PR must
include:

- A dedicated RFC that names the schema and trust boundary.
- Positive tests for accepted operation-scoped overrides.
- Negative tests for every fail-closed case in this policy.
- Golden compiler decision-report fixtures showing accepted and rejected
  override effects.
- Golden runtime-plan fixtures showing final placement after overrides.
- Proof examples that still end with `PASS` when override-backed fixtures are
  introduced.
- Security review confirming no plugin discovery, imports, subprocesses,
  dynamic libraries, device access, generated-artifact execution, network
  access, host-path reads, or environment-dependent behavior were added.

Automatic candidate scoring or global optimization must not use manual
overrides as hidden training data, performance claims, or backend certification.

## Current Status

This policy is the current contract. TUC has no accepted manual override input
surface yet.

