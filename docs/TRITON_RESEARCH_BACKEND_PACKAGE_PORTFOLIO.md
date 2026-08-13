# Triton Research Backend Package Portfolio

Triton Research Backend Package Portfolio v0 is TUC's first single live proof
from realistic Triton-like module text to independently described backend
capabilities and heterogeneous trusted execution.

## Research Question

Can bounded source syntax cross the complete Universal Compute interface while
source text, external packages, and backend implementations remain separate
trust domains?

For the fixed research slice, the answer is yes:

```text
Triton-like module source buffer
  -> bounded AST validation and kernel extraction
  -> execution-free research parser
  -> source_intent.v0 plain data
  -> Metadata -> ComputeGraph -> HAC-IR
  -> external-systolic -> external-vector
  -> blocked -> row_major layout conversion
  -> systolic-sim -> vector-sim trusted projection
  -> controlled Runtime Executor
  -> public output y
  -> independent reference correctness
  -> reference-cpu backend equivalence
  -> PASS
```

Run the proof with:

```bash
python examples/triton_research_backend_package_portfolio.py
```

## Accepted Source Slice

The fixed module contains only the approved import aliases, one
`@triton.jit`-decorated function, `tl.dot`, the exact ReLU form
`tl.where(projection > 0, projection, 0)`, and `tl.store`. The
ingress receives a caller-provided shape manifest and validates byte, line,
AST-node, AST-depth, operation, tensor, return, and shape bounds.

Python imports are never performed. The decorator is never evaluated. No
function object, bytecode, JIT artifact, file path, environment value, or
runtime callback is accepted. `ast.parse` treats the source as data and the
extracted function is converted only to schema-versioned Source Intent plain
data, which is then independently re-intaken before compilation.

## External Capability Path

The generated hardware-neutral graph contains `matmul -> elementwise` and no
backend names. Capability planning assigns every operation to the exact
data-only package set:

```text
external-systolic -> external-vector
```

There is no fallback assignment. The package plan is accepted only after exact
package, capability, operation-scope, binding, and trusted-executor digest
checks. Packages cannot contribute code or select executors.

The trusted projection is:

```text
systolic-sim -> vector-sim
```

The intermediate `projection` tensor retains one explicit 32-byte
`blocked -> row_major` conversion.

## Semantic Closure

The Source Intent return maps public output `y` to terminal tensor
`activated`. Runtime Output Contract and Runtime Public Output Bundle resolve
that boundary. The result must pass both an independent NumPy reference and an
all-`reference-cpu` Backend Equivalence comparison.

The parser records `elementwise_kind=relu`, metadata maps it to `kernel=relu`,
and trusted execution applies ReLU. The value-level test and independent
reference include negative matrix-product results, so an identity lowering
cannot pass this semantic closure.

PASS therefore means that the fixed syntax slice preserved its observable
intent across frontend translation, external capability ownership, trusted
heterogeneous placement, and runtime execution.

## Evidence Boundary

The report binds twelve artifacts by SHA-256 digest: Kernel Ingress, Research
Parser, Source Intent, metadata, HAC-IR, both package integration reports,
portfolio execution, output contract, public output bundle, reference
correctness, and backend equivalence.

It serializes no module source, extracted source, Source Intent payload, raw
tensor value, runtime handle, device ID, path, command, generated code, backend
artifact, or plugin entry point. Nested report sections and artifact objects
reject unknown properties.

## Security Properties

- Source size and AST complexity are bounded before semantic parsing.
- Imports and decorators are validated as syntax and never executed.
- Source Intent is reconstructed through the canonical plain-data intake.
- Source-level ReLU semantics are bound through Source Intent, Metadata,
  ComputeGraph, Runtime Executor, and independent reference evidence.
- Backend authority cannot enter Source Intent or HAC-IR.
- The exact two-package set must own every assignment; fallback is forbidden.
- Trusted projection uses maintainer-owned digest bindings and fixed simulators.
- External package code, plugins, native libraries, devices, JIT, subprocesses,
  network access, generated artifacts, and host-path access remain blocked.
- Public evidence is deterministic, digest-only, and raw-value-free.
- Malicious imports, decorators, top-level code, custom value mappings, unknown
  report fields, claim drift, and package-digest drift are negative-tested.

## Artifacts

- Guide: `docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md`
- Entrypoint: `examples/triton_research_backend_package_portfolio.py`
- Schema: `schemas/triton_research_backend_package_portfolio_report.v0.schema.json`
- Golden: `tests/golden/frontend/triton_research_backend_package_portfolio_report.json`
- Decision: `rfcs/0286-triton-research-backend-package-portfolio.md`

## Non-Claims

This is an explicit research path. It does not admit general or production
source ingestion, execute Triton, import the module, evaluate decorators,
compile bytecode, execute external package code, run native kernels, prove
physical device residency, or establish native performance parity.

It proves the narrower thesis that a bounded real-syntax slice can traverse a
hardware-neutral interface into independently declared heterogeneous
capabilities and retain observable semantics without opening those execution
surfaces.
