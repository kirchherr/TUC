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
- Schema-versioned Triton metadata intake rejects reserved `tuc.*` attributes,
  unsupported schema versions, custom mapping subclasses, and known execution
  surface keys before producing a `ComputeGraph`; deterministic intake reports
  make the frontend boundary reviewable without importing, parsing, JITing, or
  executing Triton code.
- Triton idiom coverage reports use
  `schemas/triton_idiom_coverage_report.v0.schema.json` to track only bounded
  metadata-example and golden-evidence identifiers; they keep direct Triton
  source ingestion blocked and do not load source, Python objects, devices,
  plugins, backend artifacts, or generated code.
- Triton source ingestion is explicitly blocked by
  [TRITON_SOURCE_THREAT_MODEL.md](TRITON_SOURCE_THREAT_MODEL.md) until a
  data-only parser design includes source budgets, negative tests, fuzzing or
  property-test corpus, deterministic diagnostics, and sandboxing gates.
- Triton source preflight v0 parses caller-provided source text as bounded
  syntax data only, emits deterministic diagnostics, rejects imports,
  decorator calls, dangerous builtins, host/device/network/dynamic-library
  surfaces, unsupported calls, and `tuc.*` HAC-IR leakage, and never produces a
  `ComputeGraph`.
- Triton source preflight fuzz/property tests cover arbitrary decoded bytes,
  invalid Unicode, seed-corpus combinations, and diagnostic-volume pressure
  without opening source-to-IR ingestion.
- Runtime Executor v0 executes already-compiled graphs only through a fixed
  trusted in-process prototype executor registry, requires plain explicit NumPy
  inputs, validates partition-plan alignment and output shapes, fails closed for
  unknown executor backends or unsupported executor operation kinds, and emits
  deterministic execution traces without plugin discovery, dynamic imports,
  subprocesses, device access, network access, JIT, dynamic libraries, or
  generated-artifact execution.
- Trusted runtime backend executor contracts expose the fixed in-process
  executor registry as bounded pure data with deterministic golden evidence.
  The v0 contract requires `in_process_reference_kernel`, forbidden external
  artifacts, forbidden device access, and the same blocked execution surfaces
  as Runtime Executor v0.
- Runtime execution readiness reports validate already-compiled graphs and
  runtime plans against trusted backend executor contracts before any operation
  executes, failing closed for untrusted backend contracts or unsupported
  operation/backend assignments.
- Triton-like MVP metadata execution carries readiness evidence across
  `matmul`, `softmax`, `reduction`, and `elementwise` before execution.
- Runtime Evidence Matrix v0 inventories proof/runtime evidence through bounded
  identifiers only, rejects path-like IDs and known execution surfaces, derives
  missing-evidence issues deterministically, and never scans repositories,
  imports code, discovers plugins, or executes artifacts.
- Runtime operation semantic contracts validate MVP operation shape and axis
  rules before trusted reference kernels run, preventing implicit NumPy
  broadcasting, scalar reductions, unsupported elementwise kernels, or
  backend-specific shape interpretation from becoming hidden behavior.
- Runtime tensor value contracts require external inputs and operation outputs
  to match declared shapes, use `float64`, and contain only finite values,
  failing closed before dtype, shape, or non-finite-value drift can reach later
  runtime steps.
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
- Proof artifact review checklist requires maintainers to review proof metadata,
  HAC-IR neutrality, runtime-plan inspectability, deterministic reference
  semantics, golden-file discipline, and absence of new plugin, subprocess,
  device, network, generated-artifact, host-path, or environment-dependent
  proof surfaces.
- HS-IR v0 contracts for backend assignments, produced layouts,
  movement-summary metadata, and runtime-transfer-summary consistency.
- Backend API v0.1 explicitly limits external backend onboarding to
  declarative manifests and trusted in-process prototypes; no auto-discovery,
  plugin loading, dynamic libraries, subprocesses, or artifact execution.
