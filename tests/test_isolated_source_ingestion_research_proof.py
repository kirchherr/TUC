from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

import tuc.frontend.isolated_source_ingestion as isolated_module
from examples.isolated_source_ingestion_research_proof import (
    ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT,
    ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION,
    assert_isolated_source_ingestion_research_proof_report,
    build_isolated_source_ingestion_research_proof_report,
    build_report,
)
from examples.source_to_intent_research_kernel_ingress import (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
)
from tuc.frontend import (
    ISOLATED_SOURCE_INGESTION_CONTRACT,
    ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS,
    ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS,
    ISOLATED_SOURCE_INGESTION_STATUS,
    ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL,
    IsolatedSourceIngestionError,
    ingest_isolated_triton_module_source,
    isolated_source_ingestion_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/isolated_source_ingestion_research_proof_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/isolated_source_ingestion_research_proof_report.json"
)
DOC_PATH = Path("docs/ISOLATED_SOURCE_INGESTION_RESEARCH_WORKER.md")
RFC_PATH = Path("rfcs/0288-isolated-source-ingestion-research-worker.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_isolated_source_ingestion_research_proof_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def _run_accepted_worker():
    return ingest_isolated_triton_module_source(
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        source_name="research_matmul_elementwise",
        kernel_name="matmul_elementwise",
        tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4, 2)},
    )


def test_isolated_worker_returns_parent_validated_source_intent() -> None:
    result = _run_accepted_worker()
    report = isolated_source_ingestion_report_to_dict(result.report)

    assert result.module.name == "research_matmul_elementwise"
    assert [operation.family for operation in result.module.operations] == [
        "matmul",
        "elementwise",
    ]
    assert result.module.operations[1].attributes["elementwise_kind"] == "relu"
    assert report["contract"] == ISOLATED_SOURCE_INGESTION_CONTRACT
    assert report["worker_protocol"] == ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL
    assert report["status"] == ISOLATED_SOURCE_INGESTION_STATUS
    assert report["enforced_controls"] == list(
        ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS
    )
    assert report["explicit_non_claims"] == list(
        ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS
    )
    assert report["research_source_to_intent_plain_data"] is True
    assert report["direct_source_ingestion"] is False
    assert report["production_source_ingestion"] is False
    assert report["source_text_executed"] is False
    assert report["source_intent_payload_serialized"] is False
    assert report["kernel_network_isolation"] is False
    assert report["filesystem_namespace_isolation"] is False
    encoded = json.dumps(report, sort_keys=True)
    assert "@triton.jit" not in encoded
    assert "import triton" not in encoded
    assert '"source_text"' not in encoded
    assert '"source_intent_payload"' not in encoded


