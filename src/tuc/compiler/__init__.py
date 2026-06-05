"""Compiler pipeline entry points."""

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
    "CompilerPipeline",
    "MOVEMENT_MODEL_VERSION",
    "annotate_graph_movement",
    "compile_graph",
    "estimate_operation_movement",
    "lower_hac_to_hs",
    "lower_tlir_to_hac",
    "summarize_graph_movement",
]
