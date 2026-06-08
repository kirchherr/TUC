from __future__ import annotations

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    TRITON_METADATA_INTAKE_CONTRACT,
    TRITON_METADATA_SCHEMA_VERSION,
    TritonKernelMetadata,
)
from tuc.ir import OperationKind


def test_triton_metadata_mapping_builds_compute_graph() -> None:
    graph = _metadata().to_compute_graph()

    assert graph.name == "triton_metadata_mlp"
    assert graph.metadata["frontend.adapter"] == "triton_metadata.v0"
    assert graph.metadata["frontend.schema_version"] == TRITON_METADATA_SCHEMA_VERSION
    assert graph.metadata["frontend.intake_contract"] == TRITON_METADATA_INTAKE_CONTRACT
    assert graph.operations[0].kind is OperationKind.MATMUL
    assert graph.operations[0].attributes["prefer_analog_linear"] is True
    assert graph.operations[0].attributes["max_error_budget"] == 0.02
    assert graph.operations[1].attributes["semantic"] == "gelu_approx"


def test_triton_metadata_graph_runs_through_pipeline() -> None:
    graph = _metadata().to_compute_graph()
    result = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    assert result.partition_plan.backend_for("projection") == "linear-sim"
    assert result.partition_plan.backend_for("activation") == "gpu"
    assert result.tlir.graph.metadata["frontend.adapter"] == "triton_metadata.v0"


def test_triton_metadata_intake_report_is_deterministic() -> None:
    report = _metadata().intake_report()

    assert report.dump() == (
        "triton.intake_report @triton_metadata_mlp {\n"
        '  schema_version = "triton_metadata.v0"\n'
        '  intake_contract = "triton_intake.execution_free.v0"\n'
        "  tensor_count = 4\n"
        "  operation_count = 2\n"
        '  operation_kinds = "matmul,elementwise"\n'
        "  blocked_execution_surfaces = "
        '"bytecode_inspection,device_access,dynamic_library_loading,'
        "generated_artifact_execution,jit_execution,network_access,python_import,"
        'subprocess_execution"\n'
        "}"
    )


def test_triton_metadata_rejects_unknown_schema_version() -> None:
    metadata = _metadata_dict()
    metadata["schema_version"] = "triton_metadata.v99"

    with pytest.raises(ValueError, match="schema_version"):
        TritonKernelMetadata.from_mapping(metadata)


def test_triton_metadata_rejects_reserved_tuc_attributes() -> None:
    metadata = _metadata_dict()
    operation = metadata["operations"][0]
    if type(operation) is not dict:
        raise AssertionError("test fixture is malformed")
    operation["attributes"] = {"tuc.bytes_read": 1}

    with pytest.raises(ValueError, match="reserved tuc"):
        TritonKernelMetadata.from_mapping(metadata)


@pytest.mark.parametrize(
    "key,value",
    [
        ("import_module", "attacker.kernel"),
        ("python_source", "@triton.jit\ndef kernel(): pass"),
        ("dynamic_library", "kernel.dll"),
        ("device_path", "/dev/nvidia0"),
        ("url", "https://example.invalid/kernel"),
    ],
)
def test_triton_metadata_rejects_execution_surface_metadata(
    key: str,
    value: object,
) -> None:
    metadata = _metadata_dict()
    metadata["metadata"] = {key: value}

    with pytest.raises(ValueError, match="forbidden execution surface key"):
        TritonKernelMetadata.from_mapping(metadata)


def test_triton_metadata_rejects_execution_surface_operation_attributes() -> None:
    metadata = _metadata_dict()
    operation = metadata["operations"][1]
    if type(operation) is not dict:
        raise AssertionError("test fixture is malformed")
    operation["attributes"] = {"python_module": "attacker.kernel"}

    with pytest.raises(ValueError, match="forbidden execution surface key"):
        TritonKernelMetadata.from_mapping(metadata)


def test_triton_metadata_rejects_unknown_tensor_reference() -> None:
    metadata = _metadata()
    operation = metadata.operations[0]
    bad_metadata = TritonKernelMetadata(
        name=metadata.name,
        tensors=metadata.tensors,
        operations=(
            type(operation)(
                name=operation.name,
                kind=operation.kind,
                inputs=("missing",),
                outputs=operation.outputs,
                hints=operation.hints,
            ),
        ),
    )

    with pytest.raises(ValueError, match="unknown input tensor"):
        bad_metadata.to_compute_graph()


def test_triton_metadata_rejects_unknown_mapping_fields() -> None:
    metadata = _metadata_dict()
    metadata["import_module"] = "do_not_import"

    with pytest.raises(ValueError, match="unsupported keys"):
        TritonKernelMetadata.from_mapping(metadata)


def test_triton_metadata_rejects_custom_mapping_subclass() -> None:
    class CustomMapping(dict[str, object]):
        pass

    with pytest.raises(TypeError, match="plain mapping"):
        TritonKernelMetadata.from_mapping(CustomMapping(_metadata_dict()))


def _metadata() -> TritonKernelMetadata:
    return TritonKernelMetadata.from_mapping(_metadata_dict())


def _metadata_dict() -> dict[str, object]:
    return {
        "name": "triton_metadata_mlp",
        "tensors": [
            {"name": "a", "shape": [32, 64], "dtype": "float32"},
            {"name": "b", "shape": [64, 16], "dtype": "float32"},
            {"name": "c", "shape": [32, 16], "dtype": "float32"},
            {"name": "y", "shape": [32, 16], "dtype": "float32"},
        ],
        "operations": [
            {
                "name": "projection",
                "kind": "matmul",
                "inputs": ["a", "b"],
                "outputs": ["c"],
                "hints": {
                    "prefer_analog_linear": True,
                    "max_error_budget": 0.02,
                },
            },
            {
                "name": "activation",
                "kind": "elementwise",
                "inputs": ["c"],
                "outputs": ["y"],
                "attributes": {"semantic": "gelu_approx"},
            },
        ],
        "schema_version": TRITON_METADATA_SCHEMA_VERSION,
        "metadata": {"frontend.source": "triton-like-metadata"},
    }