def test_isolated_worker_rejects_malicious_source_without_execution(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "source_was_executed"
    source = f"""import triton
import triton.language as tl

@triton.jit
def malicious(x, y):
    marker = __import__("pathlib").Path({str(marker)!r}).write_text("owned")
    tl.store(y, x)
"""

    with pytest.raises(IsolatedSourceIngestionError, match="source_rejected") as exc:
        ingest_isolated_triton_module_source(
            source,
            source_name="malicious_source",
            kernel_name="malicious",
            tensor_shapes={"x": (4,), "y": (4,)},
        )

    assert not marker.exists()
    assert "pathlib" not in str(exc.value)
    assert "write_text" not in str(exc.value)
    assert str(marker) not in str(exc.value)


def test_isolated_worker_command_is_fixed_and_uses_python_isolated_mode() -> None:
    command = isolated_module._fixed_worker_command()

    assert len(command) == 3
    assert command[0] == sys.executable
    assert command[1] == "-I"
    assert Path(command[2]).name == "_isolated_source_ingestion_worker.py"
    assert REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE not in " ".join(command)


def test_private_worker_rejects_malformed_protocol_source_free(tmp_path: Path) -> None:
    worker_path = Path(isolated_module.__file__).with_name(
        "_isolated_source_ingestion_worker.py"
    )
    completed = subprocess.run(
        [sys.executable, "-I", str(worker_path)],
        input=b'{"untrusted":"@triton.jit"}',
        capture_output=True,
        cwd=tmp_path,
        check=True,
        timeout=10,
    )
    response = json.loads(completed.stdout.decode("utf-8"))

    assert completed.stderr == b""
    assert response["status"] == "rejected"
    assert response["reason_code"] == "source_rejected"
    assert "@triton.jit" not in completed.stdout.decode("utf-8")
    assert set(response) == {"protocol", "reason_code", "request_digest", "status"}


def test_isolated_worker_fails_closed_without_linux_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(isolated_module.sys, "platform", "win32")

    with pytest.raises(IsolatedSourceIngestionError, match="requires Linux"):
        _run_accepted_worker()


def test_isolated_worker_rejects_oversized_source_before_process_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_process(*args: object, **kwargs: object) -> None:
        raise AssertionError("worker must not start for oversized source")

    monkeypatch.setattr(isolated_module.subprocess, "Popen", unexpected_process)

    with pytest.raises(IsolatedSourceIngestionError, match="source exceeds limit"):
        ingest_isolated_triton_module_source(
            "x" * (isolated_module.MAX_TRITON_SOURCE_BYTES + 1),
            source_name="oversized_source",
            kernel_name="oversized",
            tensor_shapes={"x": (1,)},
        )


def test_isolated_worker_rejects_bounded_file_overflow() -> None:
    with pytest.raises(IsolatedSourceIngestionError, match="response exceeds limit"):
        isolated_module._read_bounded_file(BytesIO(b"overflow"), 4, "response")


def test_isolated_worker_parent_timeout_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminated: list[object] = []

    class TimeoutProcess:
        returncode = None

        def communicate(self, *, input: bytes, timeout: float) -> None:
            raise subprocess.TimeoutExpired("fixed-worker", timeout)

    process = TimeoutProcess()
    monkeypatch.setattr(
        isolated_module.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        isolated_module,
        "_terminate_worker",
        lambda value: terminated.append(value),
    )

    with pytest.raises(IsolatedSourceIngestionError, match="wall-clock limit"):
        isolated_module._run_fixed_worker(b"{}")

    assert terminated == [process]


def test_isolated_worker_rejects_non_string_shape_key_without_coercion() -> None:
    class HostileKey:
        def __str__(self) -> str:
            raise AssertionError("untrusted shape keys must not be coerced")

    with pytest.raises(IsolatedSourceIngestionError, match="simple identifier"):
        ingest_isolated_triton_module_source(
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
            source_name="hostile_shape_key",
            kernel_name="matmul_elementwise",
            tensor_shapes={HostileKey(): (1,)},  # type: ignore[dict-item]
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("proof_status", "BLOCKED", "proof_status"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("kernel_network_isolation", True, "kernel_network_isolation"),
        ("production_source_ingestion", True, "production_source_ingestion"),
        ("source_text_executed", True, "source_text_executed"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_isolated_source_ingestion_proof_rejects_claim_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(ValueError, match=match):
        assert_isolated_source_ingestion_research_proof_report(report)


def test_isolated_source_ingestion_proof_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="report digest drift"):
        assert_isolated_source_ingestion_research_proof_report(report)


def test_isolated_source_ingestion_proof_passes_vertical_contract() -> None:
    report = _cached_report()

    assert report["schema_version"] == (
        ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION
    )
    assert report["proof_contract"] == (
        ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT
    )
    assert report["proof_status"] == "PASS"
    assert report["backend_equivalence_passed"] is True
    assert report["reference_correctness_passed"] is True
    assert report["package_backend_sequence"] == [
        "external-systolic",
        "external-vector",
    ]
    assert report["trusted_executor_sequence"] == ["systolic-sim", "vector-sim"]
    assert report["public_output_names"] == ["y"]
    assert report["issues"] == []


def test_isolated_source_ingestion_proof_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_isolated_source_ingestion_proof_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/isolated_source_ingestion_research_proof.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"proof_status": "PASS"' in completed.stdout
    assert '"production_source_ingestion": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_tensor_value":' not in completed.stdout


def test_isolated_source_ingestion_schema_matches_report() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert schema["additionalProperties"] is False
    assert sorted(schema["required"]) == sorted(report)
    assert schema["properties"]["schema_version"]["const"] == (
        ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION
    )
    assert schema["properties"]["proof_contract"]["const"] == (
        ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT
    )
    assert schema["properties"]["production_source_ingestion"]["const"] is False
    assert schema["properties"]["kernel_network_isolation"]["const"] is False
    _assert_objects_fail_closed(schema)


def test_isolated_source_ingestion_proof_is_documented() -> None:
    required_paths = (
        "src/tuc/frontend/isolated_source_ingestion.py",
        "src/tuc/frontend/_isolated_source_ingestion_worker.py",
        "examples/isolated_source_ingestion_research_proof.py",
        "schemas/isolated_source_ingestion_research_proof_report.v0.schema.json",
        "tests/golden/frontend/isolated_source_ingestion_research_proof_report.json",
        "tests/test_isolated_source_ingestion_research_proof.py",
        "rfcs/0288-isolated-source-ingestion-research-worker.md",
    )
    documentation = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path("README.md"), Path("ROADMAP.md"), DOC_PATH, RFC_PATH)
    )

    for path in required_paths:
        assert path in documentation


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
