# Source Intent Frontend Conformance Gate

Source Intent Frontend Conformance Gate v0 is the CI-facing check for external
frontend plain-data evidence.

It composes the reusable Source Intent Frontend Conformance suite and requires
the public-return conformance cases to remain present. It does not read files,
parse source text, import frontend packages, discover plugins, execute
generated artifacts, access devices, or run untrusted backend code.

## Contract

- Gate contract: `source_intent_frontend_conformance_gate.ci.v0`
- Example: `examples/source_intent_frontend_conformance_gate.py`
- Golden:
  `tests/golden/frontend/source_intent_frontend_conformance_gate.txt`
- Tests: `tests/test_source_intent_frontend_conformance_gate.py`
- CI entry: `.github/workflows/ci.yml`

The gate passes only when:

- Source Intent Frontend Conformance passes
- at least one accepted and one rejected conformance case are present
- explicit public-return conformance coverage remains present:
  `valid_source_intent_return_mlp`,
  `reject_return_unknown_tensor`,
  `reject_return_intermediate_tensor`, and
  `reject_duplicate_public_returns`

## Security Boundary

The gate consumes an in-memory `SourceIntentFrontendConformanceReport`. It
checks bounded case names, counts, issues, and required public-return coverage.
It does not serialize raw frontend payloads, source text, paths, plugin
entrypoints, generated code, runtime tensors, device handles, environment
variables, or backend artifacts.

The output is a deterministic text report ending in `PASS`.

## Review Meaning

This gate is a merge-time confidence check for the Source Intent frontend
contract. It is not a production source ingestion path, parser approval, plugin
certification runtime, backend execution gate, or native performance claim.

The Source-to-Intent research parser has its own downstream gate documented in
[Source-To-Intent Research Parser Conformance Gate](SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md).
That gate proves explicit parser output can pass this reusable conformance
path without turning source text into a default compiler input.
