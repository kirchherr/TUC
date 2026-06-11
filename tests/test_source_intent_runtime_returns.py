from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from examples.source_intent_return_semantics import build_source_intent_return_data
from examples.source_intent_runtime_returns import build_report, run_evidence, runtime_inputs
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_RETURN_POLICY,
    SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT,
    SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS,
    SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT,
    SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION,
    ComputeGraph,
    IRStage,
    SourceIntentRuntimeReturnBinding,
    SourceIntentRuntimeReturnsError,
    build_source_intent_runtime_returns_report,
    compile_graph,
    dump_runtime_output_contract_report,
    dump_runtime_public_output_bundle_report,
    dump_runtime_reference_correctness_report,
    dump_source_intent_runtime_returns_report,
    execute_graph,
    source_intent_from_mapping,
    source_intent_runtime_returns_report_to_dict,
)
from tuc.backends import LinearAlgebraSimulatorBackend

GOLDEN_PATH = Path("tests/golden/frontend/source_intent_runtime_returns_report.json")
SCHEMA_PATH = Path("schemas/source_intent_runtime_returns_report.v0.schema.json")


def test_source_intent_runtime_returns_resolves_public_outputs() -> None:
    evidence = run_evidence()
    report = evidence.runtime_returns

    assert report.schema_version == SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION
    assert report.artifact_status == SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS
    assert report.runtime_returns_contract == SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT
    assert report.source_intent_contract == SOURCE_INTENT_IR_CONTRACT
    assert report.return_semantics_contract == SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT
    assert report.return_policy == SOURCE_INTENT_RETURN_POLICY
    assert report.output_contract == RUNTIME_OUTPUT_CONTRACT
    assert report.public_output_bundle_contract == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.alias_policy == RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report.passed
    assert report.return_count == 1
    assert tuple(binding.public_name for binding in report.bindings) == ("api_y",)
    assert tuple(binding.tensor_name for binding in report.bindings) == ("y",)
    assert report.terminal_tensor_names == ("y",)
    assert report.public_output_names == ("api_y",)
    assert evidence.output_contract.passed
    assert evidence.public_output_bundle.passed

    values = evidence.public_output_bundle.values
    expected = runtime_inputs()["a"] @ runtime_inputs()["b"]
    np.testing.assert_allclose(values["api_y"], expected)
    assert not values["api_y"].flags.writeable

    assert tuple(source_intent_runtime_returns_report_to_dict(report)) == (
        "alias_policy",
        "artifact_status",
        "bindings",
        "bundle_metadata_digest",
        "contract_metadata_digest",
        "executor_contract",
        "graph_name",
        "link_metadata_digest",
        "module_name",
        "output_contract",
        "output_contract_passed",
        "passed",
        "public_output_bundle_contract",
        "public_output_bundle_passed",
        "public_output_count",
        "public_output_names",
        "raw_value_policy",
        "return_count",
        "return_policy",
        "return_semantics_contract",
        "runtime_blocked_execution_surfaces",
        "runtime_returns_contract",
        "schema_version",
        "source_intent_blocked_compiler_outputs",
        "source_intent_blocked_execution_surfaces",
        "source_intent_contract",
        "terminal_tensor_names",
    )


def test_source_intent_runtime_returns_dump_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert dump_source_intent_runtime_returns_report(run_evidence().runtime_returns) == (
        build_report()
    )


@pytest.mark.parametrize(
    ("fixture_path", "artifact_builder"),
    (
        (
            Path("hac_ir") / "source_intent_return_mlp.txt",
            lambda: run_evidence().compiled.dump(IRStage.HAC_IR),
        ),
        (
            Path("runtime_plans") / "source_intent_return_mlp.txt",
            lambda: run_evidence().compiled.dump_runtime_plan(),
        ),
        (
            Path("compiler_decisions") / "source_intent_return_mlp.txt",
            lambda: run_evidence().compiled.dump_decision_report(),
        ),
        (
            Path("execution_readiness") / "source_intent_return_mlp.txt",
            lambda: run_evidence().readiness.dump(),
        ),
        (
            Path("execution_traces") / "source_intent_return_mlp.txt",
            lambda: run_evidence().execution.trace.dump(),
        ),
        (
            Path("runtime_output_contract") / "source_intent_return_mlp.json",
            lambda: dump_runtime_output_contract_report(
                run_evidence().output_contract
            ).rstrip("\n"),
        ),
        (
            Path("runtime_public_output_bundle") / "source_intent_return_mlp.json",
            lambda: dump_runtime_public_output_bundle_report(
                run_evidence().public_output_bundle
            ).rstrip("\n"),
        ),
        (
            Path("runtime_reference_correctness") / "source_intent_return_mlp.json",
            lambda: dump_runtime_reference_correctness_report(
                run_evidence().reference_correctness
            ).rstrip("\n"),
        ),
    ),
)
def test_source_intent_runtime_returns_artifacts_match_goldens(
    fixture_path: Path,
    artifact_builder: Any,
) -> None:
    expected = (Path("tests/golden") / fixture_path).read_text(
        encoding="utf-8"
    ).rstrip("\n")

    assert artifact_builder() == expected


def test_source_intent_runtime_returns_example_runs_without_raw_values() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_intent_runtime_returns.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["runtime_returns_contract"] == SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT
    assert payload["passed"] is True
    assert payload["public_output_names"] == ["api_y"]
    _assert_forbidden_keys_absent(payload)
    assert "python_source" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_values" not in completed.stdout


