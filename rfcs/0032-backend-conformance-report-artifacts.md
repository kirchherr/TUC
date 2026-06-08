# RFC 0032: Backend Conformance Report Artifacts

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma

## Summary

TUC adds deterministic backend conformance report artifacts.

Backend conformance already verifies whether a trusted prototype backend agrees
with its declared capability data. This RFC makes that evidence serializable as
a stable JSON artifact that maintainers can review and backend authors can
attach to future proposals.

## Motivation

The external backend author path proves that a toy backend can be described,
planned, checked, and lowered without modifying TUC core. The next step is to
make the conformance evidence itself reproducible.

Maintainers should not need to execute backend artifacts or inspect opaque
backend output to understand whether a backend passed the current baseline. A
small deterministic report lets reviews focus on checked cases, pass/fail
status, and explicit issues.

## Decision

Add:

- `CONFORMANCE_REPORT_SCHEMA_VERSION`
- `conformance_report_to_dict(...)`
- `dump_backend_conformance_report(...)`
- `tests/golden/backend_conformance/external_vector_report.json`

The report schema records:

- Backend name.
- Checked conformance cases.
- Conformance issues.
- Pass/fail status.
- Report schema version.

The external backend author example now prints the conformance report before
the runtime plan and prototype lowering artifact.

## Security Model

Conformance report dumping is pure data serialization:

- It does not discover plugins.
- It does not import backend modules.
- It does not spawn subprocesses.
- It does not load dynamic libraries.
- It does not touch devices.
- It does not execute generated artifacts.
- It does not include backend artifact contents.

Report field sizes, issue counts, case counts, and total output bytes are
bounded before artifact text is emitted.

## Consequences

- Backend conformance evidence becomes stable and reviewable.
- Future backend proposals can attach report artifacts without exposing
  executable output.
- Maintainers can compare conformance drift through golden files.
- The report schema can evolve independently from backend plugin lifecycle
  work.

## Alternatives Considered

1. Print ad hoc text summaries only.

   Rejected because ad hoc text is harder to diff, version, and validate.

2. Include backend lowering artifacts in the report.

   Rejected because backend artifacts may become large, opaque, or executable
   in later phases. The report should summarize conformance evidence, not
   carry backend output.

3. Require file-writing helpers now.

   Rejected because callers can store the deterministic string themselves. TUC
   does not need a filesystem-writing helper at this stage.

## Follow-Up

1. Add capability schema documentation for error, latency, energy, and
   calibration assumptions.
2. Add report schema versioning policy if report consumers appear.
3. Add signed or attested conformance evidence only after release governance
   needs it.
