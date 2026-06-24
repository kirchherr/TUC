# RFC 0223: Planner Overhead Portfolio

- Status: accepted-for-prototype
- Created: 2026-06-24
- Phase: Alpha / Delta / Epsilon

## Summary

Add a deterministic Planner Overhead Portfolio report for the accepted Kernel
Ingress research cases.

This RFC does not run benchmarks, publish raw timing samples, execute backend
artifacts, access devices, load dynamic libraries, discover plugins, generate
native artifacts, or claim native performance parity.

## Motivation

RFC 0185 bound current Performance Proof Readiness to a diagnostic
planner-overhead report for the accepted Kernel Ingress MVP pipeline graph.
That was enough to show the phase-separation contract exists, but it kept the
evidence narrow.

TUC now has four accepted Kernel Ingress cases. Planner-overhead evidence
should show that the same phase contract survives across that accepted
portfolio without turning unstable duration values into repository goldens.

## Decision

Add [Planner Overhead Portfolio](../docs/PLANNER_OVERHEAD_PORTFOLIO.md):

- `examples/planner_overhead_portfolio.py`
- `schemas/planner_overhead_portfolio_report.v0.schema.json`
- `tests/golden/proofs/planner_overhead_portfolio_report.json`
- `tests/test_planner_overhead_portfolio.py`

The example reconstructs each accepted Kernel Ingress graph, runs
`measure_pipeline_planner_overhead`, checks the underlying
`tuc.planner_overhead_report.v0` contract, and emits only deterministic
metadata:

- case identity
- operation-family coverage
- backend sequence
- phase contract
- measured compiler-phase count
- explicitly unmeasured phase count
- blocked execution, break-even, and native-performance status

Raw timing values are measured internally for contract validation but omitted
from the published portfolio output.

## Security Boundary

The report is metadata-only. It must not include raw source, raw Source Intent
payloads, raw tensor values, raw timing samples, raw duration fields, host
paths, environment variables, device identifiers, generated code, backend
artifacts, plugin entrypoints, dynamic-library paths, or native benchmark
output.

The schema is fail-closed with `additionalProperties: false` for every object.

## Consequences

- Planner-overhead evidence now spans the accepted Kernel Ingress portfolio
  instead of only the MVP pipeline graph.
- Repository goldens stay deterministic because duration values are omitted.
- Native performance, break-even, cache, and execution-timing claims remain
  blocked under the Performance Proof Boundary.
