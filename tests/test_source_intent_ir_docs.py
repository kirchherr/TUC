from __future__ import annotations

from pathlib import Path


def test_source_intent_doc_preserves_non_lowering_boundary() -> None:
    text = Path("docs/SOURCE_INTENT_IR.md").read_text(encoding="utf-8")

    for expected in (
        "not a Triton source parser",
        "not a metadata adapter",
        "not a `ComputeGraph` constructor",
        "produce metadata",
        "produce a `ComputeGraph`",
        "produce TLIR, HAC-IR, or HS-IR",
        "execute `@triton.jit`",
        "no `to_compute_graph` or `to_metadata`",
        "The preflight must not create Source Intent IR",
    ):
        assert expected in text


def test_source_intent_rfc_preserves_conversion_gate() -> None:
    text = Path("rfcs/0053-canonical-source-intent-ir.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "no `to_metadata`",
        "no `to_compute_graph`",
        "no lowering path",
        "hardware family names",
        "reserved `tuc.*` keys",
        "metadata remains the accepted bridge",
        "Future conversion from Source Intent IR to metadata requires its own RFC",
    ):
        assert expected in text


def test_triton_docs_reference_source_intent_without_ingestion() -> None:
    compatibility = Path("docs/TRITON_COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    threat_model = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(
        encoding="utf-8"
    )
    preflight = Path("docs/TRITON_SOURCE_PREFLIGHT.md").read_text(encoding="utf-8")

    assert "Canonical Source Intent IR | L1" in compatibility
    assert "Source Intent Metadata Conversion | L2" in compatibility
    assert "not source text" in compatibility
    assert "RFC 0054 permits only execution-free conversion" in threat_model
    assert "Source text and preflight reports must remain disconnected" in threat_model
    assert "The preflight must not create it" in preflight


def test_source_intent_metadata_doc_preserves_adapter_boundary() -> None:
    text = Path("docs/SOURCE_INTENT_METADATA.md").read_text(encoding="utf-8")

    for expected in (
        "execution-free bridge",
        "already constructed `SourceIntentModule`",
        "does not parse source text",
        "must not produce `ComputeGraph`, TLIR, HAC-IR, HS-IR",
        "source_intent_to_metadata.execution_free.v0",
        "tests/golden/frontend/source_intent_metadata_report.txt",
        "source text to Source Intent IR",
    ):
        assert expected in text


def test_source_intent_intake_doc_preserves_plain_data_boundary() -> None:
    text = Path("docs/SOURCE_INTENT_INTAKE.md").read_text(encoding="utf-8")

    for expected in (
        "schema-versioned plain-data entrypoint",
        "does not read files",
        "parse source text",
        "source_intent_intake.execution_free.v0",
        "source_intent_from_mapping(data)",
        "schemas/source_intent.v0.schema.json",
        "Seed corpus: `tests/corpus/source_intent_intake/`",
        "Property tests: `tests/test_source_intent_intake_fuzz.py`",
        "arbitrary JSON-like values",
        "backend-specific hint escape attempts",
        "must not accept source text or preflight reports",
        "tests/golden/frontend/source_intent_intake_report.txt",
        "tests/golden/hac_ir/source_intent_intake_mlp.txt",
        "tests/golden/runtime_plans/source_intent_intake_mlp.txt",
        "tests/golden/compiler_decisions/source_intent_intake_mlp.txt",
        "source text to Source Intent data",
    ):
        assert expected in text


def test_source_intent_schema_doc_preserves_runtime_boundary() -> None:
    text = Path("docs/SOURCE_INTENT_SCHEMA.md").read_text(encoding="utf-8")

    for expected in (
        "schemas/source_intent.v0.schema.json",
        "JSON Schema draft: 2020-12",
        "source_intent_from_mapping(data)",
        "additionalProperties: false",
        "trusted runtime boundary remains",
        "source parsing",
        "ComputeGraph",
        "Incompatible schema changes require a new schema version",
    ):
        assert expected in text


def test_source_intent_schema_rfc_preserves_non_runtime_boundary() -> None:
    text = Path("rfcs/0058-source-intent-json-schema.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "schemas/source_intent.v0.schema.json",
        "does not add source parsing",
        "JSON Schema draft 2020-12",
        "additionalProperties: false",
        "trusted runtime boundary remains `source_intent_from_mapping(data)`",
        "prefer_analog_linear",
        "python_source",
        "Runtime validation remains fail-closed",
    ):
        assert expected in text


def test_source_intent_frontend_conformance_doc_preserves_non_parser_gate() -> None:
    text = Path("docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "reusable certification path",
        "does not read files",
        "parse source text",
        "discover plugins",
        "execute generated artifacts",
        "It is not a source parser",
        "run_source_intent_frontend_conformance(frontend_name, cases)",
        "dump_source_intent_frontend_conformance_report(report)",
        "tests/golden/frontend/source_intent_frontend_conformance_report.json",
        "failure stages and exception types, not raw payload contents",
        "must not become a production source ingestion path",
    ):
        assert expected in text


def test_source_intent_frontend_conformance_rfc_preserves_security_gate() -> None:
    text = Path("rfcs/0059-source-intent-frontend-conformance.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "frontend module imports",
        "plugin discovery",
        "generated-artifact execution",
        "run_source_intent_frontend_conformance(frontend_name, cases)",
        "Rejected cases must fail closed at Source Intent Intake",
        "not a production source parser",
        "not a parser-to-IR bridge",
        "tests/golden/frontend/source_intent_frontend_conformance_report.json",
        "certification must not import or execute untrusted frontend code",
    ):
        assert expected in text


def test_source_intent_intake_rfc_preserves_source_block() -> None:
    text = Path("rfcs/0055-source-intent-intake.md").read_text(encoding="utf-8")

    for expected in (
        "does not add source parsing",
        "source_intent_intake.execution_free.v0",
        "accepts only plain `dict`, `list`, and `tuple` data",
        "parse source text",
        "consume preflight reports",
        "produce metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR",
        "source parsing remains blocked",
    ):
        assert expected in text


def test_source_intent_intake_fuzz_rfc_preserves_non_ingestion_gate() -> None:
    text = Path("rfcs/0056-source-intent-intake-fuzz-corpus.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "arbitrary JSON-like values",
        "source-text escape attempts",
        "backend-specific hint escape attempts",
        "unknown tensor references",
        "Source text and preflight reports remain disconnected",
        "production API must remain path-free",
    ):
        assert expected in text


def test_source_intent_intake_e2e_rfc_preserves_parser_block() -> None:
    text = Path("rfcs/0057-source-intent-intake-e2e-goldens.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "plain data",
        "SourceIntentModule",
        "HAC-IR",
        "runtime plan",
        "compiler decision report",
        "Source text, preflight reports, and parser outputs remain blocked",
        "Source Intent Intake must not produce compiler artifacts directly",
    ):
        assert expected in text


def test_source_intent_metadata_rfc_preserves_source_parser_block() -> None:
    text = Path("rfcs/0054-source-intent-metadata-conversion.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "source_intent_to_metadata.execution_free.v0",
        "already validated `SourceIntentModule`",
        "consume preflight reports",
        "produce `ComputeGraph`, TLIR, HAC-IR, HS-IR",
        "direct graph construction would bypass the metadata intake",
        "source parsing remains blocked",
    ):
        assert expected in text
