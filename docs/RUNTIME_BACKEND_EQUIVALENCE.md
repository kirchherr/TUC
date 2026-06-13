# Runtime Backend Equivalence

Runtime Backend Equivalence v0 is a schema-versioned, data-only review artifact
for comparing two trusted Runtime Executor placements of the same graph.

It is a practical runtime proof slice: the same compute intent is compiled and
executed twice, once as a neutral baseline placement and once with an explicit
accelerator placement. The report records whether terminal outputs match while
keeping tensor values out of serialized evidence.

## Contract

- Report schema: `schemas/runtime_backend_equivalence_report.v0.schema.json`
- Portfolio schema:
  `schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json`
- Report schema version: `tuc.runtime_backend_equivalence_report.v0`
- Evidence contract: `runtime_backend_equivalence.data_only.v0`
- Portfolio contract: `runtime_backend_equivalence_portfolio.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Trusted executor registry: `trusted_runtime_executor_registry.v0`
- Raw value policy: `omitted_by_policy`

## What It Proves

The current evidence fixtures execute:

- baseline run: `reference-cpu`, `reference-cpu`
- candidate run: `systolic-sim`, `reference-cpu`
- baseline run: `reference-cpu`, `reference-cpu`, `reference-cpu`
- candidate run: `vector-sim`, `vector-sim`, `vector-sim`
- baseline run: `reference-cpu`, `reference-cpu`, `reference-cpu`,
  `reference-cpu`
- candidate run: `systolic-sim`, `vector-sim`, `vector-sim`, `vector-sim`

Each pair uses the same graph and deterministic inputs. The report checks that:

- the planned backend sequences are distinct
- both runs produce the same terminal output inventory
- output shapes and dtypes match the graph contract
- terminal output values match within bounded tolerance during trusted execution
- serialized evidence omits baseline and candidate tensor values

The deterministic example is:

```bash
python examples/runtime_backend_equivalence.py
python examples/runtime_vector_backend_equivalence.py
python examples/runtime_mixed_backend_equivalence.py
python examples/runtime_backend_equivalence_portfolio.py
```

Their golden evidence is:

```text
tests/golden/runtime_backend_equivalence/current_report.json
tests/golden/runtime_backend_equivalence/vector_sim_report.json
tests/golden/runtime_backend_equivalence/mixed_accelerators.json
tests/golden/runtime_backend_equivalence/portfolio_report.json
```

The CI-facing Runtime Evidence Gate requires all equivalence fixtures. It
binds the primary fixture to the expected `reference_cpu` baseline and
`systolic_sim` candidate placement, binds the vector fixture to the expected
`reference_cpu` baseline and `vector_sim` candidate placement, and binds the
mixed fixture to the expected `reference_cpu` baseline and `mixed_accelerators`
candidate placement.

Runtime Backend Equivalence Portfolio v0 aggregates those three fixtures into
one backend-diversity review artifact. The portfolio records each slice's graph,
run IDs, baseline and candidate backend sequences, comparison count, comparison
metadata digest, pass status, and raw-value policy. The Runtime Evidence Gate
binds the portfolio back to the exact three reports it has already checked.

## Security Boundary

Runtime Backend Equivalence is metadata only. It does not include tensor values,
tensor-value digests, runtime handles, host paths, device identifiers, generated
code, plugin entrypoints, commands, environment variables, benchmark samples, or
backend artifacts.

The comparison may inspect runtime arrays inside the trusted in-process Runtime
Executor boundary, but only shape, dtype, tolerance, status, backend sequence,
and metadata digests are serialized.

The portfolio is also metadata only. It does not execute reports, resolve
artifact IDs, discover backends, load plugins, access devices, or serialize raw
values. It aggregates already-produced report metadata under bounded schemas.

## Current Limitations

- The report compares trusted in-process prototype executor runs only.
- The report is correctness/equivalence evidence, not a native performance
  claim.
- The current fixtures compare `reference-cpu` with `systolic-sim` placement
  `reference-cpu` with `vector-sim` placement, and `reference-cpu` with mixed
  `systolic-sim` plus `vector-sim` placement.
- Future backend classes should add similar equivalence fixtures before any
  stronger performance or portability claims are made.
