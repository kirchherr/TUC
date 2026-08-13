# RFC 0199: Research Onboarding Evidence

Status: Accepted

## Summary

Add Research Onboarding Evidence v0: a data-only report that binds the first
public Objective Alpha proof path to fixed commands, documentation paths,
blocked claims, blocked runtime execution surfaces, and a deterministic digest.

## Motivation

The external review triage accepted one immediate improvement: make the first
proof path easier to understand without weakening the research boundary. The
onboarding page explains the path for humans. This RFC adds the machine-readable
companion so reviewers can inspect the path as deterministic evidence.

## Design

Add:

- `src/tuc/research_onboarding.py` for the report model;
- `examples/research_onboarding_evidence.py` for deterministic emission;
- `schemas/research_onboarding_report.v0.schema.json` for fail-closed shape;
- `docs/RESEARCH_ONBOARDING_EVIDENCE.md` for the review contract;
- `tests/golden/proofs/research_onboarding_report.json` for stable evidence;
- `tests/test_research_onboarding_evidence.py` for contract, schema, and
  non-claim checks.

The report records only fixed constants. It does not run the proof commands.
The commands remain visible so humans can reproduce the onboarding path from
`docs/RESEARCH_ONBOARDING_SLICE.md`.

## Security

This RFC adds no parser, plugin discovery, dynamic import, subprocess call,
device access, benchmark ingestion, or generated-artifact execution. It rejects
path traversal, URLs, host path markers, raw tensor values, raw timing samples,
plugin entrypoints, dynamic libraries, generated code, and source text markers
in report fields.

## Consequences

The first public entry path is now both readable and reviewable. Future changes
that alter the onboarding proof path must update the report, schema, golden,
tests, documentation, and roadmap status together.
