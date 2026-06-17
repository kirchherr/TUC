# Source-To-Intent Research Kernel Ingress Idiom Alignment

Source-To-Intent Research Kernel Ingress Idiom Alignment v0 proves that the
accepted Triton-module-shaped Kernel Ingress outputs remain inside the already
covered Triton MVP idiom scope.

It does not add new syntax, does not authorize general Triton source
ingestion, and does not weaken the default parser block.

## Contract

- Alignment contract:
  `source_to_intent_research_kernel_ingress_idiom_alignment.scope.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_idiom_alignment_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_idiom_alignment.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_idiom_alignment.py`
- Evidence Gate binding: `examples/source_to_intent_research_evidence_gate.py`
- Proof Bundle binding: `examples/source_to_intent_research_proof_bundle.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## What It Binds

The report binds:

- Triton Idiom Coverage
- Source-To-Intent Research Kernel Ingress
- Source-To-Intent Research Kernel Ingress Conformance Gate

The accepted Kernel Ingress cases must map to these covered MVP operation
families:

- `elementwise`
- `matmul`
- `reduction`
- `softmax`

Each case records only operation-family and idiom identifiers. Raw module
source, extracted kernel source, Source Intent payloads, tensor values,
compiler artifacts, runtime plans, backend binaries, generated code, benchmark
output, and device identifiers are omitted.

## Security Boundary

This artifact consumes previously rendered metadata-only reports. It does not
parse source text, import Triton modules, evaluate decorators, execute
`@triton.jit`, access devices, load plugins, generate code, or lower source
text directly to compiler artifacts.

The report keeps these claims blocked:

- `general_triton_source_ingestion`
- `native_performance_claim`
- `production_parser`

## Review Meaning

This is a targeted answer to parser-scope drift. It proves that the accepted
module-shaped ingress cases are not arbitrary new frontend power: their
operation families are still the same covered MVP idioms that the earlier
research parser slice already bound.

Future Kernel Ingress syntax can only count as accepted research scope after
this alignment report, its schema, its golden, the Evidence Gate, and the Proof
Bundle are updated together.
