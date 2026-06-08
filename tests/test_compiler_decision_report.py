from __future__ import annotations

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef


def test_compiler_decision_report_connects_support_diagnostics_to_assignments() -> None:
    a = TensorRef("a", (16, 32))
    b = TensorRef("b", (32, 8))
    c = TensorRef("c", (16, 8))
    y = TensorRef("y", (16, 8))
    graph = ComputeGraph(
        name="mlp",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )

    result = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    projection, activation = result.decision_report.operation_reports
    assert projection.operation_name == "projection"
    assert projection.assigned_backend == "linear-sim"
    assert projection.accepted_backends == ("linear-sim",)
    assert projection.rejected_backends == ()
    assert projection.support_diagnostics[0].reason == "accepted"

    assert activation.operation_name == "activation"
    assert activation.assigned_backend == "gpu"
    assert activation.accepted_backends == ()
    assert activation.rejected_backends == ("linear-sim",)
    assert activation.support_diagnostics[0].reason == "unsupported_operation_kind"

    assert result.dump_decision_report() == "\n".join(
        (
            "compiler.decision_report @mlp {",
            "  operation projection kind=matmul assigned=linear-sim "
            'accepted_backends="linear-sim" rejected_backends="-" '
            'reason="preferred_for:matmul;domain=analog_weight_bank;'
            'transfer_bytes=0;layout_conversion_bytes=0;produced_layout=row_major"',
            "  support {",
            '    linear-sim accepted reason="accepted" '
            'detail="capability accepts operation kind, layout, and error budget"',
            "  }",
            "  operation activation kind=elementwise assigned=gpu "
            'accepted_backends="-" rejected_backends="linear-sim" '
            'reason="fallback:transfer_bytes=512;layout_conversion_bytes=0;'
            'actual_transfer_bytes=512;actual_layout_conversion_bytes=0"',
            "  support {",
            '    linear-sim rejected reason="unsupported_operation_kind" '
            'detail="elementwise not declared in supported_ops"',
            "  }",
            "}",
        )
    )


def test_compiler_decision_report_keeps_rejection_reason_for_fallback() -> None:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    out = TensorRef("out", (4, 4))
    graph = ComputeGraph(
        name="budget_rejected",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
                attributes={"max_error_budget": 0.2},
            ),
        ),
    )
    bounded = BackendCapability(
        name="bounded-linear",
        supported_ops=frozenset({OperationKind.MATMUL}),
        max_error_budget=0.05,
    )

    result = compile_graph(graph, [bounded])
    report = result.decision_report.operation_reports[0]

    assert report.assigned_backend == "gpu"
    assert report.accepted_backends == ()
    assert report.rejected_backends == ("bounded-linear",)
    assert report.support_diagnostics[0].reason == "error_budget_exceeds_backend_limit"
    assert "requested=0.2 backend_max=0.05" in report.support_diagnostics[0].detail
