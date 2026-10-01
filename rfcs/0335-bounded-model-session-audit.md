# RFC 0335: Bounded Model Session Audit

- Status: Implemented candidate
- Date: 2026-09-29
- Scope: Evidence verification only

## Summary

Add a standalone Python-standard-library verifier for the exact RFC 0334
model-session receipt. The verifier recomputes model and request identities and
the fixed numerical corpus without importing TUC or NumPy and without invoking
the native runtime.

## Motivation

RFC 0334 retained original installed Linux evidence and recorded a one-off
NumPy audit. That audit lived in a local temporary file and depended on TUC's
own parsing and framing functions. A reviewer could inspect the receipt, but
could not replay the complete audit from committed, dependency-reduced code.

This RFC closes that reviewability gap. It does not replace the observed native
run and cannot turn same-maintainer evidence into independent reproduction.

## Contract

The public artifact set is:

- `integration/bounded_cpu_model_session_audit/audit_receipt.py`;
- `schemas/bounded_model_session_audit_report.v0.schema.json`;
- `tests/golden/bounded_model_session_audit/report.json`; and
- `docs/evidence/bounded-model-session-36570752112.json` as immutable input.

The command accepts exactly one receipt path. A successful invocation emits one
canonical, sorted JSON report. Every rejection emits only
`bounded-model-session-audit: input rejected` and exits with status 2.

## Reimplemented Evidence

The verifier owns its fixed graph and parameter descriptions. It canonicalizes
the same neutral model identity structure and independently computes SHA-256
model digests. It reconstructs request frames from the bound program digest and
ordered binary32 inputs, weights and bias, then recomputes all request digests.

The numerical implementation rounds each Linear intermediate to binary32 and
implements the fixed row-Softmax equation with the same explicit rounding
points. Linear results require identical binary32 bits. Classifier values use
the published absolute/relative tolerance and row-mass bound.

## Trust And Security

The receipt is untrusted input. Before producing a report the verifier checks:

- regular non-symlink input and a 16-KiB byte limit;
- exact UTF-8 JSON with duplicate-key and non-finite-number rejection;
- closed envelope keys and fixed counter/rejection contracts;
- source, wheel, consumer, receipt, model, program and request identities;
- exact family coverage, sequence numbering and input corpus; and
- all numerical outputs plus preserved-result behavior.

The script uses only reviewed standard-library modules. It does not import TUC
or NumPy, write files, start subprocesses, access a network or device, discover
plugins, load libraries, compile code or execute generated artifacts.

## Alternatives

### Keep the temporary NumPy audit

Rejected because it is not a durable review surface and reuses TUC functions
for identities it claims to inspect.

### Repeat the native experiment

Rejected because repetition under the same maintainer does not add independent
provenance and increases the executable surface of an evidence-only step.

### Rebuild the C11 artifact in the auditor

Rejected because that would duplicate the compiler and weaken the small,
inspectable contract. Program digests remain explicitly bound rather than
independently reconstructed.

## Acceptance

- isolated `python -I` output matches the checked-in golden byte for byte;
- the report schema is closed;
- import-surface tests reject TUC, NumPy, subprocess, network, FFI and dynamic
  import paths;
- malformed, duplicate-key, oversized, identity-drifted and numerically
  modified receipts fail closed; and
- existing RFC 0334 evidence remains unchanged.

## Non-Claims

This RFC adds no new native observation, independent organizational evidence,
arbitrary model/input support, runtime admission, resident-weight guarantee or
performance claim.
