# Compiler Decision Report

The compiler decision report connects backend support diagnostics to the
runtime assignment that TUC actually chose.

It answers:

- Which backend was assigned to each operation?
- Which registered backend capabilities accepted the operation?
- Which registered backend capabilities rejected the operation?
- Which pure-data reason code explains each accept or reject decision?
- Why did runtime planning choose the final assignment?
- Did a manual runtime override affect candidate selection?

This is a compiler-level inspectability artifact. It does not replace HAC-IR,
HS-IR, or runtime plans.

## Example

```python
result = compile_graph(graph, registry.capabilities())
print(result.dump_decision_report())
```

Example output:

```text
compiler.decision_report @mlp {
  operation projection kind=matmul assigned=linear-sim accepted_backends="linear-sim" rejected_backends="-" reason="preferred_for:matmul;domain=analog_weight_bank;transfer_bytes=0;layout_conversion_bytes=0;produced_layout=row_major"
  support {
    linear-sim accepted reason="accepted" detail="capability accepts operation kind, layout, and error budget"
  }
}
```

## Relationship To Backend Registry

`BackendRegistry.diagnose_operation_support(...)` explains whether each
registered backend capability accepts one operation.

The compiler decision report embeds those support diagnostics next to the
assignment selected by runtime planning. This makes it clear when an operation
was assigned to:

- a supported registered backend
- a fallback backend because no registered capability accepted the operation
- a backend chosen after transfer/layout planning
- a backend selected through an accepted manual override constraint

Manual override effects are reported in a `manual_overrides` block. The block is
present only when a `RuntimeOverrideSet` affects placement. The override
contract is defined by
[Runtime manual override policy](RUNTIME_OVERRIDE_POLICY.md).

## Security Model

The report is pure data built from:

- validated HAC-IR graph operations
- explicit backend capability data
- registry support diagnostics
- the runtime partition plan
- schema-versioned runtime override effects

It does not:

- execute backend code
- discover plugins
- import modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- read environment variables
- touch the network

Backend names are already bounded by the registry. Operation names, kinds,
attributes, tensor shapes, and metadata are validated before HAC-IR lowering and
before HS-IR specialization.

## Review Use

Use the decision report when reviewing changes to:

- backend capability schemas
- backend manifests
- partitioning rules
- fallback behavior
- transfer-aware placement
- manual placement overrides
- proof artifacts that include backend assignment reasoning

If a backend is rejected, the report should show a short reason code such as
`unsupported_operation_kind`, `unsupported_layout`,
`invalid_error_budget_attribute`, or `error_budget_exceeds_backend_limit`.

If an operation falls back, reviewers should be able to see which registered
backends rejected it and why.

## Golden Fixtures

Representative decision reports are locked as plain-text fixtures under:

```text
tests/golden/compiler_decisions/
```

`tests/test_compiler_decision_report_golden.py` compares proof and MVP graph
reports against those fixtures. Fixture changes are compiler-contract changes:
reviewers should inspect accepted backend candidates, rejected backend
candidates, manual override effects, fallback reasons, and assignment reasons
rather than treating the files as generated noise.
