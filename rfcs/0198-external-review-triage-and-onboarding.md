# RFC 0198: External Review Triage And Research Onboarding

Status: Accepted

## Summary

Capture the 2026-06-22 external review as a bounded project triage and add a
short research onboarding page that lets reviewers run the first proof without
reading the whole repository.

## Motivation

The review correctly identified that TUC is strongest when it is framed as a
research proof, not a vendor compiler replacement. It also identified useful
pressure points: onboarding complexity, communication clarity, future
performance evidence, backend diversity, and broader integration evidence.

The project should adopt those points without diluting its core claim or
opening unsafe compiler surfaces.

## Design

Add two documentation artifacts:

1. `docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md`
   - records adopt-now, adopt-later, and do-not-adopt decisions;
   - keeps native performance and hardware integration as gated future proof
     classes;
   - rejects broad source parsing, plugin execution, and vendor replacement
     claims.
2. `docs/RESEARCH_ONBOARDING_SLICE.md`
   - presents the Objective Alpha graph-to-evidence path visually;
   - lists the smallest proof commands;
   - states what the current proof does and does not prove;
   - points contributors toward low-risk contribution lanes.

Update the README and roadmap so the onboarding path and triage decision are
discoverable from the top-level project surface.

## Security

This RFC adds documentation only. It does not add parsing, backend discovery,
dynamic imports, subprocess execution, device access, generated artifacts, or
benchmark ingestion.

The triage explicitly preserves TUC's secure-by-design boundaries:

- all external source, manifests, IR, evidence, and benchmark metadata remain
  untrusted input;
- backend capability checks remain data-only;
- runtime execution remains limited to trusted in-process prototype executors;
- performance claims remain blocked until the existing evidence gates accept
  them.

## Acceptance Criteria

- The review triage document exists and names adopted, later, and rejected
  items.
- The onboarding page shows the Objective Alpha proof shape and runnable
  commands.
- README links to the onboarding and triage pages.
- Roadmap priority order reflects onboarding clarity and review triage without
  promoting premature hardware integration.
- Tests assert the non-dilution language so future edits cannot silently turn
  the review response into a product or performance claim.

## Outcome

The project can use external feedback constructively while remaining a bounded,
secure, falsifiable Universal Compute research proof.
