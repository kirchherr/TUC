# RFC 0287: Source Intent Elementwise Semantics v0

Status: Accepted

## Summary

Add a hardware-neutral `elementwise_kind` attribute to Source Intent and bind
it through Metadata and ComputeGraph `kernel` semantics. Restrict the research
parser to two exact, structurally recognized `tl.where` forms: ReLU and
identity. Reject all other forms.

## Motivation

The first Triton research portfolio preserved an operation family named
`elementwise` but did not preserve the value semantics of
`tl.where(projection > 0, projection, 0)`. Metadata therefore omitted a kernel
attribute and Runtime Executor used its legacy identity default.

Reference construction used the same default, so consistency and backend
equivalence could pass while the source-level ReLU meaning was absent. This was
a proof-validity defect: the abstraction was internally consistent but not
semantically closed against the bounded source.

## Decision

Source Intent v0 accepts optional `attributes.elementwise_kind` only on the
`elementwise` family. Its fixed values are `gelu`, `identity`, and `relu`.
Source Intent Metadata Conversion maps the neutral attribute to the existing
bounded Metadata and Runtime `kernel` attribute.

The research parser recognizes only:

```text
tl.where(x > 0, x, 0) -> relu
tl.where(x > 0, x, x) -> identity
```

The condition must be one `>` comparison against numeric zero. The true branch
must be the same named tensor. The false branch must be numeric zero or the
same tensor. Keywords and every other shape fail closed.

Missing `elementwise_kind` remains identity for compatibility with existing
Source Intent v0 data. Parser-produced elementwise intent is explicit.

## Security Consequences

The attribute is a closed semantic enum, not a callable or implementation
identifier. Intake rejects dotted entry points, commands, unknown names,
non-string values, and use outside the elementwise family. Parsing remains AST
inspection only; no import, decorator, JIT, plugin, device, subprocess, dynamic
library, network, path, or generated artifact surface is added.

Failing closed prevents unsupported `tl.where` semantics from being silently
approximated as identity.

## Evidence

- Source Intent Intake accepts the enum and rejects escape values.
- JSON Schema exposes the same closed enum.
- Metadata conversion binds `elementwise_kind=relu` to `kernel=relu`.
- Research parser tests cover exact ReLU and identity forms plus rejected
  condition, true-branch, and false-branch variants.
- A trusted execution test uses negative matrix-product outputs and requires
  exact ReLU results.
- Parser, execution bridge, Kernel Ingress, shape-profile, and Triton package
  portfolio goldens are regenerated from the corrected semantics.

## Alternatives Rejected

### Keep generic elementwise intent

Rejected because operation-family equivalence does not prove source value
semantics.

### Implement general `tl.where`

Rejected because predicate typing, broadcasting, scalar conversion, and
arbitrary branch semantics exceed the admitted research slice.

### Store Triton syntax in HAC-IR

Rejected because source-framework syntax is not hardware-neutral compute
semantics and would leak frontend details into the universal interface.

## Consequences

The strongest Triton research proof now binds its source-level ReLU to actual
trusted execution and independent reference correctness. TUC still makes no
claim of general Triton parsing or production source admission.
