from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_evidence_gate import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
    SourceToIntentResearchKernelIngressEvidenceGateError,
    assert_kernel_ingress_evidence_gate_report_contract,
    build_gate_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt"
)


def test_kernel_ingress_evidence_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == GOLDEN_PATH.read_text(encoding="utf-8")
    assert (
        f'gate_contract = "{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT}"'
        in report
    )
    assert 'kernel_ingress = "passed"' in report
    assert 'runtime_matrix = "passed"' in report
    assert 'runtime_step_trace = "passed"' in report
    assert 'runtime_evidence_bundle_index = "passed"' in report
    assert 'runtime_output_closure_index = "passed"' in report
    assert 'runtime_replay_verifier_index = "passed"' in report
    assert 'runtime_backend_equivalence = "passed"' in report
    assert 'runtime_backend_equivalence_shape_profiles = "passed"' in report
    assert 'runtime_coverage_policy = "passed"' in report
    assert 'runtime_backend_alignment = "passed"' in report
    assert 'boundary_budget = "passed"' in report
    assert 'rejection_coverage = "passed"' in report
    assert 'diagnostics = "passed"' in report
    assert 'conformance_gate = "passed"' in report
    assert 'idiom_alignment = "passed"' in report
    assert 'proof_bundle = "passed"' in report
    assert 'covered_rejections = "13"' in report
    assert (
        'diagnostics_rejection_reasons = "decorator_call,'
        'import_after_kernel_function,import_from_statement,kernel_name_mismatch,'
        'missing_triton_jit_decorator,multiple_kernel_functions,'
        'top_level_side_effect,unsupported_decorator,unsupported_import"'
        in report
    )
    assert (
        'budget_rejection_reasons = "module_byte_budget,module_line_budget,'
        'module_ast_node_budget,module_ast_depth_budget"'
        in report
    )
    assert (
        'backend_sequences = "linear-sim->vector-sim,vector-sim->vector-sim,'
        'linear-sim->vector-sim->vector-sim->vector-sim"'
        in report
    )
    assert 'trusted_executor_registry = "trusted_runtime_executor_registry.v0"' in report
    assert 'trusted_runtime_backends = "linear-sim,vector-sim"' in report
    assert 'runtime_case_count = "5"' in report
    assert 'runtime_step_trace_cases = "5"' in report
    assert 'runtime_evidence_bundle_cases = "5"' in report
    assert 'runtime_output_closure_cases = "5"' in report
    assert 'runtime_output_closure_check_count = "2"' in report
    assert 'output_closure_contract = "runtime_execution_output_closure.data_only.v0"' in report
    assert 'runtime_replay_verifier_cases = "5"' in report
    assert 'runtime_replay_verifier_check_count = "8"' in report
    assert 'replay_verifier_contract = "runtime_evidence_replay_verifier.review.v0"' in report
    assert 'runtime_backend_equivalence_cases = "5"' in report
    assert 'backend_equivalence_comparisons = "5"' in report
    assert 'runtime_backend_equivalence_shape_profile_cases = "10"' in report
    assert 'backend_equivalence_shape_profile_comparisons = "10"' in report
    assert 'shape_profile_ids = "base,alternate"' in report
    assert (
        'baseline_backend_sequences = "reference-cpu->reference-cpu,'
        'reference-cpu->reference-cpu->reference-cpu->reference-cpu"'
        in report
    )
    assert (
        'runtime_evidence_sections = "tensor_store_evidence,input_manifest,'
        'output_manifest,output_contract,public_output_bundle,'
        'reference_correctness,execution_receipt"'
        in report
    )
    assert (
        'mvp_pipeline_operation_path = "matmul->softmax->reduction->elementwise"'
        in report
    )
    assert 'status = "PASS"' in report


