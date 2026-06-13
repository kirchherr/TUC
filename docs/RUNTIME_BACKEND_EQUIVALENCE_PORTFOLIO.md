# Runtime Backend Equivalence Portfolio

Runtime Backend Equivalence Portfolio v0 is a schema-versioned, data-only
review artifact that aggregates multiple Runtime Backend Equivalence reports
into one backend-diversity evidence surface.

It exists because The Universal Compute claim is not just "one accelerator can
match `reference-cpu` once." The stronger early proof is that multiple trusted
backend families can be evaluated through the same hardware-independent compute
intent boundary without changing mathematical intent.

## Contract

- Report schema:
  `schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json`
- Policy schema:
  `schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json`
- Report schema version:
  `tuc.runtime_backend_equivalence_portfolio_report.v0`
- Policy schema version:
  `tuc.runtime_backend_equivalence_portfolio_policy_report.v0`
- Evidence contract:
  `runtime_backend_equivalence_portfolio.data_only.v0`
- Policy contract:
  `runtime_backend_equivalence_portfolio_policy.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Trusted executor registry: `trusted_runtime_executor_registry.v0`
- Raw value policy: `omitted_by_policy`

## Current Portfolio

The current deterministic portfolio aggregates:

- `runtime_backend_equivalence`: `reference-cpu` versus `systolic-sim`
- `runtime_vector_backend_equivalence`: `reference-cpu` versus `vector-sim`
- `runtime_mixed_backend_equivalence`: `reference-cpu` versus mixed
  `systolic-sim` and `vector-sim`

The portfolio records each slice's graph name, run IDs, backend sequences,
comparison count, comparison metadata digest, pass status, and raw-value
policy. It also records the non-reference candidate backend families currently
covered by the portfolio.

Run it with:

```bash
python examples/runtime_backend_equivalence_portfolio.py
python examples/runtime_backend_equivalence_portfolio_policy.py
```

Golden evidence:

```text
tests/golden/runtime_backend_equivalence/portfolio_report.json
tests/golden/runtime_backend_equivalence/portfolio_policy_report.json
```

## Gate Binding

Runtime Evidence Gate builds the portfolio from the same three Backend
Equivalence reports it checks individually. The gate then verifies:

- Runtime Evidence Matrix contains `runtime_backend_equivalence_portfolio`
  with scoped `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` coverage
- portfolio ID is `runtime_backend_equivalence_portfolio`
- policy ID is `runtime_backend_equivalence_portfolio_policy`
- slice count matches the expected three reports
- slice IDs and graph names match the checked reports
- baseline and candidate run IDs match the checked reports
- baseline and candidate backend sequences match the checked reports
- comparison counts and comparison metadata digests match the checked reports
- candidate backend families are `systolic-sim` and `vector-sim`
- raw tensor values remain omitted by policy
- the policy's accepted slice membership and backend sequences match the
  portfolio slices

This prevents a stale or unrelated aggregate report from counting as proof.

## Security Boundary

The portfolio is metadata only. It does not include tensor values,
tensor-value digests, runtime handles, host paths, device identifiers,
generated code, plugin entrypoints, commands, environment variables, benchmark
samples, backend artifacts, or raw execution output.

It does not execute reports, resolve artifact IDs to paths, discover backends,
load plugins, access devices, spawn subprocesses, touch the network, run JIT
code, load dynamic libraries, or authorize native execution.

## Current Limitations

- The portfolio aggregates trusted prototype executor evidence only.
- It is correctness and diversity evidence, not a native performance claim.
- It currently covers two non-reference simulator families:
  `systolic-sim` and `vector-sim`.
- New backend classes should add their own equivalence slices and then be bound
  into this portfolio before stronger portability claims are made.
