"""Run the CI-facing Source-To-Intent Research Capability Claim Gate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_capability_claim import (
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_FORBIDDEN_FRAGMENTS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS,
        assert_research_capability_claim_report_contract,
    )
    from examples.source_to_intent_research_capability_claim import (
        build_report as build_capability_claim_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_capability_claim import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_FORBIDDEN_FRAGMENTS,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH,
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS,
        assert_research_capability_claim_report_contract,
    )
    from source_to_intent_research_capability_claim import (
        build_report as build_capability_claim_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT = (
    "source_to_intent_research_capability_claim_gate.ci.v0"
)


class SourceToIntentResearchCapabilityClaimGateError(AssertionError):
    """Raised when the capability claim gate binding is incomplete."""


def build_gate_report(*, capability_claim_text: str | None = None) -> str:
    """Return stable CI-facing binding for the capability claim."""

    expected_claim = build_capability_claim_report()
    claim_text = expected_claim if capability_claim_text is None else capability_claim_text
    claim = _assert_capability_claim_bound(claim_text)
    if _digest(claim_text) != _digest(expected_claim):
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: claim digest drift"
        )
    report = _render_gate_report(claim_text, claim)
    assert_capability_claim_gate_report_contract(report)
    return report


def main() -> None:
    print(build_gate_report(), end="")


def assert_capability_claim_gate_report_contract(text: object) -> None:
    """Fail closed unless the capability claim gate text matches v0."""

    if not isinstance(text, str):
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: gate output must be text"
        )
    required_fragments = (
        "source_to_intent.research_capability_claim_gate "
        "@source_to_intent_research_capability_claim_gate_v0 {",
        (
            f'  gate_contract = "'
            f'{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT}"'
        ),
        f'  claim_contract = "{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT}"',
        '  capability_claim = "passed"',
        '  capability_claim_digest = "sha256:',
        f'  claim_id = "{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID}"',
        f'  claim_scope = "{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE}"',
        f'  claim_status = "{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS}"',
        '  accepted_kernel_count = "4"',
        '  runtime_case_count = "4"',
        (
            '  combined_pipeline = "'
            + "->".join(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH)
            + '"'
        ),
        '  trusted_runtime_backends = "linear-sim,vector-sim"',
        '  evidence_count = "7"',
        (
            '  supported_claims = "'
            + ",".join(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS)
            + '"'
        ),
        (
            '  blocked_claims = "'
            + ",".join(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS)
            + '"'
        ),
        f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"',
        (
            f'  default_parser_status = "'
            f'{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
        ),
        '  artifact_policy = "digest_only_source_free"',
        '  status = "PASS"',
        "}",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise SourceToIntentResearchCapabilityClaimGateError(
                "capability claim gate failed: required binding missing"
            )
    _assert_text_is_source_free(text)


def _assert_capability_claim_bound(text: str) -> Mapping[str, object]:
    if not isinstance(text, str):
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: claim report must be text"
        )
    _assert_text_is_source_free(text)
    try:
        claim = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: claim report not JSON"
        ) from exc
    try:
        assert_research_capability_claim_report_contract(claim)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: claim report binding missing"
        ) from exc
    if not isinstance(claim, Mapping):
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: claim report must be object"
        )
    return claim


def _render_gate_report(
    claim_text: str,
    claim: Mapping[str, object],
) -> str:
    lines = [
        "source_to_intent.research_capability_claim_gate "
        "@source_to_intent_research_capability_claim_gate_v0 {",
        (
            "  gate_contract = "
            f'"{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT}"'
        ),
        f'  claim_contract = "{claim["claim_contract"]}"',
        '  capability_claim = "passed"',
        f'  capability_claim_digest = "{_digest(claim_text)}"',
        f'  claim_id = "{claim["claim_id"]}"',
        f'  claim_scope = "{claim["claim_scope"]}"',
        f'  claim_status = "{claim["claim_status"]}"',
        f'  accepted_kernel_count = "{claim["accepted_kernel_count"]}"',
        f'  runtime_case_count = "{claim["runtime_case_count"]}"',
        (
            '  combined_pipeline = "'
            + "->".join(_string_list(claim["combined_pipeline_operation_path"]))
            + '"'
        ),
        (
            '  trusted_runtime_backends = "'
            + ",".join(_string_list(claim["trusted_runtime_backends"]))
            + '"'
        ),
        f'  evidence_count = "{claim["evidence_count"]}"',
        (
            '  supported_claims = "'
            + ",".join(_string_list(claim["supported_claims"]))
            + '"'
        ),
        (
            '  blocked_claims = "'
            + ",".join(_string_list(claim["blocked_claims"]))
            + '"'
        ),
        f'  parser_status = "{claim["parser_status"]}"',
        f'  default_parser_status = "{claim["default_parser_status"]}"',
        f'  artifact_policy = "{claim["artifact_policy"]}"',
        '  status = "PASS"',
        "}",
    ]
    return "\n".join(lines) + "\n"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceToIntentResearchCapabilityClaimGateError(
            "capability claim gate failed: expected list binding missing"
        )
    return [str(item) for item in value]


def _assert_text_is_source_free(text: str) -> None:
    for fragment in SOURCE_TO_INTENT_RESEARCH_CAPABILITY_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise SourceToIntentResearchCapabilityClaimGateError(
                "capability claim gate failed: forbidden source fragment"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
