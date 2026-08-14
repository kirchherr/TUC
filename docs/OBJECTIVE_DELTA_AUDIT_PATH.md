# Objective Delta Reduced-Dependency Audit Path

The reduced-dependency audit path lets a reviewer inspect and replay the core
Objective Delta contract without installing the TUC wheel or NumPy.

## Research Question

Can the fixed Objective Delta planning and semantic contract be reimplemented
from its public data using a small, isolated Python standard-library program?

For the repository's bounded v0 slice, the answer is **PASS**.

This is implementation-diversity evidence inside the TUC project. It is not an
independent organizational reproduction because the TUC project publishes both
implementations and the conformance vector.

## Audit Command

From a repository checkout:

```bash
python -I integration/objective_delta_audit/audit_reproducer.py \
  integration/objective_delta \
  integration/objective_delta_audit/conformance_vector.v0.json
```

`-I` starts Python in isolated mode. The script imports only `hashlib`, `json`,
`math`, `pathlib`, `sys`, `typing`, and `__future__` from the Python standard
library. It does not import TUC or NumPy.

The expected output is
`tests/golden/objective_delta_audit/report.json`. Its closed schema is
`schemas/objective_delta_audit_report.v0.schema.json`.

## Reimplemented Contract

The script independently performs these fixed steps:

1. read bounded JSON with duplicate-key and non-finite-number rejection;
2. require the exact Objective Delta Source Intent and data-only package
   policies;
3. select the only preferred capability for each operation;
4. derive `external-systolic -> external-vector`;
5. derive the required `blocked -> row_major` conversion;
6. evaluate the public `2 x 2` matrix multiplication followed by identity;
7. compare the result with the published expected public output; and
8. emit only contract metadata and canonical SHA-256 digests.

The public vector is
`integration/objective_delta_audit/conformance_vector.v0.json`, with schema
`schemas/objective_delta_conformance_vector.v0.schema.json`. It intentionally
contains the fixed, non-sensitive input and expected-output numbers so a
reviewer can write an implementation in another language. Raw values remain
outside the Objective Delta metadata-only proof report and reproduction
receipt.

## Security Boundary

- Each input is limited to 16 KiB and must be a regular non-symlink file.
- JSON duplicate keys, non-finite numbers, wrong shapes, unknown operations,
  policy drift, capability drift, ambiguous placement, and output mismatch
  fail closed.
- Rejection output is fixed and does not reveal paths or payload contents.
- The script does not use dynamic imports, `eval`, `exec`, plugins, native
  libraries, devices, network access, subprocesses, generated artifacts, or
  backend code.
- The report does not serialize tensor values.

The Python interpreter and this script are still executable software. A smaller
dependency surface improves auditability but does not establish that code is
benign. Review the script or run it in a disposable environment.

## Relation To The Release Kit

The [Objective Delta Reproduction Kit](OBJECTIVE_DELTA_REPRODUCTION_KIT.md)
tests the installed TUC distribution and requires its complete evidence report
to match byte for byte. This audit path answers a narrower but complementary
question: can the public fixed contract be understood and reimplemented without
executing the TUC package?

The audit path does not replace the installed reproduction. It cannot recreate
TUC's internal HAC-IR, execution trace, reference-correctness, or backend-
equivalence digests. It checks the externally observable fixed plan and
semantics.

## Claim Boundary

This work proves one same-project standard-library reimplementation of the
fixed Objective Delta contract. It does not prove:

- independent organizational reproduction;
- arbitrary Source Intent, packages, shapes, operations, or values;
- executable external backends or plugins;
- native or physical-device execution;
- performance parity; or
- software safety from provenance alone.

An external implementation or separately provenanced release receipt must be
reviewed before TUC claims independent reproduction.

Decision: `rfcs/0294-objective-delta-reduced-dependency-audit-path.md`.
