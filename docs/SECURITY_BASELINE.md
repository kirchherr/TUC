# Security And Standards Baseline

TUC is a compiler project, so its security baseline must cover ordinary
open-source hygiene and compiler-specific attack surfaces. This document is the
near-term baseline for architecture, implementation, CI, and release planning.

## Standards Alignment

TUC aligns its early process with:

- NIST SSDF SP 800-218 for secure software development practices.
- SLSA Build track for future release provenance and build integrity.
- OpenSSF Scorecard for machine-checkable open-source security posture.
- GitHub Actions secure-use guidance for least-privilege CI.
- Apache-2.0 licensing for a permissive open-source project with patent terms.

These references are intentionally international and ecosystem-recognized. They
do not make TUC certified; they define the direction and review gates.

## Compiler Security Invariants

All compiler-facing data is untrusted until validated:

- Source text and frontend metadata.
- Tensor names, shapes, dtypes, and graph topology.
- IR attributes and serialized IR.
- Backend capability metadata.
- Plugin manifests, cache entries, generated artifacts, and runtime plans.

Required controls:

- Parse into data, not behavior.
- Validate before lowering.
- Keep graph, tensor, attribute, and metadata budgets.
- Make backend and runtime decisions inspectable.
- Never execute plugin code during capability checks.
- Reject unsupported operations instead of silently falling back when semantics
  would change.
- Keep deterministic dumps for every IR stage.

## Current Technical Baseline

Implemented now:

- Bounded tensor rank and dimensions.
- Identifier-safe tensor, operation, and graph names.
- Immutable, canonical IR attributes and graph metadata.
- Attribute type, nesting, key-count, string-size, and total-size budgets.
- Backend capability validation for operation sets, preferences, error budgets,
  memory domains, accepted layouts, and produced layouts.
- Movement-aware partition plan metadata with transfer-byte accounting.
- Validated in-memory transfer-cost profiles with finite numeric bounds and no
  executable backend hooks.
- Schema-versioned JSON manifest loading with file-size, duplicate-key,
  nesting, string, numeric, and unknown-field rejection.
- Native MLIR design spike limited to repository-owned text artifacts; no
  external MLIR ingestion or native parser surface yet.
- Read-only default GitHub workflow permissions.
- Dependabot configuration for GitHub Actions, Python, and Docker updates.
- CodeQL, dependency review, and OpenSSF Scorecard workflows.
- Apache-2.0 license and NOTICE file.

## Supply Chain Baseline

Development:

- Use the Docker environment for repeatable local tooling.
- Keep CI read-only unless a job must write security results.
- Do not use `pull_request_target` without a dedicated threat model.
- Do not expose deploy keys or repository secrets to untrusted pull requests.
- Use Dependabot PRs to review dependency drift.

Pre-release requirements:

1. Pin release workflows and high-risk third-party actions to commit SHAs.
2. Produce release artifacts only from protected branches or tags.
3. Generate and publish provenance or GitHub artifact attestations.
4. Publish an SBOM or dependency inventory for release artifacts.
5. Add native-code sanitizers and fuzzers before accepting native parsers,
   deserializers, or backends.

## Review Gates

Every PR that touches compiler or runtime behavior must answer:

- What input boundary changed?
- What invariants are enforced before lowering?
- What resource budget applies?
- Does any new path execute code, import modules, spawn processes, or load
  dynamic libraries?
- How can a maintainer inspect the resulting decision?
- What negative tests cover malformed or malicious input?

Every PR that touches CI, dependencies, containers, release automation, or
credentials must answer:

- What can write to the repository, artifacts, packages, or security results?
- Are token permissions least-privilege?
- Are third-party actions and dependencies reviewed?
- Is provenance or attestation required now or documented as pre-release work?
