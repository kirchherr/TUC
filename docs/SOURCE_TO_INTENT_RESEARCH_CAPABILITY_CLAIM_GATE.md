# Source-To-Intent Research Capability Claim Gate

Source-To-Intent Research Capability Claim Gate v0 is the CI-facing gate for
the current bounded Universal Compute research claim.

It validates the digest-only capability claim report and renders a source-free
text gate that can be checked in CI and reviewed in pull requests.

## Contract

- Gate contract:
  `source_to_intent_research_capability_claim_gate.ci.v0`
- Example:
  `examples/source_to_intent_research_capability_claim_gate.py`
- Claim report input:
  `examples/source_to_intent_research_capability_claim.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt`
- Tests:
  `tests/test_source_to_intent_research_capability_claim_gate.py`
- CI entry: `.github/workflows/ci.yml`

## What It Gates

The gate passes only when the capability claim report:

- matches the exact v0 report contract;
- still supports only `bounded_universal_compute_research_slice`;
- still scopes the claim to
  `accepted_source_to_intent_kernel_ingress_mvp_pipeline`;
- still records `mvp_pipeline` as the combined pipeline kernel;
- still records `matmul->softmax->reduction->elementwise`;
- still records four accepted runtime cases;
- still records trusted runtime backends `linear-sim` and `vector-sim`;
- still records seven bound evidence artifacts;
- still blocks production parser, native performance, hardware certification,
  arbitrary backend execution, general Triton ingestion, and vendor compiler
  replacement claims.

The gate compares the supplied claim report digest against the freshly built
current claim report. A valid-looking report with changed evidence digests
fails closed.

## Security Boundary

The gate consumes only an already-rendered JSON claim report. It does not parse
source text, import Triton modules, execute source, run backends, access
devices, discover plugins, emit artifacts, or read host paths.

The gate output is source-free and contains only stable identifiers, counts,
claim boundaries, blocked claim names, and one SHA-256 digest.

## Review Meaning

This is the merge-facing control above the research claim:

```text
capability claim report
    ->
capability claim gate
```

Future work that expands the supported claim must update the underlying
evidence first, then update the claim report, this gate, tests, docs, and RFCs
together.
