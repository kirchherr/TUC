# RFC 0147: Runtime Evidence Gate Matrix Coverage

## Status

Accepted.

## Context

Runtime Evidence Gate now binds backend-equivalence and portfolio Matrix
coverage to exact artifact IDs. That closed the immediate drift gap, but the
binding list still lived primarily in gate code and gate text output.

Reviewers need a deterministic data artifact that shows the exact Matrix
bindings accepted by the gate without executing artifacts or resolving paths.

## Decision

Introduce Runtime Evidence Gate Matrix Coverage v0.

The report is a data-only audit with schema:

```text
schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json
```

The deterministic example is:

```text
examples/runtime_evidence_gate_matrix_coverage.py
```

The deterministic golden is:

```text
tests/golden/proofs/runtime_evidence_gate_matrix_coverage_report.json
```

Runtime Evidence Gate builds the audit from the current Runtime Evidence Matrix
and its expected backend-equivalence/portfolio bindings, then fails closed if
the audit does not pass.

## Security Boundary

The audit compares bounded identifiers already present in Matrix records. It
does not resolve artifact IDs to filesystem paths, scan the repository, load
external artifacts, execute generated files, discover plugins, import backend
code, access devices, spawn subprocesses, touch the network, run JIT code, load
dynamic libraries, or authorize native execution.

It does not include tensor values, runtime handles, source text, host paths,
commands, device identifiers, generated code, backend artifacts, raw benchmark
output, or raw timing samples.

## Consequences

The gate-required Matrix coverage set is now reviewable as JSON, not just as
procedural assertions. Future changes to backend-equivalence or portfolio
coverage must update the binding report, schema/golden tests, docs, and Runtime
Evidence Gate together.
