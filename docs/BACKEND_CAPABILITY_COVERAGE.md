# Backend Capability Coverage

Backend Capability Coverage v0 is a pure-data matrix that shows which backend
capability descriptions cover TUC's current neutral operation families.

It is deliberately earlier than backend conformance:

```text
capability data -> coverage matrix -> registry diagnostics -> conformance
```

The matrix answers three reviewer questions:

1. Which neutral operation families are covered by current capability data?
2. Which backend names accept or prefer each operation family?
3. Do any required operation families still lack a declared capability path?

## Artifact

The current executable example is:

```text
examples/backend_capability_coverage.py
```

The deterministic golden is:

```text
tests/golden/backend_capability_coverage/current_report.json
```

The schema is:

```text
schemas/backend_capability_coverage_report.v0.schema.json
```

## Security Boundary

Coverage uses `BackendCapability` data only. It does not:

- import backend plugins
- instantiate third-party backend code
- call backend lowering methods
- spawn subprocesses
- load dynamic libraries
- touch devices
- execute generated artifacts
- read benchmark outputs

The report includes the Runtime Executor blocked execution surfaces so reviewers
can see that capability coverage is not an execution permission.

## Relationship To Conformance

Coverage and conformance are different gates.

Coverage proves that current capability data declares at least one path for a
neutral operation family. Conformance proves that a trusted in-process backend
object behaves consistently with its declared capability.

Missing coverage is a capability-model issue. Failed conformance is a trusted
backend implementation issue.

## Current Matrix Meaning

The current matrix covers:

- `matmul`
- `elementwise`
- `reduction`
- `softmax`

through the current simulator capabilities:

- `linear-sim`
- `systolic-sim`
- `vector-sim`

This is not a native performance claim. It is evidence that the project can
describe multiple backend families through data while keeping HAC-IR neutral.
