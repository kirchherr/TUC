"""Emit Source Intent frontend conformance evidence for review."""

from __future__ import annotations

from copy import deepcopy

from examples.source_intent_intake import build_source_intent_data
from examples.source_intent_return_semantics import build_source_intent_return_data
from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    SourceIntentFrontendConformanceCase,
    dump_source_intent_frontend_conformance_report,
    run_source_intent_frontend_conformance,
)

ConformanceCases = tuple[SourceIntentFrontendConformanceCase, ...]


def build_source_intent_frontend_conformance_cases() -> ConformanceCases:
    """Return accepted and rejected in-memory conformance cases."""

    return (
        SourceIntentFrontendConformanceCase(
            name="valid_source_intent_mlp",
            payload=build_source_intent_data(),
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="valid_source_intent_return_mlp",
            payload=build_source_intent_return_data(),
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_source_text_escape",
            payload={
                "name": "bad",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "python_source": "@triton.jit\ndef kernel(): pass",
                "tensors": [],
                "operations": [],
            },
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_backend_hint_escape",
            payload={
                "name": "bad",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "tensors": [{"name": "a", "shape": [1]}],
                "operations": [
                    {
                        "name": "op",
                        "family": "matmul",
                        "inputs": ["a"],
                        "outputs": ["a"],
                        "hints": {"backend": "gpu"},
                    }
                ],
            },
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_unknown_tensor_reference",
            payload={
                "name": "bad",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "tensors": [{"name": "a", "shape": [1]}],
                "operations": [
                    {
                        "name": "op",
                        "family": "elementwise",
                        "inputs": ["missing"],
                        "outputs": ["a"],
                    }
                ],
            },
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_return_unknown_tensor",
            payload=_return_payload_with(
                [
                    {
                        "public_name": "api_missing",
                        "tensor_name": "missing",
                        "required": True,
                    }
                ]
            ),
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_return_intermediate_tensor",
            payload=_return_payload_with(
                [
                    {
                        "public_name": "api_c",
                        "tensor_name": "c",
                        "required": True,
                    }
                ]
            ),
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_duplicate_public_returns",
            payload=_return_payload_with(
                [
                    {
                        "public_name": "api_y",
                        "tensor_name": "y",
                        "required": True,
                    },
                    {
                        "public_name": "api_y",
                        "tensor_name": "y",
                        "required": True,
                    },
                ]
            ),
            should_accept=False,
        ),
    )


def _return_payload_with(returns: list[dict[str, object]]) -> dict[str, object]:
    payload = deepcopy(build_source_intent_return_data())
    payload["returns"] = returns
    return payload


def main() -> None:
    report = run_source_intent_frontend_conformance(
        "example-source-intent-frontend",
        build_source_intent_frontend_conformance_cases(),
    )
    print(dump_source_intent_frontend_conformance_report(report), end="")


if __name__ == "__main__":
    main()
