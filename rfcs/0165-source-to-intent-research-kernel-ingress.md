# RFC 0165: Source-To-Intent Research Kernel Ingress

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Runtime Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md`
  - `examples/source_to_intent_research_kernel_ingress.py`
  - `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
  - `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
  - `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress.py`

## Context

TUC's current Source-To-Intent Research Parser proves a narrow source-buffer to
`source_intent.v0` path and the Source Runtime Smoke proves that accepted source
buffers can reach controlled runtime execution.

That is useful, but still shaped more like embedded function snippets than real
Triton developer input. A realistic Triton kernel usually appears inside a
Python module with import statements and one or more decorated functions.

The next credible research step is not general Triton ingestion. It is a
bounded module-shaped ingress that validates an import prelude as data, extracts
one explicitly named `@triton.jit` function, and then reuses the already gated
Preflight, Research Parser, Source Intent Intake, metadata conversion, runtime
planning, and reference-correctness path.

## Decision

Add Source-To-Intent Research Kernel Ingress v0.

The v0 ingress accepts exactly:

- `import triton`
- `import triton.language as tl`
- one explicitly selected top-level kernel function

It rejects import execution, import-from syntax, top-level assignments, multiple
functions, target-kernel mismatches, unsupported imports, and all downstream
parser rejections.

The ingress emits metadata-only evidence:

- module source digest
- extracted kernel digest
- parser report digest
- Source Intent digest
- operation-family summary
- runtime evidence digests
- backend sequence
- terminal output metadata

It does not serialize raw module source, raw extracted function source, raw
Source Intent payloads, tensors, generated code, backend artifacts, host paths,
environment variables, or benchmark output.

## Consequences

This strengthens the roadmap item "First real Triton kernel ingestion path"
without opening general source parser intake.

Default source-to-intent parser intake remains blocked. The accepted research
parser remains explicit-only. The module ingress is a research proof artifact,
not a production parser.

Future expansion must add:

- source-free accepted/rejected diagnostics
- conformance evidence
- idiom alignment
- runtime correctness evidence
- digest binding in the Research Evidence Gate and Proof Bundle
- security review for every new module syntax surface

## Security Notes

The module is parsed as bounded AST data only.

The ingress must not:

- import Python modules
- evaluate decorators
- inspect live Python function objects
- run Triton JIT
- read files
- access devices
- execute subprocesses
- discover plugins
- emit compiler artifacts directly

All compiler artifacts must continue to originate from validated
`source_intent.v0` plain data after explicit Source Intent Intake.
