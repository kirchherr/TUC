# RFC 0039: Proof Artifact Review Checklist

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Alpha

## Summary

TUC adds a reviewer-facing checklist for changing proof artifacts.

The checklist lives in `docs/PROOF_ARTIFACT_REVIEW.md` and applies to proof
examples, proof metadata, full proof golden reports, HAC-IR proof fixtures,
runtime-plan proof fixtures, proof tests, and proof documentation.

## Motivation

Objective Alpha proof artifacts are public evidence for the Universal Compute
claim. Small changes to proof output can alter graph meaning, HAC-IR facts,
runtime placement, backend-set interpretation, or security assumptions.

Reviewers need a stable checklist that distinguishes intentional proof-contract
changes from accidental golden-file churn.

## Decision

Add a proof artifact review checklist covering:

- affected paths
- proof metadata expectations
- HAC-IR neutrality checks
- runtime-plan inspectability checks
- numerical reference checks
- security checks
- required validation commands
- golden-file update discipline

Link the checklist from the proof documentation, review policy, security
baseline, roadmap, and pull request template.

## Security Model

The checklist is documentation and does not add a runtime path.

It explicitly rejects proof changes that introduce backend plugin discovery,
dynamic imports, dynamic libraries, device access, network access,
generated-artifact execution, environment-dependent behavior, or host-path
leakage without a dedicated security RFC, threat model, resource budget, and
sandboxing plan.

## Consequences

- Proof reviewers have a repeatable merge gate.
- Golden proof updates require a stated contract reason.
- Future proof graph families can reuse the same review process.
- The project has a clearer path from runnable proof to external review
  confidence.

## Alternatives Considered

1. Rely only on the general pull request template.

   Rejected because proof artifacts combine compiler contracts, numerical
   correctness, runtime planning, and public evidence in one review surface.

2. Add a script that auto-approves proof golden changes.

   Rejected because proof golden changes require human interpretation.

3. Wait until JSON proof reports exist.

   Rejected because the current text proof reports already need review rules.

## Follow-Up

1. Add proof-specific PR body prompts if proof artifact changes become common.
2. Add optional machine-readable proof manifests after the text proof contract
   remains stable.
3. Revisit this checklist before any real hardware-backed proof.
