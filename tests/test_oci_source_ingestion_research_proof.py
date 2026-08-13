from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

import examples.oci_source_ingestion_research_proof as proof_module
from examples.oci_source_ingestion_research_proof import (
    _EXPECTED_SECURITY,
    EXPECTED_SOURCE_INTENT,
    OCI_SOURCE_INGESTION_BASE_IMAGE,
    OCI_SOURCE_INGESTION_PROOF_CONTRACT,
    OCI_SOURCE_INGESTION_PROOF_SCHEMA_VERSION,
    OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
    _build_rejection_request,
    _build_worker_request,
    _canonical_json,
    _digest_payload,
    _validate_compose_config,
    _validate_rejection_response,
    _validate_worker_response,
    assert_oci_source_ingestion_research_proof_report,
    build_oci_source_ingestion_research_proof_report,
    build_report,
)

SCHEMA_PATH = Path(
    "schemas/oci_source_ingestion_research_proof_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
)
DOC_PATH = Path("docs/OCI_SOURCE_INGESTION_RESEARCH_WORKER.md")
RFC_PATH = Path("rfcs/0289-oci-source-ingestion-research-worker.md")


def _accepted_worker_response() -> dict[str, object]:
    _, request_digest = _build_worker_request()
    source_intent_digest = _digest_payload(EXPECTED_SOURCE_INTENT)
    return {
        "ingress_report": {
            "ingress_contract": (
                "source_to_intent_research_kernel_ingress.execution_free.v0"
            ),
            "kernel_name": "matmul_elementwise",
            "module_digest": proof_module._digest_text(proof_module.MODULE_SOURCE),
            "operation_families": ["elementwise", "matmul"],
            "source_intent_digest": source_intent_digest,
            "source_name": "research_matmul_elementwise",
        },
        "protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "request_digest": request_digest,
        "security": dict(_EXPECTED_SECURITY),
        "source_intent_payload": EXPECTED_SOURCE_INTENT,
        "status": "accepted",
    }


def _rendered_compose_config() -> dict[str, object]:
    contract = proof_module._COMPOSE_CONTRACT
    service = {
        "build": {
            "context": str(Path.cwd().resolve()),
            "dockerfile": contract["dockerfile"],
        },
        "cap_drop": contract["cap_drop"],
        "cpus": contract["cpus"],
        "environment": contract["environment"],
        "image": contract["image"],
        "ipc": contract["ipc"],
        "mem_limit": str(contract["mem_limit"]),
        "network_mode": contract["network_mode"],
        "pids_limit": contract["pids_limit"],
        "platform": contract["platform"],
        "read_only": contract["read_only"],
        "security_opt": contract["security_opt"],
        "shm_size": str(contract["shm_size"]),
        "tmpfs": contract["tmpfs"],
        "user": contract["user"],
        "working_dir": contract["working_dir"],
    }
    return {"services": {proof_module.OCI_SOURCE_INGESTION_SERVICE: service}}


def _rejected_worker_response() -> dict[str, object]:
    _, request_digest = _build_rejection_request()
    return {
        "protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "reason_code": "source_rejected",
        "request_digest": request_digest,
        "status": "rejected",
    }


def _mock_worker(request: bytes) -> dict[str, object]:
    if b"oci_malicious_probe" in request:
        return _rejected_worker_response()
    return _accepted_worker_response()


def test_oci_worker_request_is_bounded_and_digest_bound() -> None:
    request, digest = _build_worker_request()
    payload = json.loads(request.decode("utf-8"))

    assert len(request) <= proof_module._MAX_REQUEST_BYTES
    assert payload["protocol"] == OCI_SOURCE_INGESTION_WORKER_PROTOCOL
    assert payload["request_digest"] == digest
    assert digest == _digest_payload(payload["payload"])
    assert payload["payload"]["module_source"] == proof_module.MODULE_SOURCE


def test_oci_worker_response_requires_all_kernel_invariants() -> None:
    response = _accepted_worker_response()
    _, request_digest = _build_worker_request()

    assert _validate_worker_response(
        response,
        expected_request_digest=request_digest,
    ) == _digest_payload(EXPECTED_SOURCE_INTENT)

    security = dict(_EXPECTED_SECURITY)
    security["no_new_privileges"] = False
    response["security"] = security
    with pytest.raises(ValueError, match="security invariant drift"):
        _validate_worker_response(response, expected_request_digest=request_digest)


def test_oci_worker_response_rejects_source_intent_drift() -> None:
    response = _accepted_worker_response()
    _, request_digest = _build_worker_request()
    source_intent = dict(EXPECTED_SOURCE_INTENT)
    source_intent["name"] = "tampered"
    response["source_intent_payload"] = source_intent

    with pytest.raises(ValueError, match="Source Intent drift"):
        _validate_worker_response(response, expected_request_digest=request_digest)


def test_oci_worker_malicious_source_rejection_is_source_free() -> None:
    response = _rejected_worker_response()
    _, request_digest = _build_rejection_request()

    _validate_rejection_response(
        response,
        expected_request_digest=request_digest,
    )
    encoded = _canonical_json(response)
    assert "__import__" not in encoded
    assert "pathlib" not in encoded
    assert "socket" not in encoded
    assert "/tmp/tuc_probe" not in encoded


def test_oci_compose_contract_rejects_network_or_volume_drift() -> None:
    config = _rendered_compose_config()
    assert _validate_compose_config(config) == proof_module._COMPOSE_CONTRACT

    services = config["services"]
    assert isinstance(services, dict)
    service = services[proof_module.OCI_SOURCE_INGESTION_SERVICE]
    assert isinstance(service, dict)
    service["network_mode"] = "bridge"
    service["volumes"] = [".:/workspace"]

    with pytest.raises(ValueError, match="security contract drift"):
        _validate_compose_config(config)


