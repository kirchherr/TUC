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
- HAC-IR v0 dialect contracts for operation arity, compiler-produced
  attributes, known user hints, and fail-closed rejection of unknown reserved
  `tuc.*` attributes.
- HAC-IR semantic charter separates compute intent, compiler facts, planning
  constraints, and forbidden backend details before future native IR work.
- HAC-IR neutrality guardrails and negative tests for known high-risk hardware,
  backend, device, plugin, and generated-artifact leakage attributes.
- HAC-IR golden dump fixtures for proof and MVP graphs, generated from fixed
  typed graph builders without plugin discovery, subprocesses, device access,
  network access, or generated-artifact execution.
- Second Objective Alpha proof graph covers reduction intent with bounded
  in-repository tensors, trusted in-memory capability data, deterministic
  reference kernels, and golden proof/runtime artifacts.
- Proof-report metadata validates bounded safe proof identifiers and backend
  sets, derives backend names from existing partition plans, and does not add
  parsing, plugin discovery, subprocess, device, network, or artifact execution
  surfaces.
- HS-IR v0 contracts for backend assignments, produced layouts,
  movement-summary metadata, and runtime-transfer-summary consistency.
- Backend API v0.1 explicitly limits external backend onboarding to
  declarative manifests and trusted in-process prototypes; no auto-discovery,
  plugin loading, dynamic libraries, subprocesses, or artifact execution.
- Explicit backend capability registry for caller-provided manifest paths and
  trusted in-memory capabilities, with bounded backend count, unique safe names,
  directory non-scanning, pure-data support diagnostics, and no backend object
  execution.
- Backend author certification requires negative tests for plugin-like manifest
  fields, duplicate keys, unsupported schemas, false capability claims,
  unsupported layouts, and lower-time operation rejection.
- Backend conformance fixtures check trusted in-process backends without plugin
  discovery, imports, subprocesses, dynamic libraries, device access, file I/O,
  or artifact execution.
- External-style backend author path proves manifest loading, registry
  diagnostics, compiler planning, conformance, and trusted lowering without
  backend auto-discovery or compile-time plugin execution.
- Deterministic backend conformance report artifacts with schema versioning and
  report field-size limits; report dumping is pure data serialization and does
  not include backend artifact contents.
- Backend capability schema documentation separates error-budget, latency,
  energy, calibration, and noise assumptions from HAC-IR semantics, backend
  executable behavior, and hardware certification claims.
- Capability-schema negative examples and tests reject misleading latency,
  energy, calibration, benchmark, certificate, measured-error, and executable
  backend claims from backend capability manifests.
- Native MLIR design spike limited to repository-owned text artifacts; no
  external MLIR ingestion or native parser surface yet.
- Read-only default GitHub workflow permissions.
- Dependabot configuration for GitHub Actions, Python, and Docker updates.
- CodeQL, dependency review, and OpenSSF Scorecard workflows.
- Branch protection policy for `main` requiring pull requests, review,
  conversation resolution, strict `python`, `CodeQL`, and `Dependency Review`
  checks, and disabled force pushes/deletions.
- Pre-publish release artifact workflow with least-privilege OIDC-backed
  GitHub attestations, CycloneDX SBOM generation, SHA-256 checksums, and no
  registry publishing permissions.
- Release workflow action SHA pinning and release governance policy for tag
  rulesets, publishing environments, and PyPI Trusted Publishing.
- Isolated PyPI publishing job with OIDC Trusted Publishing, no stored PyPI
  token, `v*` tag gating, and `pypi` environment approval.
- CODEOWNERS and review policy for compiler, runtime, backend, governance, and
  release trust-boundary changes.
- Apache-2.0 license and NOTICE file.

## Supply Chain Baseline

Development:

- Use the Docker environment for repeatable local tooling.
- Keep CI read-only unless a job must write security results.
- Do not use `pull_request_target` without a dedicated threat model.
- Do not expose deploy keys or repository secrets to untrusted pull requests.
- Use Dependabot PRs to review dependency drift.

Pre-release requirements:

1. Apply GitHub tag rulesets and publishing environments before any public
   release.
2. Produce release artifacts only from protected branches or tags.
3. Verify maintainer approval and OIDC-based publishing before any PyPI, GHCR,
   or external registry release.
4. Add native-code sanitizers and fuzzers before accepting native parsers,
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