def test_source_intent_runtime_returns_rejects_missing_returns() -> None:
    evidence = run_evidence()
    payload = build_source_intent_return_data()
    payload.pop("returns")
    module = source_intent_from_mapping(payload)

    with pytest.raises(ValueError, match="require explicit returns"):
        build_source_intent_runtime_returns_report(
            module,
            evidence.graph,
            evidence.execution,
        )


def test_source_intent_runtime_returns_rejects_optional_returns() -> None:
    evidence = run_evidence()
    payload = build_source_intent_return_data()
    returns = payload["returns"]
    assert isinstance(returns, list)
    returns[0]["required"] = False
    module = source_intent_from_mapping(payload)

    with pytest.raises(SourceIntentRuntimeReturnsError, match="required returns"):
        build_source_intent_runtime_returns_report(
            module,
            evidence.graph,
            evidence.execution,
        )


def test_source_intent_runtime_returns_rejects_graph_name_mismatch() -> None:
    evidence = run_evidence()
    other_graph = ComputeGraph(
        name="other_graph",
        operations=evidence.graph.operations,
        metadata=dict(evidence.graph.metadata),
    )

    with pytest.raises(SourceIntentRuntimeReturnsError, match="names must match"):
        build_source_intent_runtime_returns_report(
            evidence.module,
            other_graph,
            evidence.execution,
        )


def test_source_intent_runtime_returns_rejects_failed_output_contract() -> None:
    evidence = run_evidence()
    truncated_graph = ComputeGraph(
        name=evidence.module.name,
        operations=evidence.graph.operations[:-1],
        metadata=dict(evidence.graph.metadata),
    )
    compiled = compile_graph(
        truncated_graph,
        [LinearAlgebraSimulatorBackend().capability],
    )
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        runtime_inputs(),
    )

    with pytest.raises(SourceIntentRuntimeReturnsError, match="output contract failed"):
        build_source_intent_runtime_returns_report(
            evidence.module,
            compiled.hac_ir.graph,
            execution,
        )


def test_source_intent_runtime_binding_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        SourceIntentRuntimeReturnBinding(
            public_name="python_source",
            tensor_name="y",
        )


def test_source_intent_runtime_returns_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/source_intent_runtime_returns_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS
    )
    assert schema["properties"]["runtime_returns_contract"]["const"] == (
        SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT
    )
    assert schema["properties"]["source_intent_contract"]["const"] == (
        SOURCE_INTENT_IR_CONTRACT
    )
    assert schema["properties"]["return_semantics_contract"]["const"] == (
        SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT
    )
    assert schema["properties"]["output_contract"]["const"] == RUNTIME_OUTPUT_CONTRACT
    assert schema["properties"]["public_output_bundle_contract"]["const"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert [
        item["const"]
        for item in schema["$defs"]["runtime_blocked_execution_surfaces"][
            "prefixItems"
        ]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_source_intent_runtime_returns_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_value",
        "tensor_values",
        "value",
        "values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["binding"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "tensor_values" in schema["$defs"]["report_text"]["not"]["enum"]


def test_source_intent_runtime_returns_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS
    assert golden["runtime_returns_contract"] == SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT
    assert golden["source_intent_contract"] == SOURCE_INTENT_IR_CONTRACT
    assert golden["return_semantics_contract"] == SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT
    assert golden["output_contract"] == RUNTIME_OUTPUT_CONTRACT
    assert golden["public_output_bundle_contract"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["passed"] is True
    assert golden["output_contract_passed"] is True
    assert golden["public_output_bundle_passed"] is True
    assert golden["return_count"] == 1
    assert golden["public_output_count"] == 1
    assert golden["bindings"] == [
        {
            "public_name": "api_y",
            "required": True,
            "tensor_name": "y",
        }
    ]
    assert golden["public_output_names"] == ["api_y"]
    assert golden["terminal_tensor_names"] == ["y"]


def test_source_intent_runtime_returns_docs_are_referenced() -> None:
    docs_path = "docs/SOURCE_INTENT_RUNTIME_RETURNS.md"
    schema_path = "schemas/source_intent_runtime_returns_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_INTENT_RETURN_SEMANTICS.md"),
        Path("docs/RUNTIME_OUTPUT_CONTRACT.md"),
        Path("rfcs/0117-source-intent-runtime-returns.md"),
    ):
        text = path.read_text(encoding="utf-8")
        if path in (
            Path("docs/SOURCE_INTENT_RETURN_SEMANTICS.md"),
            Path("docs/RUNTIME_OUTPUT_CONTRACT.md"),
        ):
            assert "SOURCE_INTENT_RUNTIME_RETURNS.md" in text
        else:
            assert docs_path in text
        assert schema_path in text


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_forbidden_keys_absent(value: object) -> None:
    forbidden_keys = {
        "file_path",
        "generated_code",
        "host_path",
        "python_source",
        "raw_output_value",
        "raw_tensor_value",
        "source_text",
        "tensor_value",
        "tensor_values",
        "value",
        "values",
    }
    if isinstance(value, dict):
        assert not (set(value) & forbidden_keys)
        for item in value.values():
            _assert_forbidden_keys_absent(item)
    elif isinstance(value, list):
        for item in value:
            _assert_forbidden_keys_absent(item)


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
