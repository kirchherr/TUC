# RFC 0343: Acceptance-led delivery roadmap

- Status: Proposed for review; documentation and retained observed data only
- Date: 2026-11-12
- Engineering baseline: `3324f72390c3e5711f1be519fa400dfe906df621`
- Builds on: RFCs 0291-0294 and 0333-0342; existing governance and claim gates

## Problem

The roadmap accumulates implemented increments while its current status and
priority list still mix candidates, completed work and long-term research.
The bounded CPU model path now has installed APIs, sessions and a CLI, but
independent acceptance and a reviewed next-release boundary remain open.
Its new lifecycle observations also rely on expiring CI artifacts.

The configuration review found two additional delivery dependencies: effective
main rules lack the status-check/history controls described by branch policy,
and the only current codeowner is also author of the recent PRs. Their
separately authorized review exceptions do not establish a normal review path.

## Decision

Adopt [the completion plan](../docs/PROJECT_COMPLETION_PLAN.md) as the ordered
near-term roadmap while preserving the master plan's universal-compute mission:

1. M0: resolve findings, verify governance/supply-chain readiness and freeze an
   exact research release candidate.
2. M1: obtain and review independently controlled reproduction of that candidate.
3. M2: publish the accepted bounded research release through existing controls.
4. M3: validate independent backend authorship through the installed data-only
   contract without TUC core modification.
5. M4: test a distinct physical vendor/ISA through a dedicated bounded proof.
6. M5: assess performance through the existing separate evidence requirements.
7. M6: obtain attributable acceptance of a scoped real organizational pilot,
   including compatibility, operation, admission and integration-effort criteria.

The bounded CPU deliverable is complete at M0-M2. The wider TUC mission remains
active through M3-M6 and actual organizational use. Existing Gamma/Delta
integration proof and same-project physical observations retain their exact
scope; they do not fill in missing independent authors or organizations.

Each milestone names an owner role, a dependency and an exit artifact. During
closure, implementation work resolves findings, reproduction obstacles or
release requirements. Future features must supply their own distinct proof
value through the relevant milestone and RFC.

## Evidence retention and review

Retain the actual merged-source CLI and session JSON members byte-for-byte
from their GitHub artifacts after checking ZIP digests, source/wheel bindings,
consumer/auditor Git blobs and the existing numerical audit. Add an evidence
index with the original run, artifact identities and file checksums. Preserve
all earlier observations, archived auditor, goldens and legacy CI unchanged.

## Authority and security

This RFC changes planning and evidence availability. It introduces no parser,
compiler pass, runtime admission, dependency, workflow, plugin, device access
or new executable artifact. It does not modify GitHub rules or CODEOWNERS,
invite reviewers, authorize outreach/remote runs, trigger a release, or grant
review/publishing bypasses. Actual configuration and publishing work remains
with the repository/release owner under the existing approval policy.

An arithmetic audit does not authenticate execution origin. Independent
acceptance requires separately attributable environment/operator control.
Production source ingestion, executable plugins, general backends and native
performance remain subject to their existing gates.

## Validation

Use the existing standard-library auditor on both newly retained CI packets;
check the original numerical digest and artifact-member byte identity. Check
documentation links, existing documentation contracts and the research scope
claim gate. Source/runtime and CI are unchanged; ordinary PR checks still apply.
