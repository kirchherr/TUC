"""External-style backend author path for TUC Backend API v0.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tuc.backends.author_readiness import (
    BackendAuthorReadinessCheck,
    BackendAuthorReadinessReport,
    build_backend_author_readiness_report,
    dump_backend_author_readiness_report,
)
from tuc.backends.base import BackendCapability, LoweringResult
from tuc.backends.claim_review import (
    ManifestClaimReviewInput,
    ManifestClaimReviewReport,
    build_manifest_claim_review_report,
    dump_manifest_claim_review_report,
)
from tuc.backends.conformance import (
    BackendConformanceReport,
    assert_backend_conformance,
    dump_backend_conformance_report,
)
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

    claim_review: ManifestClaimReviewReport
    registry: BackendRegistry
    compiled: CompilationResult
    conformance: BackendConformanceReport
    lowered: LoweringResult
    readiness: BackendAuthorReadinessReport


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
    """Run claim review, registry, compiler planning, conformance, and lowering."""

    claim_review = build_external_backend_claim_review(manifest_path)
    _assert_author_manifest_accepted(claim_review)
    registry = BackendRegistry.from_manifest_paths([manifest_path])
    backend = ExternalVectorBackend(registry.capability("external-vector"))
    graph = build_graph()
    compiled = compile_graph(graph, registry.capabilities())
    conformance = assert_backend_conformance(backend)
    assigned_graph = assigned_graph_for_backend(compiled, backend.capability.name)
    lowered = backend.lower(assigned_graph)
    readiness = build_external_backend_author_readiness_report(
        claim_review=claim_review,
        registry=registry,
        compiled=compiled,
        conformance=conformance,
        lowered=lowered,
        assigned_graph=assigned_graph,
    )
    return ExternalBackendAuthorReport(
        claim_review=claim_review,
        registry=registry,
        compiled=compiled,
        conformance=conformance,
        lowered=lowered,
        readiness=readiness,
    )


def main() -> None:
    report = run_external_backend_author_path()

    print("manifest_claim_review_passed=" + str(report.claim_review.passed).lower())
    print(dump_manifest_claim_review_report(report.claim_review), end="")
    print("registered_backends=" + ",".join(report.registry.names()))
    for diagnostic in report.registry.diagnose_operation_support(build_graph().operations[0]):
        print(
            "support "
            f"{diagnostic.backend_name}:{diagnostic.operation_name} "
            f"{diagnostic.reason}"
        )
    print("conformance_passed=" + str(report.conformance.passed).lower())
    print(dump_backend_conformance_report(report.conformance), end="")
    print(report.compiled.dump_runtime_plan())
    print()
    print(report.lowered.artifact)
    print()
    print("backend_author_readiness_ready=" + str(report.readiness.ready).lower())
    print(dump_backend_author_readiness_report(report.readiness), end="")


def build_external_backend_claim_review(
    manifest_path: Path = MANIFEST_PATH,
) -> ManifestClaimReviewReport:
    """Return the author-path manifest claim review report."""

    return build_manifest_claim_review_report(
        (
            ManifestClaimReviewInput(
                manifest_id="external_vector_backend",
                path=manifest_path,
                expected_review_status="accepted",
            ),
        )
    )


def _assert_author_manifest_accepted(report: ManifestClaimReviewReport) -> None:
    if not report.passed:
        raise ValueError("external backend manifest claim review failed")
    case = report.cases[0]
    if case.observed_review_status != "accepted":
        raise ValueError("external backend manifest was not accepted by claim review")


def build_external_backend_author_readiness_report(
    *,
    claim_review: ManifestClaimReviewReport,
    registry: BackendRegistry,
    compiled: CompilationResult,
    conformance: BackendConformanceReport,
    lowered: LoweringResult,
    assigned_graph: ComputeGraph,
) -> BackendAuthorReadinessReport:
    """Summarize the external backend author path as one readiness report."""

    backend_name = "external-vector"
    manifest_id = "external_vector_backend"
    assignment_backend = compiled.partition_plan.backend_for("activation")
    lowered_assigned_ops = "_".join(assigned_graph.operation_names())
    checks = (
        BackendAuthorReadinessCheck(
            check_name="manifest_claim_review",
            status=(
                "passed"
                if claim_review.passed
                and claim_review.cases[0].observed_review_status == "accepted"
                else "failed"
            ),
            evidence_id="external_vector_author_claim_review",
            detail=claim_review.cases[0].observed_review_status,
        ),
        BackendAuthorReadinessCheck(
            check_name="manifest_registry",
            status="passed" if registry.names() == (backend_name,) else "failed",
            evidence_id="external_vector_registry",
            detail="registered",
        ),
        BackendAuthorReadinessCheck(
            check_name="compiler_assignment",
            status="passed" if assignment_backend == backend_name else "failed",
            evidence_id="external_backend_author_demo",
            detail=f"activation_{assignment_backend}",
        ),
        BackendAuthorReadinessCheck(
            check_name="backend_conformance",
            status="passed" if conformance.passed else "failed",
            evidence_id="external_vector_conformance_report",
            detail=f"cases_{len(conformance.checked_cases)}",
        ),
        BackendAuthorReadinessCheck(
            check_name="assigned_subgraph_lowering",
            status=(
                "passed"
                if lowered.backend_name == backend_name
                and lowered.graph_name == assigned_graph.name
                else "failed"
            ),
            evidence_id="external_vector_assigned_lowering",
            detail=f"lowered_{lowered_assigned_ops}",
        ),
    )
    return build_backend_author_readiness_report(
        backend_name=backend_name,
        manifest_id=manifest_id,
        checks=checks,
    )


if __name__ == "__main__":
    main()