- Explicit backend capability registry for caller-provided manifest paths and
  trusted in-memory capabilities, with bounded backend count, unique safe names,
  directory non-scanning, pure-data support diagnostics, and no backend object
  execution.
- Compiler decision reports derive accepted and rejected backend candidate
  evidence from validated HAC-IR operations, explicit capability data, registry
  diagnostics, and runtime plans without plugin discovery, imports,
  subprocesses, dynamic libraries, device access, network access, or generated
  artifact execution.
- Golden compiler decision-report fixtures verify backend support evidence and
  fallback reasoning from fixed in-repository graphs and trusted in-memory
  capability data without adding generator execution.
- Runtime manual override policy in
  [RUNTIME_OVERRIDE_POLICY.md](RUNTIME_OVERRIDE_POLICY.md) blocks any future
  placement override implementation unless it is schema-versioned, bounded,
  operation-scoped, fail closed, visible in compiler decision reports and
  runtime-plan dumps, and free of plugin discovery, imports, subprocesses,
  dynamic libraries, device access, network access, host-path reads,
  environment-dependent behavior, or generated-artifact execution.
- Runtime manual override v0 implements that gate with `RuntimeOverrideSet`,
  `tuc.runtime_overrides.v0`, positive and negative tests, compiler
  decision-report goldens, and runtime-plan goldens. Overrides are accepted only
  after graph and capability validation, and only for already accepted backend
  candidates.
- Runtime candidate score diagnostics are opt-in bounded `CandidateScore`
  records derived from validated graph operations, capability data, movement
  estimates, transfer-cost profiles, and override effects. They do not execute
  backend code, discover plugins, import modules, spawn subprocesses, load
  dynamic libraries, access devices, execute generated artifacts, touch the
  network, read host paths, read environment variables, change HAC-IR, or alter
  default placement behavior.
- Softmax operation-family planning defines the nonlinear proof gate before
  softmax proof graphs, decomposition paths, or softmax-specific scoring can be
  accepted. The contract keeps decomposition, approximation, backend support,
  noise assumptions, calibration evidence, and generated artifacts outside
  HAC-IR semantics.
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
- Executable backend security review reports provide a diagnostic, data-only
  evidence contract for future executable surfaces. They require threat-model,
  sandbox, resource-budget, provenance, fuzzing or negative-test evidence,
  maintainer approval, and digest identifiers before an executable surface can
  count as performance-proof evidence. They do not approve execution by
  themselves.
- Performance proof RFC reports provide a diagnostic, data-only governance
  contract for future native performance claims. They require scoped workload,
  threshold-policy, acceptance-criteria, evidence-bundle, security-review,
  maintainer-acceptance, and digest identifiers before benchmark artifacts can
  be interpreted as claim evidence. They do not load artifacts, parse raw
  benchmark output, grant execution permission, or prove native performance.
- Performance claim threshold policy reports provide a diagnostic, data-only
  governance contract for future native performance thresholds. They require
  scoped workload, comparison metric, summary policy, threshold kind, integer
  basis points, maintainer acceptance, and digest identifiers before
  percentage or "near native" claims can be reviewed. They do not ingest
  timing samples, load benchmark artifacts, grant execution permission, or
  prove native performance.
- Performance acceptance criteria reports provide a diagnostic, data-only
  governance contract for future native performance pass/fail rules. They
  require scoped workload, threshold policy, correctness evidence, methodology,
  native comparison, planner-overhead, break-even, leaky-abstraction, and
  executable-surface security identifiers before benchmark artifacts can be
  treated as passing evidence. They do not ingest timing samples, load
  benchmark artifacts, grant execution permission, or prove native performance.
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
- If manual placement overrides are involved, do they follow
  [Runtime manual override policy](RUNTIME_OVERRIDE_POLICY.md)?

Every PR that touches CI, dependencies, containers, release automation, or
credentials must answer:

- What can write to the repository, artifacts, packages, or security results?
- Are token permissions least-privilege?
- Are third-party actions and dependencies reviewed?
- Is provenance or attestation required now or documented as pre-release work?
