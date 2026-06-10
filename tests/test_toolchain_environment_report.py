from __future__ import annotations

import json

import pytest

from tuc import (
    TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
    TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
    TOOLCHAIN_ENVIRONMENT_DEFAULT_ISSUES,
    TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
    ToolchainComponent,
    build_toolchain_environment_report,
    dump_toolchain_environment_report,
    toolchain_environment_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_toolchain_environment_report_blocks_without_components() -> None:
    report = build_toolchain_environment_report("blocked_toolchain_environment")
    payload = toolchain_environment_report_to_dict(report)

    assert payload["schema_version"] == TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["toolchain_environment_ready"] is False
    assert payload["components"] == []
    assert payload["issues"] == list(TOOLCHAIN_ENVIRONMENT_DEFAULT_ISSUES)


def test_toolchain_environment_report_tracks_components() -> None:
    report = build_toolchain_environment_report(
        "phase1_toolchain_environment_candidate",
        components=(
            ToolchainComponent(
                component_id="python_runtime",
                component_kind="python_runtime",
                version_id="python_3.11",
                provenance_id="docker_dev_container",
                component_digest=_DIGEST,
            ),
        ),
    )
    payload = toolchain_environment_report_to_dict(report)

    assert payload["toolchain_environment_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["components"] == [
        {
            "component_digest": _DIGEST,
            "component_id": "python_runtime",
            "component_kind": "python_runtime",
            "provenance_id": "docker_dev_container",
            "version_id": "python_3.11",
        }
    ]
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_toolchain_environment_report_tracks_missing_digest() -> None:
    report = build_toolchain_environment_report(
        "phase1_toolchain_environment_candidate",
        components=(
            ToolchainComponent(
                component_id="python_runtime",
                component_kind="python_runtime",
                version_id="python_3.11",
                provenance_id="docker_dev_container",
            ),
        ),
    )
    payload = toolchain_environment_report_to_dict(report)

    assert payload["toolchain_environment_ready"] is False
    assert "toolchain_component_digest_not_supplied" in payload["issues"]


def test_toolchain_environment_report_is_json_serializable() -> None:
    report = build_toolchain_environment_report("blocked_toolchain_environment")
    payload = json.loads(dump_toolchain_environment_report(report))

    assert payload["schema_version"] == "tuc.toolchain_environment_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_toolchain_environment_rejects_duplicate_components() -> None:
    component = ToolchainComponent(
        component_id="same_component",
        component_kind="python_runtime",
        version_id="python_3.11",
        provenance_id="docker_dev_container",
    )

    with pytest.raises(ValueError, match="duplicate toolchain component id"):
        build_toolchain_environment_report(
            "duplicate_toolchain_component",
            components=(component, component),
        )


def test_toolchain_environment_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported toolchain component kind"):
        build_toolchain_environment_report(
            "bad_kind",
            components=(
                ToolchainComponent(
                    component_id="bad_component",
                    component_kind="host_env_dump",
                    version_id="dump_v0",
                    provenance_id="local_host",
                ),
            ),
        )


def test_toolchain_environment_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="provenance_id"):
        build_toolchain_environment_report(
            "bad_provenance_path",
            components=(
                ToolchainComponent(
                    component_id="python_runtime",
                    component_kind="python_runtime",
                    version_id="python_3.11",
                    provenance_id="C:/Python/python.exe",
                ),
            ),
        )


def test_toolchain_environment_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="component_digest"):
        build_toolchain_environment_report(
            "bad_digest",
            components=(
                ToolchainComponent(
                    component_id="python_runtime",
                    component_kind="python_runtime",
                    version_id="python_3.11",
                    provenance_id="docker_dev_container",
                    component_digest="sha256:ABCDEF",
                ),
            ),
        )
