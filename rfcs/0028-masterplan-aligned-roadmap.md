# RFC 0028: Masterplan-Aligned Roadmap

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: strategic alignment

## Summary

TUC replaces the older compiler-centric roadmap with a masterplan-aligned
roadmap organized around proof phases:

- Phase Alpha: Smallest Unarguable Proof
- Phase Beta: HAC-IR Contract
- Phase Gamma: Capability Framework
- Phase Delta: Runtime Planning
- Phase Epsilon: Real Triton Integration
- Phase Zeta: Specialized Hardware Proofs
- Phase Eta: External Integration And Governance

## Motivation

The project identity changed from "build a compiler" to **The Universal
Compute**: proving that compute intent can flow through a hardware-independent
interface into capability-driven runtime planning and correct execution.

The roadmap must reflect that identity. A roadmap led by Triton compatibility,
compiler implementation, backend work, and performance risks pulling the project
back toward "another compiler." A roadmap led by proof phases keeps the project
focused on hardware independence.

## Decision

Rewrite `ROADMAP.md` so that:

- The master plan is explicitly authoritative.
- Every roadmap item is gated by hardware independence, HAC-IR strength,
  vendor extensibility, reproducibility, and secure-by-design boundaries.
- Triton integration becomes a credibility milestone after the abstraction proof
  is stable.
- Specialized hardware work is framed as proof expansion, not project identity.
- Runtime planning and backend capabilities become first-class proof assets.

Update `docs/ROADMAP_STATUS.md` to match the new phase vocabulary.

## Security Model

The roadmap explicitly rejects new execution surfaces until separate security
work exists:

- no auto-discovery
- no dynamic backend imports
- no subprocess-based backend probing
- no dynamic library loading
- no device access
- no generated-artifact execution

Future native parser, native MLIR dialect, plugin lifecycle, and artifact
execution work must be introduced through dedicated security RFCs, negative
tests, fuzzing/sanitizer plans where relevant, and sandboxing models.

## Consequences

- Project decisions now prioritize proof quality over implementation breadth.
- HAC-IR neutrality becomes a roadmap gate, not a documentation footnote.
- Backend work remains capability-first.
- Runtime planning explanations become central to the proof.
- Triton remains important, but as a real-world integration milestone rather
  than TUC's identity.

## Follow-Up

1. Add a HAC-IR neutrality checklist.
2. Add golden runtime-plan dumps for proof-of-abstraction graphs.
3. Add an external-style backend author test.
4. Integrate compiler decision reports once that branch lands.
