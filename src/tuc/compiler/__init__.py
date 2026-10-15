"""Compiler pipeline entry points."""

from tuc.compiler.decisions import (
    CompilerDecisionReport,
    OperationDecisionReport,
    build_compiler_decision_report,
)
from tuc.compiler.lowering import lower_hac_to_hs, lower_tlir_to_hac
from tuc.compiler.movement import (
    MOVEMENT_MODEL_VERSION,
    annotate_graph_movement,
    estimate_operation_movement,
    summarize_graph_movement,
)
from tuc.compiler.pipeline import CompilationResult, CompilerPipeline, compile_graph

# isort: split
# Load the explicit frontend facade after the existing pipeline exports: the
# frontend conformance module imports compile_graph during package startup.
from tuc.compiler.bounded_c11 import (
    BoundedC11Entrypoint,
    emit_bounded_c11_entrypoint,
    validate_bounded_c11_entrypoint,
)
from tuc.compiler.bounded_model_application import (
    MODEL_APPLICATION_RESULT_CONTRACT,
    BoundedModelApplication,
    BoundedModelApplicationError,
    BoundedModelApplicationOutput,
    BoundedModelApplicationResult,
    decode_bounded_model_application_response,
    prepare_bounded_model_application,
    validate_bounded_model_application_result,
)
from tuc.compiler.bounded_model_artifact_bundle import (
    MODEL_ARTIFACT_BUNDLE_CONTRACT,
    BoundedModelArtifactBundle,
    BoundedModelArtifactBundleError,
    create_bounded_model_artifact_bundle,
    inspect_bounded_model_artifact_bundle,
    validate_bounded_model_artifact_bundle,
)
from tuc.compiler.bounded_model_artifact_request import (
    MODEL_ARTIFACT_REQUEST_CONTRACT,
    BoundedModelArtifactRequest,
    BoundedModelArtifactRequestError,
    BoundedModelArtifactRequestInput,
    create_bounded_model_artifact_request,
    inspect_bounded_model_artifact_request,
    validate_bounded_model_artifact_request,
)
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    BoundedSourceCompilation,
    BoundedTensorBinding,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)

__all__ = [
    "MODEL_APPLICATION_RESULT_CONTRACT",
    "BoundedModelApplication",
    "BoundedModelApplicationError",
    "BoundedModelApplicationOutput",
    "BoundedModelApplicationResult",
    "prepare_bounded_model_application",
    "decode_bounded_model_application_response",
    "validate_bounded_model_application_result",
    "BoundedBackendBinding",
    "BoundedModelArtifactBundle",
    "BoundedModelArtifactBundleError",
    "BoundedModelArtifactRequest",
    "BoundedModelArtifactRequestError",
    "BoundedModelArtifactRequestInput",
    "BoundedC11Entrypoint",
    "BoundedSourceCompilation",
    "BoundedTensorBinding",
    "CompilationResult",
    "CompilerDecisionReport",
    "CompilerPipeline",
    "MOVEMENT_MODEL_VERSION",
    "MODEL_ARTIFACT_BUNDLE_CONTRACT",
    "MODEL_ARTIFACT_REQUEST_CONTRACT",
    "OperationDecisionReport",
    "annotate_graph_movement",
    "build_compiler_decision_report",
    "compile_graph",
    "create_bounded_model_artifact_bundle",
    "create_bounded_model_artifact_request",
    "compile_bounded_source_intent",
    "estimate_operation_movement",
    "emit_bounded_c11_entrypoint",
    "lower_hac_to_hs",
    "lower_tlir_to_hac",
    "inspect_bounded_model_artifact_bundle",
    "inspect_bounded_model_artifact_request",
    "summarize_graph_movement",
    "validate_bounded_source_compilation",
    "validate_bounded_c11_entrypoint",
    "validate_bounded_model_artifact_bundle",
    "validate_bounded_model_artifact_request",
]
