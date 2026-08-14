# RFC 0294: Objective Delta Reduced-Dependency Audit Path

- Status: Accepted
- Date: 2026-08-14
- Owners: TUC maintainers

## Context

Objective Delta v0.1.0 can be replayed from a data-only release kit through an
installed TUC wheel. That validates the distribution boundary, but an unknown
Python package and NumPy create a significant trust and review burden for an
external researcher.

The current research claim is small enough to expose a second path. Its fixed
input values, two operations, two capability packages, one layout conversion,
and expected public output can be inspected and reimplemented without TUC
runtime imports.

## Decision

Add a reduced-dependency audit path with:

- one public, schema-versioned fixed conformance vector;
- one standalone Python script using only a narrow standard-library import
  allowlist;
- exact validation of the existing Source Intent and package policies;
- separate placement, layout-conversion, and numerical logic;
- one closed digest-only report schema and deterministic golden; and
- negative tests for package drift, duplicate keys, oversized inputs, ambiguous
  CLI arity, dependency-surface drift, and diagnostic disclosure.

The script must not import `tuc` or `numpy`. It must not discover or execute
plugins, package code, native libraries, generated artifacts, devices,
networks, or subprocesses.

## Trust And Claim Policy

The audit path is maintained in the TUC repository, so it is not independent
organizational evidence. Its report must keep
`independent_organizational_evidence = false` and block native execution,
physical-device portability, arbitrary-input, and performance claims.

The conformance vector intentionally publishes fixed raw values. Those values
must remain separate from the metadata-only Objective Delta proof report and
release receipt.

## Security Analysis

All four consumed files are untrusted input. The standalone reproducer must
bound byte size before JSON parsing, reject symlinks, duplicate keys and non-
finite values, require exact v0 structures, and fail closed with a source-free
public diagnostic. Its imports and dangerous-call surface are enforced by AST
tests.

The script itself remains executable Python. Standard-library-only operation
reduces dependency risk and review size; it is not a guarantee of benign
behavior.

## Consequences

Positive:

- reviewers can understand the experiment without installing TUC;
- the fixed contract now has public numerical test vectors;
- a third party can reimplement the same contract in another language; and
- the installed and reduced-dependency paths provide different checks against
  accidental implementation coupling.

Costs:

- the fixed semantics exist in two implementations and must remain aligned;
- this path cannot reproduce internal TUC evidence digests; and
- a future release must deliberately decide whether to package the audit path
  without changing the immutable v0.1.0 artifacts.

## Rejected Alternatives

- Treating checksums or attestations as a safety guarantee.
- Calling a same-project implementation independent evidence.
- Expanding Objective Delta's source, package, or executor scope before an
  external reproduction is reviewed.
- Replacing the installed-wheel proof with the smaller audit path.
