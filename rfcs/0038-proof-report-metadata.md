# RFC 0038: Proof Report Metadata

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Alpha

## Summary

TUC adds deterministic proof-report metadata for Objective Alpha proof
artifacts.

Each proof report now prints:

- `report_schema`
- `proof_id`
- `proof_version`
- `graph_family`
- `backend_set`

## Motivation

The proof ladder depends on reproducible reports that reviewers can compare
across graph families and backend sets. Before this RFC, the proof reports
showed input graph, HAC-IR, backend assignments, transfer plan, result, and
reference result, but did not state which proof contract or backend set the
report represented.

That makes future proof evolution harder to review. A report that changes graph
family, backend set, or proof version should say so explicitly before the
compiler artifacts begin.

## Decision

Add `tuc.proof.ProofReportMetadata` and
`tuc.proof.proof_metadata_from_partition_plan(...)`.

The metadata object validates bounded safe identifiers, rejects empty or
duplicate backend sets, sorts backend names deterministically, and renders a
stable line sequence for proof reports.

Both Objective Alpha proof examples now include a `== proof metadata ==`
section before the input graph.

## Security Model

Proof metadata is pure data derived from fixed proof configuration and an
already built runtime partition plan.

It does not:

- parse external proof files
- discover backend plugins
- import backend modules
- spawn subprocesses
- access devices
- execute generated artifacts
- read environment variables
- touch the network

Metadata strings and backend counts are bounded. Unsafe proof identifiers and
backend names fail closed before the report renders.

## Consequences

- Golden proof reports now make proof version, graph family, and backend set
  visible at the top of each artifact.
- Reviewers can tell whether a proof changed because of graph evolution,
  backend-set evolution, or compiler-output drift.
- Future proof artifacts can use the same metadata contract without inventing
  a new report format.

## Alternatives Considered

1. Keep metadata only in documentation.

   Rejected because reproducible proof artifacts need machine-checkable output,
   not only prose.

2. Put proof metadata into HAC-IR metadata.

   Rejected because proof identity and backend set are report-level evidence,
   not hardware-independent compute intent.

3. Serialize JSON reports immediately.

   Deferred because the current proof contract is intentionally plain text.
   JSON may be useful later, but would be a larger reporting-format change.

## Follow-Up

1. Add a reviewer-facing checklist for changing proof artifacts.
2. Add optional JSON proof reports only after the text proof contract remains
   stable.
3. Add future proof metadata fields through RFCs rather than ad hoc report
   edits.
