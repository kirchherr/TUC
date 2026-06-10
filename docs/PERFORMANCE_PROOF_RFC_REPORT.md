# Performance Proof RFC Report

Performance Proof RFC Report is a diagnostic review artifact for future native
performance proof proposals.

It records whether the claim proposal itself is scoped, accepted, digest-pinned,
and linked to bounded evidence. It is not a benchmark report, not an execution
permission, and not a native performance proof.

The report does not run benchmarks, ingest benchmark artifacts, access devices,
inspect host hardware, execute backend artifacts, execute generated code,
discover plugins, load dynamic libraries, run subprocesses, or claim native
performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema: `schemas/performance_proof_rfc_report.v0.schema.json`
- Report schema version: `tuc.performance_proof_rfc_report.v0`
- Evidence type: `PerformanceProofRFC`
- API: `build_performance_proof_rfc_report(proposal_name, rfcs)`
- Dump API: `dump_performance_proof_rfc_report(report)`
- Example: `examples/performance_proof_rfc_report.py`
- Tests: `tests/test_performance_proof_rfc_report.py`
- Schema tests: `tests/test_performance_proof_rfc_schema.py`

The report is ready only when at least one RFC is present, every RFC is
`accepted_by_maintainers`, all required evidence identifiers are supplied, and
each RFC has a SHA-256 digest. Even then, `native_performance_claim` remains
`false`; readiness means the proposal metadata is reviewable, not that the
performance claim has been proven.

## RFC Fields

Each RFC entry is bounded plain data:

- `rfc_id`: stable performance-proof RFC identifier
- `workload_scope_id`: linked workload-scope report identifier
- `claim_threshold_policy_id`: predefined threshold policy identifier
- `acceptance_criteria_id`: acceptance-criteria identifier
- `evidence_bundle_id`: bounded evidence-bundle identifier
- `security_review_id`: executable-surface security review identifier
- `rfc_status`: `draft`, `reviewed_not_accepted`, or
  `accepted_by_maintainers`
- `rfc_digest`: `not_supplied` or `sha256:<64 lowercase hex chars>`

IDs are safe identifiers, not paths or command lines.

## Security Boundary

Performance proof RFC reports must not include raw benchmark output, raw timing
samples, tensors, host paths, command lines, environment variables, hardware
serials, device identifiers, generated artifacts, generated code, plugin
entrypoints, backend binaries, backend artifact contents, native source
contents, dynamic-library paths, cache paths, URLs, credentials, or execution
permission.

The report is a claim-governance boundary. It links to evidence IDs; it does
not load evidence, parse benchmark output, inspect native artifacts, execute
backend code, or grant device access.

Unknown fields fail closed through the schema. Duplicate RFC identifiers,
unknown status values, path-like identifiers, and invalid digests fail closed in
the runtime builder.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance
- claiming near-native performance without an accepted threshold policy
- hiding planner overhead inside execution timing
- treating benchmark output as proof without bounded artifacts and security
  review
- executing backend artifacts or device code as part of RFC review
