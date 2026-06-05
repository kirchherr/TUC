"""Compiler pipeline entry points."""

from tuc.compiler.decisions import (
    CompilerDecisionReport,
    OperationDecision,
    build_decision_report,
    dump_decision_report,
)
from tuc.compiler.lowering import lower_hac_to_hs, lower_tlir_to_hac
from tuc.compiler.movement import (
    MOVEMENT_MODEL_VERSION,
    annotate_graph_movement,
    estimate_operation_movement,
    summarize_graph_movement,
)
from tuc.compiler.pipeline import CompilationResult, CompilerPipeline, compile_graph

__all__ = [
    "CompilationResult",
    "CompilerDecisionReport",
    "CompilerPipeline",
    "MOVEMENT_MODEL_VERSION",
    "OperationDecision",
    "annotate_graph_movement",
    "build_decision_report",
    "compile_graph",
    "dump_decision_report",
    "estimate_operation_movement",
    "lower_hac_to_hs",
    "lower_tlir_to_hac",
    "summarize_graph_movement",
]
