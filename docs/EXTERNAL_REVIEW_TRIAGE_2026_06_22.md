# External Review Triage 2026-06-22

This document records the project response to an external review dated
2026-06-22. It is intentionally a triage artifact, not a product roadmap reset.

TUC remains a research prototype for proving whether compute intent can move
through a hardware-independent interface into capability-driven runtime
planning and controlled execution. It is not a CUDA, ROCm, XLA, TVM, IREE, or
vendor compiler replacement claim.

## Review Signal

The review identified five constructive pressure points:

1. New contributors face a steep conceptual learning curve.
2. Performance evidence is intentionally blocked but still needs a visible
   path toward future measurement.
3. Backend diversity is currently mostly prototype and simulator based.
4. The public entry point can be too technical for non-specialist reviewers.
5. Golden tests are strong, but broader integration and system-level evidence
   should continue to grow.

## Adopt Now

### Research Onboarding Slice

Adopt the onboarding critique immediately by keeping a short, visual first path
from the claim to executable evidence:

- one page that explains the Objective Alpha proof shape;
- exact commands for the smallest runnable proof;
- links to the proof inventory, runtime evidence, frontend intake, and
  performance boundary;
- explicit non-claims for native performance parity, broad source parsing,
  device access, and production backend support.

This is captured in `docs/RESEARCH_ONBOARDING_SLICE.md`.

### Communication Boundary

Adopt clearer public framing:

- "research proof" before "compiler";
- "hardware-independent interface" before "backend implementation";
- "correctness, inspectability, and evidence" before "speed";
- "controlled prototype executors" before "hardware integration".

This keeps the project understandable without turning it into marketing copy.

### Performance Evidence Path

Keep the current performance work, but describe it as a future proof class:

- baseline provenance;
- baseline comparison;
- planner overhead;
- break-even workload size;
- workload scope;
- methodology;
- toolchain environment;
- artifact manifest;
- executable backend security review;
- claim RFC, threshold policy, acceptance criteria;
- post-readiness measurement interpretation.

No benchmark number becomes a claim until the Performance Proof Boundary,
Performance Proof Readiness, and Performance Proof Interpretation gates all
accept it. Until then, native performance claims remain blocked.

### Integration Evidence Growth

Continue expanding system evidence only when it reinforces the current proof:

- runtime executor conformance;
- backend equivalence portfolio evidence;
- source-to-intent research ingress;
- metadata-only execution receipts and public output bundles;
- fail-closed security gates for every new input boundary.

## Adopt Later

### Real Hardware Integration

Real hardware integration is strategically useful, but it must not be the next
default proof center. It can enter only as a bounded research slice after:

- the backend surface remains capability-data first;
- executable backend security review covers the new surface;
- no dynamic plugin discovery is introduced;
- no user-controlled source, manifest, or artifact is executed during
  validation;
- benchmark evidence remains separated from correctness evidence.

A future Triton-backed or MLIR-backed experiment should be framed as a
controlled hardware-adjacent proof, not as production GPU support.

### Broader Integration And System Tests

More system-level testing is useful after each proof slice has a stable public
contract. The priority is not to replace golden tests, but to compose them into
larger evidence bundles whose failure messages stay explainable.

### External Contributor Path

Community growth matters, but it should be earned through crisp contribution
lanes:

- documentation and onboarding improvements;
- manifest-only backend author examples;
- negative security fixtures;
- reproducible evidence artifacts.

Governance should not expand faster than the number of real maintainers and
reviewers.

## Do Not Adopt

The following review-adjacent ideas would dilute TUC if adopted now:

- claiming that TUC replaces vendor compiler stacks;
- adding broad PyTorch, Triton, or arbitrary Python source parsing;
- making GPU or any hardware family the implicit center of the project;
- accepting performance comparisons without claim thresholds and methodology;
- adding auto-discovered plugins, dynamic imports, dynamic libraries,
  subprocess execution, device access, or generated-artifact execution;
- turning HAC-IR into a container for vendor-specific performance knobs;
- optimizing for stars, hype, or benchmark wins before proof closure.

## Roadmap Consequence

The review strengthens the current path rather than changing it. The near-term
order is:

1. Keep the research claim short and falsifiable.
2. Make the first-run proof path easier to follow.
3. Continue runtime and backend-equivalence evidence.
4. Keep performance as a gated future proof class.
5. Add hardware-adjacent experiments only after the security and evidence
   contracts can contain them.

## Security Consequence

Every adopted item preserves the secure-by-design boundary:

- source, manifests, IR, evidence reports, and benchmark metadata remain
  untrusted input;
- validation remains separate from lowering and execution;
- backend capability checks remain data-only;
- runtime evidence remains metadata-only unless a dedicated RFC changes that;
- unsupported surfaces fail closed with structured diagnostics.
