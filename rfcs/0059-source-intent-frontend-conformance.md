# RFC 0059: Source Intent Frontend Conformance

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds reusable Source Intent frontend conformance fixtures for tools that
emit `source_intent.v0` plain data.

This RFC does not add source parsing, file loading, preflight-to-intent
conversion, Python-object ingestion, frontend module imports, plugin discovery,
backend lowering, generated-artifact execution, or device access.

## Motivation

Source Intent Intake and the JSON Schema give external frontend authors a data
contract. The project also needs a repeatable way to review whether a frontend
emits accepted plain data and rejects known dangerous or invalid shapes before
maintainers consider deeper integration.

The conformance suite turns that into a deterministic report artifact without
making GPU, Triton, Python source, or any specialized hardware the center of
the interface.

## Decision

Add `tuc.frontend.source_intent_conformance` with:

- `SourceIntentFrontendConformanceCase`
- `run_source_intent_frontend_conformance(frontend_name, cases)`
- `assert_source_intent_frontend_conformance(frontend_name, cases)`
- `dump_source_intent_frontend_conformance_report(report)`
- report schema
  `tuc.source_intent_frontend_conformance_report.v0`

Accepted cases must flow through:

1. Source Intent Intake
2. Source Intent Metadata Conversion
3. metadata to `ComputeGraph`
4. neutral compiler planning with explicit backend capability data and the
   `reference-cpu` fallback

Rejected cases must fail closed at Source Intent Intake.

## Security Boundary

The conformance suite accepts in-memory case payloads. It must not load files,
import frontend modules, inspect source text, execute decorators, discover
plugins, touch devices, run subprocesses, or execute generated artifacts.

Diagnostics intentionally report the failed stage and exception type rather
than raw payload contents.

The suite is a certification aid for frontend authors. It is not a production source parser, not a parser-to-IR bridge, and not a backend plugin gate.

## Evidence

The implementation adds:

- `src/tuc/frontend/source_intent_conformance.py`
- `examples/source_intent_frontend_conformance.py`
- `tests/test_source_intent_conformance.py`
- `tests/golden/frontend/source_intent_frontend_conformance_report.json`
- `docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md`

The example report covers one valid plain-data MLP and rejected cases for
source-text escape, backend-specific hint escape, and unknown tensor reference.

## Consequences

- External frontend authors get a standards-oriented review artifact.
- TUC can evaluate frontend proposals without importing or executing their
  code.
- Source Intent remains the hardware-independent data contract before any
  source parser work begins.

## Rejected Alternatives

1. Require frontends to ship executable Python adapters for certification.

   Rejected because certification must not import or execute untrusted frontend code.

2. Treat JSON Schema validation as sufficient certification.

   Rejected because runtime canonicalization, metadata conversion, graph
   validation, and planning evidence also need review.

3. Let frontend conformance load fixture files by path.

   Rejected because production path handling is outside this slice and would
   enlarge the attack surface.
