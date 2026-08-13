"""Prove bounded Source Intent ingress through a hardened OCI worker."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from hashlib import sha256
from pathlib import Path
from typing import cast

OCI_SOURCE_INGESTION_PROOF_SCHEMA_VERSION = (
    "tuc.oci_source_ingestion_research_proof_report.v0"
)
OCI_SOURCE_INGESTION_PROOF_CONTRACT = (
    "oci_source_ingestion_research_proof.kernel_isolated.v0"
)
OCI_SOURCE_INGESTION_PROOF_CLAIM = (
    "bounded_source_intent_crosses_kernel_isolated_worker_and_matches_vertical_proof"
)
OCI_SOURCE_INGESTION_PROOF_STATUS = "PASS"
OCI_SOURCE_INGESTION_WORKER_PROTOCOL = "tuc.oci_source_ingestion_worker.v0"
OCI_SOURCE_INGESTION_SERVICE = "source-ingestion-worker"
OCI_SOURCE_INGESTION_BASE_IMAGE = (
    "python:3.12-slim-bookworm@"
    "sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
)
OCI_SOURCE_INGESTION_NUMPY_VERSION = "2.4.4"
OCI_SOURCE_INGESTION_NUMPY_WHEEL_DIGEST = (
    "sha256:81f4a14bee47aec54f883e0cad2d73986640c1590eb9bfaaba7ad17394481e6e"
)
OCI_SOURCE_INGESTION_BLOCKED_CLAIMS = (
    "general_triton_parser",
    "native_backend_execution",
    "native_performance_parity",
    "production_source_ingestion",
    "production_source_sandbox",
    "published_worker_image_provenance",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yml"
WORKER_DOCKERFILE_PATH = REPOSITORY_ROOT / "docker/source-worker/Dockerfile"
WORKER_REQUIREMENTS_PATH = REPOSITORY_ROOT / "requirements/source-worker.txt"
WORKER_SOURCE_PATH = (
    REPOSITORY_ROOT / "src/tuc/frontend/_isolated_source_ingestion_worker.py"
)
VERTICAL_PROOF_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/frontend/triton_research_backend_package_portfolio_report.json"
)
GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
)

MODULE_SOURCE = """import triton
import triton.language as tl

@triton.jit
def matmul_elementwise(a, b, y):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0.0, projection, 0.0)
    tl.store(y, activated)
"""
SOURCE_NAME = "research_matmul_elementwise"
KERNEL_NAME = "matmul_elementwise"
TENSOR_SHAPES = {"a": [4, 8], "b": [8, 2], "y": [4, 2]}
MALICIOUS_MODULE_SOURCE = """import triton
import triton.language as tl

@triton.jit
def malicious_probe(x, y):
    marker = __import__("pathlib").Path("/tmp/tuc_probe").write_text("executed")
    network = __import__("socket").create_connection(("127.0.0.1", 1))
    tl.store(y, x)