def test_oci_worker_launcher_uses_fixed_compose_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _accepted_worker_response()
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    class FakeStdin:
        def __init__(self) -> None:
            self.data = b""

        def write(self, data: bytes) -> None:
            self.data += data

        def close(self) -> None:
            return None

    class FakeProcess:
        returncode = 0

        def __init__(self, command: tuple[str, ...], **kwargs: object) -> None:
            calls.append((command, kwargs))
            self.stdin = FakeStdin()
            stdout = kwargs["stdout"]
            stdout.write(_canonical_json(response).encode("utf-8"))  # type: ignore[attr-defined]

        def poll(self) -> int:
            return 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(proof_module.subprocess, "Popen", FakeProcess)
    request, _ = _build_worker_request()

    assert proof_module._run_worker(request) == response
    command, kwargs = calls[0]
    assert command == (
        "docker",
        "compose",
        "run",
        "--rm",
        "-T",
        "--no-deps",
        "source-ingestion-worker",
    )
    assert kwargs["shell"] is False
    assert proof_module.MODULE_SOURCE not in " ".join(command)


def test_oci_worker_launcher_rejects_oversized_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStdin:
        def write(self, data: bytes) -> None:
            return None

        def close(self) -> None:
            return None

    class OversizedProcess:
        returncode = 0

        def __init__(self, command: tuple[str, ...], **kwargs: object) -> None:
            self.stdin = FakeStdin()
            stdout = kwargs["stdout"]
            stdout.write(b"x" * (proof_module._MAX_RESPONSE_BYTES + 1))  # type: ignore[attr-defined]

        def poll(self) -> int:
            return 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(proof_module.subprocess, "Popen", OversizedProcess)

    with pytest.raises(ValueError, match="response exceeds limit"):
        proof_module._run_worker(b"{}")


def test_oci_proof_report_matches_golden_without_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proof_module,
        "_load_compose_config",
        _rendered_compose_config,
    )
    monkeypatch.setattr(
        proof_module,
        "_run_worker",
        _mock_worker,
    )

    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


@pytest.mark.skipif(
    os.environ.get("TUC_RUN_OCI_TESTS") != "1",
    reason="requires built OCI worker and Docker Engine",
)
def test_oci_proof_real_worker_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("proof_status", "BLOCKED", "proof_status"),
        ("kernel_network_isolation", False, "kernel_network_isolation"),
        ("filesystem_namespace_isolation", False, "filesystem_namespace_isolation"),
        ("repository_bind_mount", True, "repository_bind_mount"),
        ("production_source_ingestion", True, "production_source_ingestion"),
        ("published_worker_image_provenance", True, "published_worker_image_provenance"),
    ),
)
def test_oci_proof_rejects_claim_drift(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    match: str,
) -> None:
    monkeypatch.setattr(
        proof_module,
        "_load_compose_config",
        _rendered_compose_config,
    )
    monkeypatch.setattr(
        proof_module,
        "_run_worker",
        _mock_worker,
    )
    report = build_oci_source_ingestion_research_proof_report()
    report[field] = value

    with pytest.raises(ValueError, match=match):
        assert_oci_source_ingestion_research_proof_report(report)


def test_oci_proof_schema_is_closed_and_matches_golden() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert sorted(schema["required"]) == sorted(golden)
    assert schema["properties"]["schema_version"]["const"] == (
        OCI_SOURCE_INGESTION_PROOF_SCHEMA_VERSION
    )
    assert schema["properties"]["proof_contract"]["const"] == (
        OCI_SOURCE_INGESTION_PROOF_CONTRACT
    )
    assert schema["properties"]["kernel_network_isolation"]["const"] is True
    assert schema["properties"]["production_source_ingestion"]["const"] is False
    _assert_objects_fail_closed(schema)


def test_oci_worker_supply_chain_and_build_context_are_pinned() -> None:
    dockerfile = Path("docker/source-worker/Dockerfile").read_text(encoding="utf-8")
    requirements = Path("requirements/source-worker.txt").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8").splitlines()

    assert OCI_SOURCE_INGESTION_BASE_IMAGE in dockerfile
    assert "docker/dockerfile:1.7@sha256:" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "USER ${USER_UID}:${USER_GID}" in dockerfile
    assert 'ENTRYPOINT ["python", "-I"' in dockerfile
    assert "numpy==2.4.4 --hash=sha256:" in requirements
    assert dockerignore == [
        "*",
        "!docker/",
        "!docker/**",
        "!requirements/",
        "!requirements/**",
        "!src/",
        "!src/**",
    ]


def test_oci_source_ingestion_proof_is_documented_and_in_ci() -> None:
    required_paths = (
        "docker/source-worker/Dockerfile",
        "requirements/source-worker.txt",
        "examples/oci_source_ingestion_research_proof.py",
        "schemas/oci_source_ingestion_research_proof_report.v0.schema.json",
        "tests/golden/frontend/oci_source_ingestion_research_proof_report.json",
        "tests/test_oci_source_ingestion_research_proof.py",
        "rfcs/0289-oci-source-ingestion-research-worker.md",
    )
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("README.md"),
            Path("ROADMAP.md"),
            DOC_PATH,
            RFC_PATH,
            Path(".github/workflows/ci.yml"),
        )
    )

    for path in required_paths:
        assert path in text
    assert "docker compose build source-ingestion-worker" in text
    assert "TUC_VERIFY_OCI_GOLDEN" in text


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