def test_kernel_ingress_evidence_gate_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_evidence_gate.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "sha256:" in completed.stdout
    assert "kernel_ingress_digest" in completed.stdout
    assert "runtime_matrix_digest" in completed.stdout
    assert "runtime_step_trace_digest" in completed.stdout
    assert "runtime_evidence_bundle_index_digest" in completed.stdout
    assert "runtime_output_closure_index_digest" in completed.stdout
    assert "runtime_replay_verifier_index_digest" in completed.stdout
    assert "runtime_backend_equivalence_digest" in completed.stdout
    assert "runtime_backend_equivalence_shape_profiles_digest" in completed.stdout
    assert "runtime_coverage_policy_digest" in completed.stdout
    assert "runtime_backend_alignment_digest" in completed.stdout
    assert "rejection_coverage_digest" in completed.stdout
    assert "proof_bundle_digest" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_evidence_gate_rejects_tampered_kernel_ingress() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="kernel ingress binding missing",
    ):
        build_gate_report(kernel_ingress_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_rejection_coverage() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="rejection coverage binding missing",
    ):
        build_gate_report(rejection_coverage_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_runtime_matrix() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime matrix binding missing",
    ):
        build_gate_report(runtime_matrix_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_runtime_step_trace() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime step trace binding missing",
    ):
        build_gate_report(runtime_step_trace_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_bundle_index() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime evidence bundle index binding missing",
    ):
        build_gate_report(runtime_evidence_bundle_index_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_output_closure_index() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime output closure index binding missing",
    ):
        build_gate_report(runtime_output_closure_index_text='{"status": "PASS"}\n')



def test_kernel_ingress_evidence_gate_rejects_tampered_replay_verifier_index() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime replay verifier index binding missing",
    ):
        build_gate_report(runtime_replay_verifier_index_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_backend_equivalence() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime backend equivalence binding missing",
    ):
        build_gate_report(runtime_backend_equivalence_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_shape_profiles() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime backend equivalence shape profiles binding missing",
    ):
        build_gate_report(
            runtime_backend_equivalence_shape_profiles_text='{"status": "PASS"}\n'
        )


def test_kernel_ingress_evidence_gate_rejects_tampered_runtime_coverage_policy() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime coverage policy binding missing",
    ):
        build_gate_report(runtime_coverage_policy_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_runtime_backend_alignment() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="runtime backend alignment binding missing",
    ):
        build_gate_report(runtime_backend_alignment_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_proof_bundle() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="proof bundle binding missing",
    ):
        build_gate_report(proof_bundle_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_source_leakage() -> None:
    leaky_conformance = (
        'source_intent_frontend_conformance = "passed"\n'
        'ingress_sources = "research_matmul_elementwise,'
        'research_softmax_reduction,research_matmul_reduction,research_softmax_elementwise,'
        'research_mvp_pipeline"\n'
        'kernel_names = "matmul_elementwise,softmax_reduction,'
        'matmul_reduction,softmax_elementwise,mvp_pipeline"\n'
        'status = "PASS"\n'
        "@triton.jit\n"
    )

    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="forbidden source fragment",
    ):
        build_gate_report(conformance_gate_text=leaky_conformance)


def test_kernel_ingress_evidence_gate_contract_rejects_drift() -> None:
    report = build_gate_report().replace('status = "PASS"', 'status = "WARN"')

    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="required binding missing",
    ):
        assert_kernel_ingress_evidence_gate_report_contract(report)


def test_kernel_ingress_evidence_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_research_kernel_ingress_evidence_gate.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"
    replay_verifier_index_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py"
    )

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md"),
        Path(
            "rfcs/"
            "0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md"
        ),
        Path(
            "rfcs/"
            "0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md"
        ),
        Path(
            "rfcs/"
            "0209-source-to-intent-research-kernel-ingress-runtime-output-closure-index.md"
        ),
        Path(
            "rfcs/"
            "0211-source-to-intent-research-kernel-ingress-runtime-replay-verifier-index.md"
        ),
        Path(
            "rfcs/"
            "0183-source-to-intent-research-kernel-ingress-backend-equivalence-shape-profiles.md"
        ),
        Path(
            "rfcs/"
            "0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md"
        ),
        Path(
            "rfcs/"
            "0175-source-to-intent-research-kernel-ingress-runtime-backend-alignment.md"
        ),
    ):
        assert gate_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")

    focused_gate_doc = Path(
        "docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"
    ).read_text(encoding="utf-8")
    assert replay_verifier_index_path in focused_gate_doc
    assert "Kernel Ingress Runtime Replay Verifier Index evidence" in focused_gate_doc
    assert "runtime replay verifier index" in focused_gate_doc
    assert "Follow-Up Evidence" not in focused_gate_doc
