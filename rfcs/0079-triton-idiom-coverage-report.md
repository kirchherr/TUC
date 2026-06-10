# RFC 0079: Triton Idiom Coverage Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Epsilon

## Summary

Add a bounded diagnostic report for Triton-like idiom coverage through the
existing execution-free metadata path.

## Motivation

TUC's roadmap moves toward real Triton integration, but the safe path remains:

```text
schema-versioned metadata -> ComputeGraph -> HAC-IR -> runtime plan
```

Direct Triton source ingestion is still blocked by the source threat model and
parser gate. We need a way to expand Triton credibility without turning source
text, decorators, Python objects, or JIT code into compiler inputs.

## Decision

Add:

- `TritonIdiomCoverage`
- `TritonIdiomCoverageReport`
- `build_triton_idiom_coverage_report(proposal_name, coverages)`
- `dump_triton_idiom_coverage_report(report)`
- `triton_idiom_coverage_report_to_dict(report)`
- report schema version `tuc.triton_idiom_coverage_report.v0`
- schema file `schemas/triton_idiom_coverage_report.v0.schema.json`
- example `examples/triton_idiom_coverage_report.py`
- golden `tests/golden/frontend/triton_idiom_coverage_report.json`
- documentation `docs/TRITON_IDIOM_COVERAGE_REPORT.md`

The report records bounded identifiers for:

- covered idiom
- MVP operation family
- metadata example
- intake golden
- HAC-IR golden
- runtime-plan golden
- compiler-decision golden
- coverage status

## Security Model

The report is data-only. It must not include:

- source text
- Python source
- host paths
- command lines
- environment variables
- device identifiers
- plugin entrypoints
- generated code
- backend artifacts
- raw benchmark output
- raw compiler artifacts

`direct_triton_source_ingestion` is always `false`.

`parser_status` is always `direct_triton_source_ingestion_blocked`.

The report does not parse source, import Triton, inspect Python functions,
evaluate decorators, execute `@triton.jit`, discover plugins, access devices,
or run generated artifacts.

## Consequences

- Future Triton idiom coverage has a machine-readable review artifact.
- Metadata-based coverage can grow without weakening Source Intent or parser
  gates.
- The real Triton integration milestone remains credible but still safe.
- Source parser work remains blocked until the parser gate and readiness report
  are satisfied.

## Alternatives Considered

1. Extend `TritonIntakeReport` directly.

   Rejected because intake reports describe one metadata payload. Idiom coverage
   needs a separate review surface across examples and goldens.

2. Add direct Triton source parsing.

   Rejected. The threat model and parser gate intentionally keep source text
   disconnected from compiler artifacts.

3. Track coverage only in prose.

   Rejected. The roadmap needs machine-readable evidence that can be tested.

## References

- [Triton Idiom Coverage Report](../docs/TRITON_IDIOM_COVERAGE_REPORT.md)
- [Triton Source Threat Model](../docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Frontend Adapter](../docs/FRONTEND_ADAPTER.md)
- `schemas/triton_idiom_coverage_report.v0.schema.json`
- `tests/golden/frontend/triton_idiom_coverage_report.json`
