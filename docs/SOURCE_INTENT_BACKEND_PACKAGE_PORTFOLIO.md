# Source Intent Backend Package Portfolio

Source Intent Backend Package Portfolio v0 is TUC's first single proof that
joins the neutral frontend boundary to an independently described,
heterogeneous backend portfolio and controlled runtime execution.

## Research Question

Can one hardware-neutral compute-intent payload reach two externally described
capability domains without fallback, preserve an explicit layout boundary, and
produce the same observable result as an independent reference execution?

For the bounded v0 slice, the answer is yes:

```text
Source Intent plain data
  -> Metadata
  -> ComputeGraph / HAC-IR
  -> external-systolic -> external-vector
  -> blocked -> row_major layout conversion
  -> systolic-sim -> vector-sim trusted projection
  -> controlled execution
  -> public output contract
  -> independent NumPy reference correctness
  -> reference-cpu backend equivalence
  -> PASS
```

Run the proof with:

```bash
python examples/source_intent_backend_package_portfolio.py
```

## Accepted Slice

The Source Intent payload is already decoded plain data under
`source_intent.v0`. It declares two `float64` matrix inputs, a `matmul`, an
identity `elementwise` operation, and one explicit public return. It contains no
backend, device, memory-domain, layout, command, path, module, callable, or
source-text authority.

The graph is compiled against two separately loaded data-only packages:

- `external-systolic-reference-package` owns `matmul`;
- `external-vector-reference-package` owns `elementwise`.

Every source-plan assignment must belong to this exact admitted package set.
`reference-cpu`, unknown backends, runtime overrides, candidate-score payloads,
and noncanonical placement metadata are rejected.

## Trusted Projection

External packages describe capabilities and conformance cases. They do not
provide executors. Maintainer-owned digest bindings project the accepted source
plan to fixed in-repository simulators:

```text
external-systolic -> systolic-sim
external-vector   -> vector-sim
```

The intermediate `projection` tensor is produced as `blocked` and consumed as
`row_major`. The compiler's 32-byte layout conversion remains present in the
trusted projected plan and the portfolio evidence.

## Correctness Closure

The projected plan is executed by the fixed Runtime Executor registry. TUC
then requires both:

- Runtime Reference Correctness against an independent NumPy `matmul` result;
- Runtime Backend Equivalence against an all-`reference-cpu` execution.

The Source Intent public alias `api_activated` is resolved through Runtime
Output Contract and Runtime Public Output Bundle. A report cannot claim PASS
unless package admission, no-fallback planning, execution, public-output
closure, reference correctness, and backend equivalence all succeed.

## Public Evidence

The public report contains ten digest-bound artifacts: Source Intent IR,
Source Intent metadata, HAC-IR, both package integration reports, package
portfolio execution, output contract, public output bundle, reference
correctness, and backend equivalence.

The report never serializes Source Intent payload bodies, source text, raw
tensor values, runtime handles, device IDs, host paths, commands, generated
code, backend artifacts, or plugin entry points. Its JSON schema fixes the
package IDs and digests, backend sequences, blocked claims, false execution
flags, and exact artifact order, and rejects unknown object properties.

## Security Properties

- Source Intent intake is plain-data-only and rejects backend authority.
- No source parsing, Python execution, imports, plugin discovery, or callbacks.
- No package implementation, JIT, native library, generated artifact, or device
  execution.
- Exact package and capability digests bind admission.
- Every source assignment is package-owned; fallback count is exactly zero.
- Canonical plan reconstruction rejects forged placement and movement data.
- Trusted executors come only from the fixed maintainer-owned registry.
- Deterministic finite inputs and bounded tensor shapes are used.
- Public evidence is digest-only and fail-closed.

## Artifacts

- Guide: `docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md`
- Entrypoint: `examples/source_intent_backend_package_portfolio.py`
- Schema: `schemas/source_intent_backend_package_portfolio_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_intent_backend_package_portfolio_report.json`
- Decision: `rfcs/0285-source-intent-backend-package-portfolio.md`

## Non-Claims

This proof does not ingest or execute source text, implement a general parser,
execute external package code, run native kernels, prove physical device
residency, or establish native performance parity. It proves a narrower
research result: one neutral intent description can cross separately owned
capability domains and preserve observable semantics without changing HAC-IR.
