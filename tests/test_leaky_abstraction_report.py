from __future__ import annotations

from dataclasses import replace

import pytest

from examples.leaky_abstraction_report import build_graph
from tuc import (
    LEAKY_ABSTRACTION_ARTIFACT_STATUS,
    LEAKY_ABSTRACTION_DEFAULT_ISSUES,
    LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
    LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    LeakyAbstractionFact,
    build_leaky_abstraction_report,
    compile_graph,
    dump_leaky_abstraction_report,
    leaky_abstraction_report_to_dict,
)
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.ir import HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES, ComputeGraph
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT


def _compiled_hac_ir():
    simulator = LinearAlgebraSimulatorBackend()
    return compile_graph(build_graph(), [simulator.capability]).hac_ir


def test_leaky_abstraction_report_preserves_hac_ir_boundary() -> None:
    report = build_leaky_abstraction_report(
        _compiled_hac_ir(),
        performance_facts=(
            LeakyAbstractionFact(
                fact_id="matmul_tile_shape",
                correct_home="backend_implementation",
                required_for_performance=True,
            ),
            LeakyAbstractionFact(
                fact_id="transfer_latency_model",
                correct_home="runtime_plan",
                required_for_performance=True,
            ),
        ),
    )
    payload = leaky_abstraction_report_to_dict(report)

    assert payload["schema_version"] == LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == LEAKY_ABSTRACTION_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == (
        LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS
    )
    assert payload["native_performance_claim"] is False
    assert payload["hac_ir_contract_valid"] is True
    assert payload["hac_ir_leak_detected"] is False
    assert payload["detected_leaks"] == []
    assert payload["issues"] == list(LEAKY_ABSTRACTION_DEFAULT_ISSUES)
    assert len(payload["checked_forbidden_attributes"]) == len(
        HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES
    )
    assert all(not fact["enters_hac_ir"] for fact in payload["performance_facts"])


def test_leaky_abstraction_report_is_json_serializable() -> None:
    report = build_leaky_abstraction_report(_compiled_hac_ir())

    dumped = dump_leaky_abstraction_report(report)

    assert '"schema_version": "tuc.leaky_abstraction_report.v0"' in dumped
    assert '"performance_claim_status": "blocked"' in dumped


def test_leaky_abstraction_report_detects_forbidden_hac_ir_attribute() -> None:
    hac_ir = _compiled_hac_ir()
    operation = hac_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={**operation.attributes, "tuc.cuda_arch": "sm_90"},
    )
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,) + hac_ir.graph.operations[1:],
        metadata=hac_ir.graph.metadata,
    )

    report = build_leaky_abstraction_report(replace(hac_ir, graph=bad_graph))
    payload = leaky_abstraction_report_to_dict(report)

    assert payload["hac_ir_contract_valid"] is False
    assert payload["hac_ir_leak_detected"] is True
    assert payload["detected_leaks"] == [
        {
            "attribute_name": "tuc.cuda_arch",
            "operation_name": "dense_projection",
            "reason": "vendor target details belong to backend capabilities",
        }
    ]
    assert "forbidden_hardware_fact_entered_hac_ir" in payload["issues"]


def test_leaky_abstraction_report_blocks_fact_entering_hac_ir() -> None:
    report = build_leaky_abstraction_report(
        _compiled_hac_ir(),
        performance_facts=(
            LeakyAbstractionFact(
                fact_id="cuda_launch_grid",
                correct_home="backend_implementation",
                required_for_performance=True,
                enters_hac_ir=True,
            ),
        ),
    )
    payload = leaky_abstraction_report_to_dict(report)

    assert payload["hac_ir_leak_detected"] is True
    assert "performance_fact_entered_hac_ir" in payload["issues"]


def test_leaky_abstraction_report_rejects_duplicate_fact_ids() -> None:
    with pytest.raises(ValueError, match="duplicate leaky abstraction fact id"):
        build_leaky_abstraction_report(
            _compiled_hac_ir(),
            performance_facts=(
                LeakyAbstractionFact(
                    fact_id="same_fact",
                    correct_home="runtime_plan",
                    required_for_performance=True,
                ),
                LeakyAbstractionFact(
                    fact_id="same_fact",
                    correct_home="hs_ir",
                    required_for_performance=True,
                ),
            ),
        )


def test_leaky_abstraction_report_rejects_unknown_fact_home() -> None:
    with pytest.raises(ValueError, match="unsupported leaky abstraction fact home"):
        build_leaky_abstraction_report(
            _compiled_hac_ir(),
            performance_facts=(
                LeakyAbstractionFact(
                    fact_id="bad_home",
                    correct_home="hac_ir",
                    required_for_performance=True,
                ),
            ),
        )
