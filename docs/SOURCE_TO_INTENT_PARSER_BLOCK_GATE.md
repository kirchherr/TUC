# Source-To-Intent Parser Block Gate

Source-To-Intent Parser Block Gate v0 is the CI-facing check that the default
source-to-intent parser state remains intentionally blocked.

It does not parse source text, inspect preflight reports, load source files,
import frontend modules, discover plugins, produce `source_intent.v0` payloads,
construct `ComputeGraph`, lower IR, plan runtime placement, or execute backend
artifacts.

## Contract

- Gate contract: `source_to_intent_parser_block_gate.ci.v0`
- Parser gate contract: `source_to_intent_parser_gate.blocking.v0`
- Example: `examples/source_to_intent_parser_block_gate.py`
- Golden: `tests/golden/frontend/source_to_intent_parser_block_gate.txt`
- Tests: `tests/test_source_to_intent_parser_block_gate.py`
- CI entry: `.github/workflows/ci.yml`

The gate passes only when the default Source-To-Intent Readiness report remains
blocked and every required evidence ID is missing, including
`source_intent_frontend_conformance_gate`.

## Security Boundary

The gate consumes bounded in-memory readiness metadata. It checks evidence IDs,
boolean readiness flags, blocked execution-surface labels, and issue IDs. It
does not serialize raw source text, raw frontend payloads, paths, environment
variables, plugin entrypoints, generated code, runtime tensors, device handles,
backend artifacts, or cache locations.

## Review Meaning

This gate is a merge-time assertion that TUC has not accidentally opened a
source-to-intent parser path. If parser work intentionally begins, this gate
must be revised through a dedicated RFC and new evidence rather than silently
allowing source text to influence compiler artifacts.
