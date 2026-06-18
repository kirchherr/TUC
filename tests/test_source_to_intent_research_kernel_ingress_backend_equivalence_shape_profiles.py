from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT,
)
from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract,
    build_kernel_ingress_backend_equivalence_shape_profiles_report,
    build_report,
)
from tuc.runtime import RUNTIME_BACKEND_EQUIVALENCE_CONTRACT

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0.schema.json"
)


def test_kernel_ingress_backend_equivalence_shape_profiles_report_shape() -> None:
    report = build_kernel_ingress_backend_equivalence_shape_profiles_report()
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION
    )
    assert report["kernel_ingress_backend_equivalence_shape_profiles_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
    )
    assert report["kernel_ingress_backend_equivalence_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert report["equivalence_contract"] == RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    assert report["status"] == "PASS"
    assert report["profile_count"] == 2
    assert report["profile_ids"] == ["base", "alternate"]
    assert report["case_count"] == 8
    assert report["comparison_count"] == 8
    assert report["baseline_backend_sequences"] == [
        "reference-cpu->reference-cpu",
        "reference-cpu->reference-cpu->reference-cpu->reference-cpu",
    ]
    assert report["candidate_backend_sequences"] == [
        "linear-sim->vector-sim",
        "vector-sim->vector-sim",
        "linear-sim->vector-sim->vector-sim->vector-sim",
    ]

    mvp_alternate = report["cases"][7]
    assert mvp_alternate["profile_case_id"] == (
        "research_module_mvp_pipeline:alternate"
    )
    assert mvp_alternate["case_id"] == "research_module_mvp_pipeline"
    assert mvp_alternate["graph_name"] == "research_mvp_pipeline"
    assert mvp_alternate["declared_tensor_shapes"] == {
        "a": [3, 5],
        "b": [5, 3],
        "y": [3],
    }
    assert mvp_alternate["baseline_backend_sequence"] == [
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
    ]
    assert mvp_alternate["candidate_backend_sequence"] == [
        "linear-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]
    assert mvp_alternate["terminal_outputs"] == ["stable"]
    assert mvp_alternate["comparison_count"] == 1
    assert mvp_alternate["passed"] is True
    assert mvp_alternate["raw_value_policy"] == "omitted_by_policy"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 7, "case_count"),
        ("comparison_count", 7, "comparison_count"),
        ("profile_count", 1, "profile_count"),
        (
            "kernel_ingress_backend_equivalence_shape_profiles_contract",
            "other",
            "kernel_ingress_backend_equivalence_shape_profiles_contract",
        ),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_backend_equivalence_shape_profiles_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_backend_equivalence_shape_profiles_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
            report
        )


def test_kernel_ingress_backend_equivalence_shape_profiles_rejects_case_drift() -> None:
    report = build_kernel_ingress_backend_equivalence_shape_profiles_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[7], dict)
    cases[7]["declared_tensor_shapes"] = {"a": [9, 9], "b": [9, 9], "y": [9]}

    with pytest.raises(ValueError, match="declared_tensor_shapes drift"):
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
            report
        )


def test_kernel_ingress_backend_equivalence_shape_profiles_rejects_failed_case() -> None:
    report = build_kernel_ingress_backend_equivalence_shape_profiles_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["passed"] = False

    with pytest.raises(ValueError, match="passed drift"):
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
            report
        )


def test_kernel_ingress_backend_equivalence_shape_profiles_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_backend_equivalence_shape_profiles_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/"
            "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"profile_count": 2' in completed.stdout
    assert '"case_count": 8' in completed.stdout
    assert '"tensor_shape_digest"' in completed.stdout
    assert '"baseline_reference_correctness_digest"' in completed.stdout
    assert '"candidate_reference_correctness_digest"' in completed.stdout
    assert "reference-cpu" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_backend_equivalence_shape_profiles_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"][
        "kernel_ingress_backend_equivalence_shape_profiles_contract"
    ]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
    )
    assert schema["properties"]["kernel_ingress_backend_equivalence_contract"][
        "const"
    ] == SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
    assert schema["properties"]["equivalence_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert schema["properties"]["case_count"]["const"] == 8
    assert schema["properties"]["profile_count"]["const"] == 2
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "tensor_shape_digest" in schema["$defs"]["case"]["required"]


def test_kernel_ingress_backend_equivalence_shape_profiles_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py"
    )
    doc_path = (
        "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
    )

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0182-source-to-intent-research-kernel-ingress-backend-equivalence.md"
        ),
        Path(
            "rfcs/"
            "0183-source-to-intent-research-kernel-ingress-backend-equivalence-shape-profiles.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0183-source-to-intent-research-kernel-ingress-backend-equivalence-shape-profiles.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
