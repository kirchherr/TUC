# Backend Conformance Fixtures

Backend conformance fixtures are reusable tests for trusted in-process prototype
backends. They complement the negative-test template by checking that a backend
behaves consistently with its declared capability data.

## What They Prove

The current fixtures check:

- MVP operation fixtures can be constructed for `matmul`, `elementwise`,
  `reduction`, and `softmax`.
- Operations accepted by `capability.supports(operation)` can be lowered.
- Operations rejected by `capability.supports(operation)` are not lowered.
- `LoweringResult.backend_name` matches the capability name.
- `LoweringResult.graph_name` matches the input graph.
- Artifacts are non-empty and bounded.
- Prototype textual artifacts mention the operation kind and operation name.
- Diagnostics are bounded tuples of non-empty strings.

These checks do not execute backend artifacts and do not prove real hardware
correctness. They establish a small, deterministic backend-authoring baseline.

## Running The Fixtures

Use the helper:

```python
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.conformance import assert_backend_conformance


def test_backend_conformance() -> None:
    assert_backend_conformance(LinearAlgebraSimulatorBackend())
```

Or inspect the report directly:

```python
from tuc.backends.conformance import run_backend_conformance

report = run_backend_conformance(backend)
assert report.passed, report.issues
```

The reference tests live in:

```text
tests/test_backend_conformance.py
```

An external-style backend author path also lives in:

```text
examples/external_backend_author_path.py
tests/test_external_backend_author_path.py
```

It loads a schema-versioned capability manifest through the explicit registry,
compiles a graph using only that capability data, runs the reusable conformance
fixtures, and lowers only the compiler-assigned HAC-IR subgraph with a trusted
in-process prototype backend.

## Fixture Scope

The fixture graphs are intentionally tiny:

| Operation | Fixture shape |
| --- | --- |
| `matmul` | `(4, 8) x (8, 3) -> (4, 3)` |
| `elementwise` | `(4, 3) -> (4, 3)` |
| `reduction` | `(4, 3) -> (4,)` |
| `softmax` | `(4, 3) -> (4, 3)` |

Fixtures are generated for row-major layout and for layouts declared by the
backend capability. This catches layout support drift without creating a large
cartesian product.

## Security Rules

Backend conformance does not:

- Discover backend plugins.
- Import backend modules.
- Spawn subprocesses.
- Load dynamic libraries.
- Touch devices.
- Read manifests or files.
- Execute generated artifacts.

The only backend method called by the fixtures is `lower(graph)` on a trusted
object that the test constructed directly.

The external author path follows the same rule: manifest and registry steps are
pure data; backend lowering starts only after the test explicitly constructs
the trusted backend object.

## Relation To Certification

Backend authors should provide both:

- Negative tests from `tests/test_backend_author_negative_template.py`.
- Positive and rejection conformance tests through `assert_backend_conformance`.

The negative template protects the input boundary. The conformance fixtures
check that declared capability data and lower-time behavior agree.

## Current Limitations

Backend conformance v0.1 does not yet check:

- Numeric output correctness.
- Hardware execution.
- Artifact binary format.
- Calibration behavior.
- Noise-model quality.
- Performance claims.

Those require backend-specific conformance suites and eventually artifact
sandboxing before generated output can execute.
