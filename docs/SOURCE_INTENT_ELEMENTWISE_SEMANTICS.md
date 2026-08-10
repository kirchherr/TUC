# Source Intent Elementwise Semantics

Source Intent Elementwise Semantics v0 preserves the observable meaning of a
bounded elementwise source operation before metadata conversion, HAC-IR
construction, planning, or trusted execution.

## Contract

- Source Intent attribute: `elementwise_kind`
- Accepted values: `gelu`, `identity`, `relu`
- Owning operation family: `elementwise`
- Metadata and ComputeGraph attribute: `kernel`
- Decision: `rfcs/0287-source-intent-elementwise-semantics.md`

`elementwise_kind` is hardware-neutral. It describes value semantics and does
not select a backend, device, layout, memory domain, package, or implementation.
Source Intent Intake rejects unknown values, non-string values, and use on any
other operation family.

For compatibility with existing Source Intent v0 payloads, an elementwise
operation without `elementwise_kind` retains the existing identity default.
New source-parser mappings must emit an explicit kind whenever source syntax
determines one.

## Research Parser Slice

The execution-free research parser recognizes exactly two `tl.where` forms:

```python
tl.where(x > 0, x, 0)  # elementwise_kind = relu
tl.where(x > 0, x, x)  # elementwise_kind = identity
```

Numeric `0` and `0.0` are accepted. The condition, true branch, and false
branch are inspected structurally as AST data. Any different comparison,
operand, branch value, arity, or keyword form fails closed.

This is not general `tl.where` support. TUC does not infer arbitrary predicates,
broadcast semantics, scalar promotion, callable behavior, or control flow from
this slice.

## End-To-End Binding

The accepted path is:

```text
bounded tl.where syntax
  -> source_intent.v0 attributes.elementwise_kind
  -> metadata attributes.kernel
  -> ComputeGraph attributes.kernel
  -> trusted runtime elementwise kernel
  -> independent reference comparison
```

Tests include a negative-valued matrix product so that an accidental identity
lowering cannot satisfy the ReLU proof.

## Security Boundary

- No source, module, decorator, callable, or JIT execution is introduced.
- The enum cannot contain import paths, plugin entry points, code, or commands.
- Unknown semantics are rejected instead of approximated as identity.
- Backend selection remains capability-driven and outside Source Intent.
- Production source ingestion remains blocked.

Future elementwise semantics require an RFC, a bounded enum addition, intake
and schema tests, metadata and runtime binding tests, parser rejection cases,
and value-level reference evidence.
