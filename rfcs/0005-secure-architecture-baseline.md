# RFC 0005: Secure Architecture And Standards Baseline

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adopts a secure-by-design baseline for its compiler architecture and
open-source process. The baseline is aligned with NIST SSDF, SLSA, OpenSSF
Scorecard, GitHub Actions hardening, and Apache-2.0 open-source licensing.

## Motivation

Compiler projects accumulate attack surface quickly: parsers, IR serializers,
backend plugins, runtime plans, generated artifacts, native code, caches, and
CI release jobs. TUC should not wait until those surfaces exist before defining
their trust boundaries.

The goal is to make secure defaults part of the project's shape from the first
public phases.

## Decision

TUC now treats these as architectural invariants:

- All source, IR, metadata, graph, backend capability, plugin, cache, and
  runtime-plan inputs are untrusted until validated.
- IR objects enforce bounded names, tensor shapes, attribute types, metadata
  size, and graph size.
- Backend capability checks are data-only and validated.
- Partition plans expose movement and transfer costs.
- CI uses least-privilege permissions by default.
- Supply-chain monitoring is enabled through Dependabot, CodeQL, dependency
  review, and OpenSSF Scorecard.
- Apache-2.0 is the project license.

## Non-Goals

- This RFC does not claim formal certification.
- This RFC does not create a release pipeline.
- This RFC does not add native-code fuzzing yet, because the project has no
  native parser or deserializer surface today.

## Required Follow-Up

1. Add branch protection on `main`.
2. Require CI and security checks before merging.
3. Add signed release artifacts and provenance before the first package release.
4. Add SBOM output before distributing binaries or wheels.
5. Add fuzz targets before accepting native parsers, IR deserializers, or
   plugin manifest parsers.
