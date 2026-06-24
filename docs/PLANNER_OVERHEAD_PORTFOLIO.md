# Planner Overhead Portfolio

Planner Overhead Portfolio is deterministic, metadata-only evidence that the
diagnostic planner-overhead contract runs across every accepted Kernel Ingress
research case.

It does not publish raw timing samples, raw duration values, raw source, raw
tensor values, execution timings, device data, generated code, benchmark
artifacts, or native performance claims.

## Contract

- Report schema: `schemas/planner_overhead_portfolio_report.v0.schema.json`
- Report schema version: `tuc.planner_overhead_portfolio_report.v0`
- Documentation: `docs/PLANNER_OVERHEAD_PORTFOLIO.md`
- Portfolio contract: `planner_overhead_portfolio.kernel_ingress.v0`
- Underlying report contract: `tuc.planner_overhead_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Execution time status: `not_measured`
- Break-even status: `not_established`
- Example: `examples/planner_overhead_portfolio.py`
- Golden: `tests/golden/proofs/planner_overhead_portfolio_report.json`
- Tests: `tests/test_planner_overhead_portfolio.py`

## Evidence Scope

The report covers the four accepted Kernel Ingress cases:

- `research_module_matmul_elementwise`
- `research_module_softmax_reduction`
- `research_module_matmul_reduction`
- `research_module_mvp_pipeline`

For each case, the portfolio reconstructs the bounded Kernel Ingress graph,
runs `measure_pipeline_planner_overhead`, verifies the underlying planner
report contract, records the backend sequence and phase contract, and omits
the non-deterministic planner duration values from the published evidence.

The published report records only:

- case identity
- source-free operation-family coverage
- backend sequence
- measured compiler-phase count
- explicitly unmeasured phase count
- phase contract
- blocked execution and break-even status

## Security Boundary

The report must remain source-free and value-free. It must not contain:

- raw Triton source
- raw Source Intent payloads
- raw tensor values
- raw timing samples
- `duration_ns` values
- host paths or environment variables
- device identifiers
- backend artifacts or generated code

The schema is fail-closed with `additionalProperties: false` on every object.

## Still Blocked

This portfolio does not prove native performance parity, break-even workload
size, execution timing, planner benefit, cache behavior, or benchmark
interpretation. It strengthens the planner-overhead evidence surface by moving
from a single accepted graph to the full accepted Kernel Ingress portfolio.
