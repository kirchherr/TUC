"""Emit the current Real Triton Integration Readiness report."""

from tuc.frontend import (
    TritonIntegrationReadinessPrerequisite,
    build_triton_integration_readiness_report,
    dump_triton_integration_readiness_report,
)

_CURRENT_PREREQUISITES = (
    TritonIntegrationReadinessPrerequisite(
        "triton_source_threat_model",
        "satisfied",
        "docs.TRITON_SOURCE_THREAT_MODEL",
    ),
    TritonIntegrationReadinessPrerequisite(
        "triton_source_preflight",
        "satisfied",
        "examples.triton_source_preflight",
    ),
    TritonIntegrationReadinessPrerequisite(
        "triton_idiom_coverage_report",
        "satisfied",
        "examples.triton_idiom_coverage_report",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_intent_plain_data_contract",
        "satisfied",
        "docs.SOURCE_INTENT_IR",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_intent_frontend_conformance_gate",
        "satisfied",
        "examples.source_intent_frontend_conformance_gate",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_to_intent_parser_gate",
        "satisfied",
        "docs.SOURCE_TO_INTENT_PARSER_GATE",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_to_intent_research_parser",
        "satisfied",
        "examples.source_to_intent_research_parser",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_to_intent_research_kernel_ingress",
        "satisfied",
        "examples.source_to_intent_research_kernel_ingress_evidence_gate",
    ),
    TritonIntegrationReadinessPrerequisite(
        "backend_equivalence_proof",
        "satisfied",
        "examples.proof_of_backend_equivalence",
    ),
    TritonIntegrationReadinessPrerequisite(
        "layout_conversion_evidence",
        "satisfied",
        "examples.runtime_layout_conversion_trace_replay_verifier",
    ),
    TritonIntegrationReadinessPrerequisite(
        "broader_parser_implementation_rfc",
        "satisfied",
        "rfcs.0242_source_to_intent_next_syntax_slice",
    ),
    TritonIntegrationReadinessPrerequisite(
        "semantic_mapping_corpus_for_next_syntax",
        "satisfied",
        "examples.source_to_intent_next_syntax_slice",
    ),
    TritonIntegrationReadinessPrerequisite(
        "source_intent_goldens_for_next_syntax",
        "satisfied",
        "tests.golden.frontend.source_to_intent_next_syntax_source_intent",
    ),
    TritonIntegrationReadinessPrerequisite(
        "fuzz_semantic_mapping_for_next_syntax",
        "satisfied",
        "tests.test_source_to_intent_next_syntax_slice",
    ),
    TritonIntegrationReadinessPrerequisite(
        "external_frontend_package_conformance",
        "satisfied",
        "examples.external_frontend_package_conformance",
    ),
    TritonIntegrationReadinessPrerequisite(
        "direct_triton_source_ingestion",
        "blocked_by_policy",
        "docs.SOURCE_TO_INTENT_PARSER_GATE",
        required_for_readiness=False,
    ),
    TritonIntegrationReadinessPrerequisite(
        "triton_jit_execution_permission",
        "blocked_by_policy",
        "docs.TRITON_SOURCE_THREAT_MODEL",
        required_for_readiness=False,
    ),
)


def build_current_triton_integration_readiness_report():
    """Build the current data-only readiness state for Real Triton Integration."""

    return build_triton_integration_readiness_report(
        "real_triton_integration_readiness_current",
        _CURRENT_PREREQUISITES,
    )


def build_report() -> str:
    """Return stable JSON for the current readiness report."""

    return dump_triton_integration_readiness_report(
        build_current_triton_integration_readiness_report()
    )


if __name__ == "__main__":
    print(build_report(), end="")