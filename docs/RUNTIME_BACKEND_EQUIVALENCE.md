# Runtime Backend Equivalence

Runtime Backend Equivalence v0 is a schema-versioned, data-only review artifact
for comparing two trusted Runtime Executor placements of the same graph.

It is a practical runtime proof slice: the same compute intent is compiled and
executed twice, once as a neutral baseline placement and once with an explicit
accelerator placement. The report records whether terminal outputs match while
keeping tensor values out of serialized evidence.

## Contract

- Report schema: `schemas/runtime_backend_equivalence_report.v0.schema.json`
- Report schema version: `tuc.runtime_backend_equivalence_report.v0`
- Evidence contract: `runtime_backend_equivalence.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Trusted executor registry: `trusted_runtime_executor_registry.v0`
- Raw value policy: `omitted_by_policy`

## What It Proves

The current evidence fixture executes:

- baseline run: `reference-cpu`, `reference-cpu`
- candidate run: `systolic-sim`, `reference-cpu`

Both runs use the same graph and deterministic inputs. The report checks that:

- the planned backend sequences are distinct
- both runs produce the same terminal output inventory
- output shapes and dtypes match the graph contract
- terminal output values match within bounded tolerance during trusted execution
- serialized evidence omits baseline and candidate tensor values

The deterministic example is:

```bash
python examples/runtime_backend_equivalence.py
```

Its golden evidence is:

```text
tests/golden/runtime_backend_equivalence/current_report.json
```

## Security Boundary

Runtime Backend Equivalence is metadata only. It does not include tensor values,
tensor-value digests, runtime handles, host paths, device identifiers, generated
code, plugin entrypoints, commands, environment variables, benchmark samples, or
backend artifacts.

The comparison may inspect runtime arrays inside the trusted in-process Runtime
Executor boundary, but only shape, dtype, tolerance, status, backend sequence,
and metadata digests are serialized.

## Current Limitations

- The report compares trusted in-process prototype executor runs only.
- The report is correctness/equivalence evidence, not a native performance
  claim.
- The current fixture compares `reference-cpu` with `systolic-sim` placement.
- Future backend classes should add similar equivalence fixtures before any
  stronger performance or portability claims are made.
