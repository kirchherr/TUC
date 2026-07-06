from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress import (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
    REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
    REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_report_contract,
    build_kernel_ingress_report,
    build_report,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SourceToIntentResearchKernelIngressError,
    dump_source_to_intent_research_kernel_ingress_report,
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json"
)


def test_kernel_ingress_frontend_extracts_realistic_module_source() -> None:
    result = ingest_triton_module_source_to_source_intent(
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        source_name="research_matmul_elementwise",
        kernel_name="matmul_elementwise",
        tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4, 2)},
    )

    report = source_to_intent_research_kernel_ingress_report_to_dict(result.report)
    assert report["schema_version"] == (
        "tuc.source_to_intent_research_kernel_ingress_report.v0"
    )
    assert report["ingress_contract"] == SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    assert report["input_policy"] == "single_triton_module_source_buffer_only"
    assert report["output_policy"] == (
        "extracted_kernel_source_to_source_intent.v0_plain_data"
    )
    assert report["allowed_import_aliases"] == ["tl", "triton"]
    assert report["operation_families"] == ["elementwise", "matmul"]
    assert result.parser_result.source_intent_payload["name"] == (
        "research_matmul_elementwise"
    )

    dumped = dump_source_to_intent_research_kernel_ingress_report(result.report)
    assert "@triton.jit" not in dumped
    assert "import triton" not in dumped
    assert "tl.dot" not in dumped
    assert "source_intent_payload" not in dumped


def test_kernel_ingress_frontend_extracts_matmul_reduction_module_source() -> None:
    result = ingest_triton_module_source_to_source_intent(
        REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
        source_name="research_matmul_reduction",
        kernel_name="matmul_reduction",
        tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4,)},
    )

    report = source_to_intent_research_kernel_ingress_report_to_dict(result.report)
    assert report["operation_families"] == ["matmul", "reduction"]
    assert result.parser_result.source_intent_payload["name"] == (
        "research_matmul_reduction"
    )

    dumped = dump_source_to_intent_research_kernel_ingress_report(result.report)
    assert "@triton.jit" not in dumped
    assert "import triton" not in dumped
    assert "tl.dot" not in dumped
    assert "tl.store" not in dumped
    assert "source_intent_payload" not in dumped


def test_kernel_ingress_frontend_extracts_mvp_pipeline_module_source() -> None:
    result = ingest_triton_module_source_to_source_intent(
        REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
        source_name="research_mvp_pipeline",
        kernel_name="mvp_pipeline",
        tensor_shapes={"a": (4, 8), "b": (8, 4), "y": (4,)},
    )

    report = source_to_intent_research_kernel_ingress_report_to_dict(result.report)
    assert report["operation_families"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert result.parser_result.source_intent_payload["name"] == (
        "research_mvp_pipeline"
    )

    dumped = dump_source_to_intent_research_kernel_ingress_report(result.report)
    assert "@triton.jit" not in dumped
    assert "import triton" not in dumped
    assert "tl.dot" not in dumped
    assert "tl.store" not in dumped
    assert "source_intent_payload" not in dumped


@pytest.mark.parametrize(
    ("source", "error"),
    [
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
                "import triton", "import os"
            ),
            "supports only import triton",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
            + "\ndef extra_kernel(a):\n    tl.store(a, a)\n",
            "exactly one top-level kernel function",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
            + "\nSIDE_EFFECT = open('secret.txt')\n",
            "supports only imports and one kernel function",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
                "import triton.language as tl", "from triton import language as tl"
            ),
            "forbids import-from statements",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace("@triton.jit\n", ""),
            "requires one @triton.jit decorator",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
                "@triton.jit", "@triton.jit(num_warps=4)"
            ),
            "forbids decorator calls",
        ),
        (
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
                "@triton.jit", "@not_triton.jit"
            ),
            "requires @triton.jit decorator data",
        ),
    ],
)
def test_kernel_ingress_rejects_unsupported_module_surfaces(
    source: str,
    error: str,
) -> None:
    with pytest.raises(SourceToIntentResearchKernelIngressError, match=error):
        ingest_triton_module_source_to_source_intent(
            source,
            source_name="research_matmul_elementwise",
            kernel_name="matmul_elementwise",
            tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4, 2)},
        )


def test_kernel_ingress_rejects_kernel_name_mismatch() -> None:
    with pytest.raises(SourceToIntentResearchKernelIngressError, match="name mismatch"):
        ingest_triton_module_source_to_source_intent(
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
            source_name="research_matmul_elementwise",
            kernel_name="other_kernel",
            tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4, 2)},
        )


def test_kernel_ingress_e2e_report_shape() -> None:
    report = build_kernel_ingress_report()
    assert_kernel_ingress_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION
    )
    assert report["e2e_contract"] == SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT
    assert report["status"] == "PASS"
    assert report["case_count"] == 5
    assert report["source_boundary"] == (
        "triton_module_source_buffer_to_runtime_via_research_kernel_ingress"
    )
    assert [case["case_id"] for case in report["cases"]] == [
        "research_module_matmul_elementwise",
        "research_module_softmax_reduction",
        "research_module_matmul_reduction",
        "research_module_softmax_elementwise",
        "research_module_mvp_pipeline",
    ]
    assert report["cases"][0]["backend_sequence"] == ["linear-sim", "vector-sim"]
    assert report["cases"][1]["backend_sequence"] == ["vector-sim", "vector-sim"]
    assert report["cases"][2]["backend_sequence"] == ["linear-sim", "vector-sim"]
    assert report["cases"][3]["backend_sequence"] == ["vector-sim", "vector-sim"]
    assert report["cases"][4]["backend_sequence"] == [
        "linear-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]
    assert report["cases"][4]["trace_step_count"] == 4


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 1, "case_count"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "import triton", "top-level report"),
    ],
)
def test_kernel_ingress_e2e_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_report_contract(report)


def test_kernel_ingress_e2e_contract_rejects_case_drift() -> None:
    report = build_kernel_ingress_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["backend_sequence"] = ["reference-cpu", "vector-sim"]

    with pytest.raises(ValueError, match="backend drift"):
        assert_kernel_ingress_report_contract(report)


def test_kernel_ingress_e2e_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_kernel_ingress.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"source_boundary"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["e2e_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT
    )
    assert schema["properties"]["frontend_ingress_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "blocked_claims" in schema["required"]


def test_kernel_ingress_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_kernel_ingress.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