"""
EXPECTED_SOURCE_INTENT = {
    "name": SOURCE_NAME,
    "operations": [
        {
            "family": "matmul",
            "hints": {},
            "inputs": ["a", "b"],
            "name": "projection",
            "outputs": ["projection"],
        },
        {
            "attributes": {"elementwise_kind": "relu"},
            "family": "elementwise",
            "hints": {},
            "inputs": ["projection"],
            "name": "activated",
            "outputs": ["activated"],
        },
    ],
    "returns": [{"public_name": "y", "required": True, "tensor_name": "activated"}],
    "schema_version": "source_intent.v0",
    "tensors": [
        {"dtype": "float32", "name": "a", "shape": [4, 8]},
        {"dtype": "float32", "name": "b", "shape": [8, 2]},
        {"dtype": "float32", "name": "projection", "shape": [4, 2]},
        {"dtype": "float32", "name": "activated", "shape": [4, 2]},
    ],
}

_MAX_REQUEST_BYTES = 96 * 1024
_MAX_RESPONSE_BYTES = 256 * 1024
_MAX_STDERR_BYTES = 64 * 1024
_WORKER_TIMEOUT_SECONDS = 30.0
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RESPONSE_KEYS = frozenset(
    {
        "ingress_report",
        "protocol",
        "request_digest",
        "security",
        "source_intent_payload",
        "status",
    }
)
_SECURITY_KEYS = frozenset(
    {
        "address_space_bytes",
        "capability_effective_hex",
        "core_dump_disabled",
        "cpu_period_micros",
        "cpu_quota_micros",
        "cpu_seconds",
        "empty_working_directory",
        "file_size_bytes",
        "filesystem_namespace_isolation",
        "gid",
        "isolated_python_mode",
        "kernel_network_isolation",
        "memory_limit_bytes",
        "network_route_count",
        "no_new_privileges",
        "open_files",
        "pids_limit",
        "repository_bind_mount",
        "root_filesystem_read_only",
        "seccomp_mode",
        "shell",
        "tmpfs_nodev",
        "tmpfs_noexec",
        "tmpfs_nosuid",
        "uid",
    }
)
_EXPECTED_SECURITY: dict[str, object] = {
    "address_space_bytes": 768 * 1024 * 1024,
    "capability_effective_hex": "0000000000000000",
    "core_dump_disabled": True,
    "cpu_period_micros": 100000,
    "cpu_quota_micros": 100000,
    "cpu_seconds": 4,
    "empty_working_directory": True,
    "file_size_bytes": 256 * 1024,
    "filesystem_namespace_isolation": True,
    "gid": 10001,
    "isolated_python_mode": True,
    "kernel_network_isolation": True,
    "memory_limit_bytes": 1024 * 1024 * 1024,
    "network_route_count": 0,
    "no_new_privileges": True,
    "open_files": 32,
    "pids_limit": 32,
    "repository_bind_mount": False,
    "root_filesystem_read_only": True,
    "seccomp_mode": 2,
    "shell": False,
    "tmpfs_nodev": True,
    "tmpfs_noexec": True,
    "tmpfs_nosuid": True,
    "uid": 10001,
}
_COMPOSE_CONTRACT = {
    "cap_drop": ["ALL"],
    "cpus": 1,
    "dockerfile": "docker/source-worker/Dockerfile",
    "environment": {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
    },
    "image": "tuc-source-ingestion-worker:research-v0",
    "ipc": "private",
    "mem_limit": 1024 * 1024 * 1024,
    "network_mode": "none",
    "pids_limit": 32,
    "platform": "linux/amd64",
    "read_only": True,
    "security_opt": ["no-new-privileges:true"],
    "shm_size": 16 * 1024 * 1024,
    "tmpfs": [
        "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1700,uid=10001,gid=10001"
    ],
    "user": "10001:10001",
    "volumes": [],
    "working_dir": "/run/tuc",
}
_REPORT_KEYS = frozenset(
    {
        "artifact_policy",
        "backend_equivalence_passed",
        "base_image",
        "blocked_claims",
        "compose_contract_digest",
        "direct_source_ingestion",
        "dockerfile_digest",
        "external_package_code_executed",
        "fallback_assignment_count",
        "filesystem_namespace_isolation",
        "kernel_network_isolation",
        "malicious_source_executed",
        "malicious_source_rejected",
        "negative_case_count",
        "no_new_privileges",
        "numpy_version",
        "numpy_wheel_digest",
        "operation_families",
        "production_source_ingestion",
        "production_source_sandbox",
        "proof_claim",
        "proof_contract",
        "proof_status",
        "published_worker_image_provenance",
        "raw_source_serialized",
        "raw_tensor_values_serialized",
        "reference_correctness_passed",
        "report_digest",
        "repository_bind_mount",
        "requirements_digest",
        "rejection_reason_code",
        "rejection_request_digest",
        "root_filesystem_read_only",
        "schema_version",
        "seccomp_mode",
        "source_intent_digest",
        "source_intent_matches_vertical_proof",
        "source_intent_payload_serialized",
        "source_text_executed",
        "trusted_executor_sequence",
        "vertical_proof_digest",
        "worker_protocol",
        "worker_request_digest",
        "worker_source_digest",
    }
)
_FORBIDDEN_REPORT_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"command":',
    '"host_path":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_values":',
)


def build_oci_source_ingestion_research_proof_report() -> dict[str, object]:
    """Execute and validate the fixed hardened worker and linked vertical proof."""

    compose = _load_compose_config()
    compose_contract = _validate_compose_config(compose)
    request, request_digest = _build_worker_request()
    response = _run_worker(request)
    source_intent_digest = _validate_worker_response(
        response,
        expected_request_digest=request_digest,
    )
    rejection_request, rejection_request_digest = _build_rejection_request()
    rejection_response = _run_worker(rejection_request)
    _validate_rejection_response(
        rejection_response,
        expected_request_digest=rejection_request_digest,
    )
    vertical_proof = _load_json(VERTICAL_PROOF_PATH)
    _validate_vertical_proof(vertical_proof, source_intent_digest)
    security = cast(dict[str, object], response["security"])
    report: dict[str, object] = {
        "artifact_policy": "metadata_digest_only_source_and_values_omitted",
        "backend_equivalence_passed": True,
        "base_image": OCI_SOURCE_INGESTION_BASE_IMAGE,
        "blocked_claims": list(OCI_SOURCE_INGESTION_BLOCKED_CLAIMS),
        "compose_contract_digest": _digest_payload(compose_contract),
        "direct_source_ingestion": False,
        "dockerfile_digest": _digest_file(WORKER_DOCKERFILE_PATH),
        "external_package_code_executed": False,
        "fallback_assignment_count": 0,
        "filesystem_namespace_isolation": security[
            "filesystem_namespace_isolation"
        ],
        "kernel_network_isolation": security["kernel_network_isolation"],
        "malicious_source_executed": False,
        "malicious_source_rejected": True,
        "negative_case_count": 1,
        "no_new_privileges": security["no_new_privileges"],
        "numpy_version": OCI_SOURCE_INGESTION_NUMPY_VERSION,
        "numpy_wheel_digest": OCI_SOURCE_INGESTION_NUMPY_WHEEL_DIGEST,
        "operation_families": ["elementwise", "matmul"],
        "production_source_ingestion": False,
        "production_source_sandbox": False,
        "proof_claim": OCI_SOURCE_INGESTION_PROOF_CLAIM,
        "proof_contract": OCI_SOURCE_INGESTION_PROOF_CONTRACT,
        "proof_status": OCI_SOURCE_INGESTION_PROOF_STATUS,
        "published_worker_image_provenance": False,
        "raw_source_serialized": False,
        "raw_tensor_values_serialized": False,
        "reference_correctness_passed": True,
        "repository_bind_mount": security["repository_bind_mount"],
        "requirements_digest": _digest_file(WORKER_REQUIREMENTS_PATH),
        "rejection_reason_code": "source_rejected",
        "rejection_request_digest": rejection_request_digest,
        "root_filesystem_read_only": security["root_filesystem_read_only"],
        "schema_version": OCI_SOURCE_INGESTION_PROOF_SCHEMA_VERSION,
        "seccomp_mode": security["seccomp_mode"],
        "source_intent_digest": source_intent_digest,
        "source_intent_matches_vertical_proof": True,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
        "vertical_proof_digest": _digest_file(VERTICAL_PROOF_PATH),
        "worker_protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "worker_request_digest": request_digest,
        "worker_source_digest": _digest_file(WORKER_SOURCE_PATH),
    }
    report["report_digest"] = _digest_payload(report)
    return assert_oci_source_ingestion_research_proof_report(report)


def assert_oci_source_ingestion_research_proof_report(
    report: object,
) -> dict[str, object]:
    """Fail closed unless public OCI evidence matches the research claim."""

    if type(report) is not dict:
        raise TypeError("OCI source ingestion proof report must be plain object")
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise ValueError("OCI source ingestion proof report key drift")
    expected: dict[str, object] = {
        "artifact_policy": "metadata_digest_only_source_and_values_omitted",
        "backend_equivalence_passed": True,
        "base_image": OCI_SOURCE_INGESTION_BASE_IMAGE,
        "blocked_claims": list(OCI_SOURCE_INGESTION_BLOCKED_CLAIMS),
        "direct_source_ingestion": False,
        "external_package_code_executed": False,
        "fallback_assignment_count": 0,
        "filesystem_namespace_isolation": True,
        "kernel_network_isolation": True,
        "malicious_source_executed": False,
        "malicious_source_rejected": True,
        "negative_case_count": 1,
        "no_new_privileges": True,
        "numpy_version": OCI_SOURCE_INGESTION_NUMPY_VERSION,
        "numpy_wheel_digest": OCI_SOURCE_INGESTION_NUMPY_WHEEL_DIGEST,
        "operation_families": ["elementwise", "matmul"],
        "production_source_ingestion": False,
        "production_source_sandbox": False,
        "proof_claim": OCI_SOURCE_INGESTION_PROOF_CLAIM,
        "proof_contract": OCI_SOURCE_INGESTION_PROOF_CONTRACT,
        "proof_status": OCI_SOURCE_INGESTION_PROOF_STATUS,
        "published_worker_image_provenance": False,
        "raw_source_serialized": False,
        "raw_tensor_values_serialized": False,
        "rejection_reason_code": "source_rejected",
        "reference_correctness_passed": True,
        "repository_bind_mount": False,
        "root_filesystem_read_only": True,
        "schema_version": OCI_SOURCE_INGESTION_PROOF_SCHEMA_VERSION,
        "seccomp_mode": 2,
        "source_intent_matches_vertical_proof": True,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
        "worker_protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
    }
    for key, expected_value in expected.items():
        if typed[key] != expected_value:
            raise ValueError(f"OCI source ingestion proof {key} drift")
    for key in (
        "compose_contract_digest",
        "dockerfile_digest",
        "numpy_wheel_digest",
        "report_digest",
        "requirements_digest",
        "rejection_request_digest",
        "source_intent_digest",
        "vertical_proof_digest",
        "worker_request_digest",
        "worker_source_digest",
    ):
        _validate_digest(typed[key], key)
    without_digest = dict(typed)
    del without_digest["report_digest"]
    if typed["report_digest"] != _digest_payload(without_digest):
        raise ValueError("OCI source ingestion proof report digest drift")
    encoded = _canonical_json(typed).lower()
    for fragment in _FORBIDDEN_REPORT_FRAGMENTS:
        if fragment in encoded:
            raise ValueError("OCI source ingestion proof leaks source or values")
    return typed


def build_report() -> str:
    """Return deterministic OCI proof evidence."""

    return json.dumps(
        build_oci_source_ingestion_research_proof_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def _build_worker_request() -> tuple[bytes, str]:
    payload: dict[str, object] = {
        "kernel_name": KERNEL_NAME,
        "module_source": MODULE_SOURCE,
        "source_name": SOURCE_NAME,
        "tensor_shapes": TENSOR_SHAPES,
    }
    request_digest = _digest_payload(payload)
    request = {
        "payload": payload,
        "protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "request_digest": request_digest,
    }
    encoded = _canonical_json(request).encode("utf-8")
    if len(encoded) > _MAX_REQUEST_BYTES:
        raise ValueError("OCI source ingestion request exceeds limit")
    return encoded, request_digest


def _build_rejection_request() -> tuple[bytes, str]:
    payload: dict[str, object] = {
        "kernel_name": "malicious_probe",
        "module_source": MALICIOUS_MODULE_SOURCE,
        "source_name": "oci_malicious_probe",
        "tensor_shapes": {"x": [4], "y": [4]},
    }
    request_digest = _digest_payload(payload)
    request = {
        "payload": payload,
        "protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "request_digest": request_digest,
    }
    encoded = _canonical_json(request).encode("utf-8")
    if len(encoded) > _MAX_REQUEST_BYTES:
        raise ValueError("OCI source ingestion rejection request exceeds limit")
    return encoded, request_digest


def _run_worker(request: bytes) -> dict[str, object]:
    command = (
        "docker",
        "compose",
        "run",
        "--rm",
        "-T",
        "--no-deps",
        OCI_SOURCE_INGESTION_SERVICE,
    )
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(  # noqa: S603 - fixed Compose service only
            command,
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.PIPE,
            stdout=stdout_file,
            stderr=stderr_file,
            shell=False,
            close_fds=True,
        )
        if process.stdin is None:
            process.kill()
            raise ValueError("OCI worker stdin unavailable")
        process.stdin.write(request)
        process.stdin.close()
        deadline = time.monotonic() + _WORKER_TIMEOUT_SECONDS
        while process.poll() is None:
            if time.monotonic() >= deadline:
                process.kill()
                process.wait()
                raise ValueError("OCI worker exceeded wall-clock limit")
            if os.fstat(stdout_file.fileno()).st_size > _MAX_RESPONSE_BYTES:
                process.kill()
                process.wait()
                raise ValueError("OCI worker response exceeds limit")
            if os.fstat(stderr_file.fileno()).st_size > _MAX_STDERR_BYTES:
                process.kill()
                process.wait()
                raise ValueError("OCI worker diagnostics exceed limit")
            time.sleep(0.01)
        if process.returncode != 0:
            raise ValueError("OCI worker failed closed")
        response_bytes = _read_bounded_file(
            stdout_file,
            _MAX_RESPONSE_BYTES,
            "response",
        )
        _read_bounded_file(stderr_file, _MAX_STDERR_BYTES, "diagnostics")
    try:
        response = json.loads(response_bytes.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("OCI worker returned invalid JSON") from exc
    if type(response) is not dict:
        raise ValueError("OCI worker response must be plain object")
    return cast(dict[str, object], response)


def _load_compose_config() -> dict[str, object]:
    completed = subprocess.run(  # noqa: S603 - fixed Compose inspection only
        ("docker", "compose", "config", "--format", "json"),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        timeout=15,
        shell=False,
    )
    if completed.returncode != 0 or len(completed.stdout) > _MAX_RESPONSE_BYTES:
        raise ValueError("OCI Compose contract inspection failed closed")
    try:
        payload = json.loads(completed.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("OCI Compose contract returned invalid JSON") from exc
    if type(payload) is not dict:
        raise ValueError("OCI Compose contract must be plain object")
    return cast(dict[str, object], payload)


def _validate_compose_config(config: dict[str, object]) -> dict[str, object]:
    services = config.get("services")
    if type(services) is not dict:
        raise ValueError("OCI Compose services missing")
    service = cast(dict[str, object], services).get(OCI_SOURCE_INGESTION_SERVICE)
    if type(service) is not dict:
        raise ValueError("OCI worker Compose service missing")
    typed = cast(dict[str, object], service)
    build = typed.get("build")
    if type(build) is not dict:
        raise ValueError("OCI worker build contract missing")
    build_typed = cast(dict[str, object], build)
    context = build_typed.get("context")
    if not isinstance(context, str) or Path(context).resolve() != REPOSITORY_ROOT:
        raise ValueError("OCI worker build context drift")
    normalized = {
        "cap_drop": typed.get("cap_drop"),
        "cpus": typed.get("cpus"),
        "dockerfile": build_typed.get("dockerfile"),
        "environment": typed.get("environment"),
        "image": typed.get("image"),
        "ipc": typed.get("ipc"),
        "mem_limit": int(cast(str, typed.get("mem_limit"))),
        "network_mode": typed.get("network_mode"),
        "pids_limit": typed.get("pids_limit"),
        "platform": typed.get("platform"),
        "read_only": typed.get("read_only"),
        "security_opt": typed.get("security_opt"),
        "shm_size": int(cast(str, typed.get("shm_size"))),
        "tmpfs": typed.get("tmpfs"),
        "user": typed.get("user"),
        "volumes": typed.get("volumes", []),
        "working_dir": typed.get("working_dir"),
    }
    if normalized != _COMPOSE_CONTRACT:
        raise ValueError("OCI worker Compose security contract drift")
    return normalized


def _validate_worker_response(
    response: dict[str, object],
    *,
    expected_request_digest: str,
) -> str:
    if frozenset(response) != _RESPONSE_KEYS:
        raise ValueError("OCI worker response key drift")
    if response.get("protocol") != OCI_SOURCE_INGESTION_WORKER_PROTOCOL:
        raise ValueError("OCI worker protocol drift")
    if response.get("status") != "accepted":
        raise ValueError("OCI worker rejected request")
    if response.get("request_digest") != expected_request_digest:
        raise ValueError("OCI worker request binding drift")
    security = response.get("security")
    if type(security) is not dict or frozenset(security) != _SECURITY_KEYS:
        raise ValueError("OCI worker security key drift")
    if security != _EXPECTED_SECURITY:
        raise ValueError("OCI worker security invariant drift")
    source_intent = response.get("source_intent_payload")
    if source_intent != EXPECTED_SOURCE_INTENT:
        raise ValueError("OCI worker Source Intent drift")
    source_intent_digest = _digest_payload(source_intent)
    ingress = response.get("ingress_report")
    if type(ingress) is not dict:
        raise ValueError("OCI worker ingress report missing")
    ingress_typed = cast(dict[str, object], ingress)
    expected_ingress = {
        "ingress_contract": "source_to_intent_research_kernel_ingress.execution_free.v0",
        "kernel_name": KERNEL_NAME,
        "module_digest": _digest_text(MODULE_SOURCE),
        "operation_families": ["elementwise", "matmul"],
        "source_intent_digest": source_intent_digest,
        "source_name": SOURCE_NAME,
    }
    for key, expected in expected_ingress.items():
        if ingress_typed.get(key) != expected:
            raise ValueError(f"OCI worker ingress {key} drift")
    return source_intent_digest


def _validate_rejection_response(
    response: dict[str, object],
    *,
    expected_request_digest: str,
) -> None:
    expected = {
        "protocol": OCI_SOURCE_INGESTION_WORKER_PROTOCOL,
        "reason_code": "source_rejected",
        "request_digest": expected_request_digest,
        "status": "rejected",
    }
    if response != expected:
        raise ValueError("OCI worker malicious-source rejection drift")
    encoded = _canonical_json(response).lower()
    for fragment in ("__import__", "pathlib", "socket", "/tmp/tuc_probe"):
        if fragment in encoded:
            raise ValueError("OCI worker rejection leaked malicious source")


def _validate_vertical_proof(
    proof: dict[str, object],
    source_intent_digest: str,
) -> None:
    frontend = proof.get("frontend")
    planning = proof.get("planning")
    execution = proof.get("execution")
    if not all(type(item) is dict for item in (frontend, planning, execution)):
        raise ValueError("OCI vertical proof structure drift")
    if proof.get("proof_status") != "PASS":
        raise ValueError("OCI vertical proof status drift")
    if cast(dict[str, object], frontend).get("source_intent_digest") != (
        source_intent_digest
    ):
        raise ValueError("OCI vertical proof Source Intent binding drift")
    if cast(dict[str, object], planning).get("fallback_assignment_count") != 0:
        raise ValueError("OCI vertical proof fallback drift")
    if cast(dict[str, object], planning).get("trusted_executor_sequence") != [
        "systolic-sim",
        "vector-sim",
    ]:
        raise ValueError("OCI vertical proof executor drift")
    if cast(dict[str, object], execution).get("reference_correctness_passed") is not True:
        raise ValueError("OCI vertical proof correctness drift")
    if cast(dict[str, object], execution).get("backend_equivalence_passed") is not True:
        raise ValueError("OCI vertical proof equivalence drift")


def _read_bounded_file(file: object, limit: int, label: str) -> bytes:
    file.seek(0, os.SEEK_END)  # type: ignore[attr-defined]
    size = file.tell()  # type: ignore[attr-defined]
    if not isinstance(size, int) or size < 0 or size > limit:
        raise ValueError(f"OCI worker {label} exceeds limit")
    file.seek(0)  # type: ignore[attr-defined]
    data = file.read(limit + 1)  # type: ignore[attr-defined]
    if not isinstance(data, bytes) or len(data) > limit:
        raise ValueError(f"OCI worker {label} exceeds limit")
    return data


def _load_json(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) > _MAX_RESPONSE_BYTES:
        raise ValueError("OCI proof input artifact exceeds limit")
    try:
        payload = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("OCI proof input artifact invalid") from exc
    if type(payload) is not dict:
        raise ValueError("OCI proof input artifact must be plain object")
    return cast(dict[str, object], payload)


def _validate_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"OCI source ingestion proof {label} invalid")


def _digest_file(path: Path) -> str:
    data = path.read_bytes()
    return f"sha256:{sha256(data).hexdigest()}"


def _digest_payload(payload: object) -> str:
    return _digest_text(_canonical_json(payload))


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def main() -> None:
    verify_golden = os.environ.get("TUC_VERIFY_OCI_GOLDEN") == "1"
    report = build_report()
    if verify_golden and report != GOLDEN_PATH.read_text(encoding="utf-8"):
        raise SystemExit("OCI source ingestion proof golden drift")
    print(report, end="")


if __name__ == "__main__":
    main()
