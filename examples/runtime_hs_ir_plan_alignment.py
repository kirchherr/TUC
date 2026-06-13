"""Emit HS-IR to runtime-plan alignment evidence for a mixed backend slice."""

from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
from tuc import (
    RuntimeHsIrPlanAlignmentReport,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    build_runtime_hs_ir_plan_alignment_report,
    compile_graph,
    dump_runtime_hs_ir_plan_alignment_report,
    execute_graph,
)


def build_alignment_report() -> RuntimeHsIrPlanAlignmentReport:
    """Compile, execute, and report HS-IR/runtime-plan alignment."""

    graph = build_graph()
    compiled = compile_graph(
        graph,
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        proof_inputs(),
    )
    return build_runtime_hs_ir_plan_alignment_report(
        compiled.hs_ir,
        compiled.partition_plan,
        execution,
    )


def build_report() -> str:
    """Return the stable serialized HS-IR/runtime-plan alignment report."""

    return dump_runtime_hs_ir_plan_alignment_report(build_alignment_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
