from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_backend_equivalence_portfolio import (
    build_backend_equivalence_portfolio_report,
)
from examples.runtime_backend_equivalence_portfolio_policy import (
    build_backend_equivalence_portfolio_policy_report,
)
from tuc import (
    MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REQUIREMENTS,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeBackendEquivalencePortfolioRequirement,
    assert_runtime_backend_equivalence_portfolio_matches_policy,
    build_default_runtime_backend_equivalence_portfolio_policy_report,
    dump_runtime_backend_equivalence_portfolio_policy_report,
    runtime_backend_equivalence_portfolio_policy_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/runtime_backend_equivalence/portfolio_policy_report.json"
)
SCHEMA_PATH = Path(
    "schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json"
)


def test_runtime_backend_equivalence_portfolio_policy_matches_current_portfolio() -> None:
    policy = build_backend_equivalence_portfolio_policy_report()
    portfolio = build_backend_equivalence_portfolio_report()

    assert policy.policy_contract == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT
    assert policy.policy_id == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID
    assert policy.policy_status == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS
    assert policy.artifact_status == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS
    )
    assert policy.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert policy.trusted_executor_registry == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert policy.requirement_count == 3
    assert policy.required_candidate_backend_families == (
        "systolic-sim",
        "vector-sim",
    )
    assert tuple(requirement.slice_id for requirement in policy.requirements) == (
        "runtime_backend_equivalence",
        "runtime_vector_backend_equivalence",
        "runtime_mixed_backend_equivalence",
    )
    assert (
        assert_runtime_backend_equivalence_portfolio_matches_policy(
            policy,
            portfolio,
        )
        is portfolio
    )
    assert tuple(runtime_backend_equivalence_portfolio_policy_report_to_dict(policy)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "policy_contract",
        "policy_id",
        "policy_metadata_digest",
        "policy_status",
        "portfolio_id",
        "raw_value_policy",
        "required_candidate_backend_families",
        "requirement_count",
        "requirements",
        "schema_version",
        "trusted_executor_registry",
    )


def test_runtime_backend_equivalence_portfolio_policy_dump_matches_golden() -> None:
    assert dump_runtime_backend_equivalence_portfolio_policy_report(
        build_backend_equivalence_portfolio_policy_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_backend_equivalence_portfolio_policy_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_backend_equivalence_portfolio_policy.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_backend_equivalence_portfolio_policy.data_only.v0" in (
        completed.stdout
    )
    assert '"runtime_backend_equivalence_portfolio_policy"' in completed.stdout
    assert '"runtime_backend_equivalence"' in completed.stdout
    assert '"runtime_vector_backend_equivalence"' in completed.stdout
    assert '"runtime_mixed_backend_equivalence"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_runtime_backend_equivalence_portfolio_policy_rejects_missing_slice() -> None:
    policy = build_default_runtime_backend_equivalence_portfolio_policy_report()
    portfolio = build_backend_equivalence_portfolio_report()
    truncated = replace(portfolio, slices=portfolio.slices[:-1], issues=())

    with pytest.raises(AssertionError, match="slice_count_mismatch"):
        assert_runtime_backend_equivalence_portfolio_matches_policy(
            policy,
            truncated,
        )


def test_runtime_backend_equivalence_portfolio_policy_rejects_wrong_sequence() -> None:
    policy = build_default_runtime_backend_equivalence_portfolio_policy_report()
    portfolio = build_backend_equivalence_portfolio_report()
    forged = replace(
        portfolio,
        slices=(
            replace(
                portfolio.slices[0],
                candidate_backend_sequence=("vector-sim", "reference-cpu"),
            ),
            *portfolio.slices[1:],
        ),
        issues=(),
    )

    with pytest.raises(AssertionError, match="candidate_backend_sequence_mismatch"):
        assert_runtime_backend_equivalence_portfolio_matches_policy(policy, forged)


def test_runtime_backend_equivalence_portfolio_policy_rejects_forbidden_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeBackendEquivalencePortfolioRequirement(
            slice_id="python_source",
            graph_name="runtime_backend_equivalence",
            baseline_run_id="reference_cpu",
            candidate_run_id="systolic_sim",
            baseline_backend_sequence=("reference-cpu",),
            candidate_backend_sequence=("systolic-sim",),
        )


def test_runtime_backend_equivalence_portfolio_policy_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT
    )
    assert schema["properties"]["policy_id"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID
    )
    assert schema["properties"]["policy_status"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["properties"]["requirements"]["maxItems"] == (
        MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REQUIREMENTS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_backend_equivalence_portfolio_policy_schema_fails_closed() -> None:
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
        "tensor_values",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["requirement"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_backend_equivalence_portfolio_policy_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_REPORT_SCHEMA_VERSION
    )
    assert golden["artifact_status"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ARTIFACT_STATUS
    )
    assert golden["policy_contract"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_CONTRACT
    )
    assert golden["policy_id"] == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_ID
    assert golden["policy_status"] == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_POLICY_STATUS
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["required_candidate_backend_families"] == [
        "systolic-sim",
        "vector-sim",
    ]
    assert golden["requirement_count"] == len(golden["requirements"]) == 3


def test_runtime_backend_equivalence_portfolio_policy_schema_is_referenced() -> None:
    schema_path = (
        "schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json"
    )

    for path in (
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0145-runtime-backend-equivalence-portfolio-policy.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
