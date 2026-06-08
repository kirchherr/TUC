"""External-style backend author path for TUC Backend API v0.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.backends.conformance import BackendConformanceReport, assert_backend_conformance
from tuc.backends.registry import BackendRegistry
from tuc.compiler import CompilationResult, compile_graph
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.manifests import load_backend_capability_manifest

MANIFEST_PATH = Path(__file__).with_name("manifests") / "external_vector_backend.json"


class ExternalVectorBackend:
    """Trusted in-process prototype backend supplied by an external author."""

    def __init__(self, capability: BackendCapability) -> None:
        self._capability = capability

    @property
    def capability(self) -> BackendCapability:
        """Return declarative capability data loaded from an explicit manifest."""

        return self._capability

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        """Lower only graph operations accepted by the declared capability."""

        unsupported = [
            operation.name
            for operation in graph.operations
            if not self.capability.supports(operation)
        ]
        if unsupported:
            raise ValueError("external-vector cannot lower: " + ", ".join(unsupported))

        lines = [
            f"# backend: {self.capability.name}",
            f"# graph: {graph.name}",
            "# artifact_kind: external_author_demo",
        ]
        for operation in graph.operations:
            inputs = ", ".join(tensor.name for tensor in operation.inputs)
            outputs = ", ".join(tensor.name for tensor in operation.outputs)
            lines.append(f"{operation.kind.value} {operation.name}: ({inputs}) -> ({outputs})")

        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="\n".join(lines),
            diagnostics=("lowered=external-author-demo",),
        )


@dataclass(frozen=True)
class ExternalBackendAuthorReport:
    """Reviewable outputs from the external backend author path."""

    registry: BackendRegistry
    compiled: CompilationResult
    conformance: BackendConformanceReport
    lowered: LoweringResult


def build_backend_from_manifest(path: Path = MANIFEST_PATH) -> ExternalVectorBackend:
    """Build a trusted prototype backend from explicit capability data."""

    return ExternalVectorBackend(load_backend_capability_manifest(path))


def build_graph() -> ComputeGraph:
    """Build a tiny graph that an external elementwise backend can accept."""

    x = TensorRef("x", (4, 4))
    y = TensorRef("y", (4, 4))
    return ComputeGraph(
        name="external_backend_author_demo",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
            ),
        ),
    )


def assigned_graph_for_backend(
    compiled: CompilationResult,
    backend_name: str,
) -> ComputeGraph:
    """Return the HAC-IR subgraph assigned to one backend by HS-IR metadata."""

    assigned_operation_names = {
        operation.name
        for operation in compiled.hs_ir.graph.operations
        if operation.attributes["tuc.assigned_backend"] == backend_name
    }
    return ComputeGraph(
        name=compiled.hac_ir.graph.name,
        operations=tuple(
            operation
            for operation in compiled.hac_ir.graph.operations
            if operation.name in assigned_operation_names
        ),
        metadata=compiled.hac_ir.graph.metadata,
    )


def run_external_backend_author_path(
    manifest_path: Path = MANIFEST_PATH,
) -> ExternalBackendAuthorReport:
    """Run manifest registry, compiler planning, conformance, and trusted lowering."""

    registry = BackendRegistry.from_manifest_paths([manifest_path])
    backend = ExternalVectorBackend(registry.capability("external-vector"))
    graph = build_graph()
    compiled = compile_graph(graph, registry.capabilities())
    conformance = assert_backend_conformance(backend)
    lowered = backend.lower(assigned_graph_for_backend(compiled, backend.capability.name))
    return ExternalBackendAuthorReport(
        registry=registry,
        compiled=compiled,
        conformance=conformance,
        lowered=lowered,
    )


def main() -> None:
    report = run_external_backend_author_path()

    print("registered_backends=" + ",".join(report.registry.names()))
    for diagnostic in report.registry.diagnose_operation_support(build_graph().operations[0]):
        print(
            "support "
            f"{diagnostic.backend_name}:{diagnostic.operation_name} "
            f"{diagnostic.reason}"
        )
    print("conformance_passed=" + str(report.conformance.passed).lower())
    print(report.compiled.dump_runtime_plan())
    print()
    print(report.lowered.artifact)


if __name__ == "__main__":
    main()
