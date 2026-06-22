# RFC 0190: Performance Readiness Toolchain Environment Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to digest-bound Toolchain Environment Report
evidence for the current Kernel Ingress proof slice.

This RFC does not run benchmarks, inspect host packages, read environment
variables, access devices, execute backend artifacts, load dynamic libraries,
discover plugins, execute generated code, or claim native performance parity.

## Motivation

Future performance evidence is not reviewable unless the relevant software
environment is explicit enough to identify. TUC already has a diagnostic
Toolchain Environment Report, but Performance Proof Readiness still treated
`versioned_toolchain_environment` as missing.

The next useful research step is to make the readiness gate recognize a bounded
repository-controlled toolchain declaration while keeping native performance
claims blocked.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `versioned_toolchain_environment` present only after:

1. building a Toolchain Environment Report through
   `build_toolchain_environment_report(...)`;
2. representing CI runtime, package metadata, development requirements, dev
   container image, native compiler policy, and compose environment as explicit
   `ToolchainComponent` entries;
3. binding every component to a `sha256:` digest of a repository-controlled
   file;
4. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `toolchain_environment_ready = true`;
5. rejecting forbidden host-data fields such as host paths, environment data,
   device identifiers, and hardware serials.

The bound component sources are:

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/dev.txt`
- `docker/dev/Dockerfile`
- `docker-compose.yml`

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding is data-only. It reads only repository files needed to compute
content digests. It must not collect local host package versions, read
environment variables, inspect devices, run discovery commands, execute backend
artifacts, invoke package managers, or store host paths.

The binding also does not turn unpinned dependency declarations into a
reproducible lockfile. Native baseline provenance, benchmark artifacts,
break-even workload evidence, native baseline comparison, performance threshold
policy, and executable backend security review remain separate blockers.

## Consequences

- Performance Proof Readiness now has a concrete versioned toolchain
  environment evidence item.
- The readiness report remains blocked for native performance claims.
- Toolchain review is tied to repository-controlled declarations instead of
  ambient host state.
- Future reproducibility work can refine this into lockfiles, provenance, and
artifact attestations without changing HAC-IR semantics.