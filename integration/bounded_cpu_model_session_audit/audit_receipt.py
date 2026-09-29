"""Audit the fixed bounded-model-session receipt with the Python standard library."""

from __future__ import annotations

import json
import math
import struct
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = "tuc.bounded_model_session_audit_report.v0"
AUDIT_CONTRACT = "bounded_model_session.receipt_reimplementation.stdlib.v0"
MAX_RECEIPT_BYTES = 16 * 1024
EXPECTED_RECEIPT_SHA256 = "6e94549a7e11d5501198ac0e7070e4b4f909d5148345e98902cb5b42aa686d1a"
EXPECTED_SOURCE_COMMIT = "f4dbcc9a109142fad5bb2734443532cdbc6345d6"
EXPECTED_WHEEL_SHA256 = "60546f131e2473e9cfd3eeca8a0e38342be3e5a37010e5a64522f88df7ee7dfd"
EXPECTED_CONSUMER_SHA256 = "d13700b1788d53b3363c81e2461f2af728591865cfbc6f291fbbc706f4bbc087"
EXPECTED_PROGRAMS = {
    "linear": "00120d74783287c744827c78b819d98e38a1a84d4b1d9293da22a04991b48071",
    "classifier": "b995a4679612449ce508089568d00fde45954722a1db0afbd08bdca74bac7e3b",
    "changed_parameters": (
        "00120d74783287c744827c78b819d98e38a1a84d4b1d9293da22a04991b48071"
    ),
}
EXPECTED_REJECTIONS = [
    "linear:override",
    "request_limit",
    "linear:closed",
    "classifier:override",
    "classifier:closed",
    "changed_parameters:override",
    "changed_parameters:closed",
    "numeric_rejection",
    "closed_after_failure",
]
BLOCKED_CLAIMS = [
    "independent_organizational_reproduction",
    "arbitrary_models_or_inputs",
    "general_native_runtime_admission",
    "resident_model_weights",
    "native_performance",
]
_USAGE = "usage: python audit_receipt.py RECEIPT.json\n"
_REJECTION = "bounded-model-session-audit: input rejected\n"


class AuditError(ValueError):
    """Raised when the fixed receipt does not satisfy the audit contract."""


def audit(receipt_path: str | Path) -> dict[str, object]:
    """Reconstruct fixed identities and numerical results without importing TUC."""

    raw = _read_regular_file(Path(receipt_path))
    receipt = _load_object(raw)
    if set(receipt) != {"consumer_sha256", "integration", "source_commit", "wheel_sha256"}:
        raise AuditError("receipt envelope drift")
    if receipt["source_commit"] != EXPECTED_SOURCE_COMMIT:
        raise AuditError("source identity drift")
    if receipt["wheel_sha256"] != EXPECTED_WHEEL_SHA256:
        raise AuditError("wheel identity drift")
    if receipt["consumer_sha256"] != EXPECTED_CONSUMER_SHA256:
        raise AuditError("consumer identity drift")

    integration = _object(receipt["integration"])
    expected_keys = {
        "before_numeric_failure",
        "bitexact_scalar_checks",
        "invalid_extent_rejections",
        "native_execution_observed",
        "records",
        "rejections",
        "scalar_checks",
        "schema_version",
        "sessions",
        "stable_context_checks",
        "status",
        "successful_runs",
        "tolerance_scalar_checks",
        "workspaces_clean",
    }
    if set(integration) != expected_keys:
        raise AuditError("integration envelope drift")
    expected_scalars = {
        "bitexact_scalar_checks": 38,
        "invalid_extent_rejections": 20,
        "native_execution_observed": True,
        "scalar_checks": 42,
        "schema_version": "tuc.bounded_cpu_model_session_integration.v0",
        "sessions": 4,
        "stable_context_checks": 17,
        "status": "PASS",
        "successful_runs": 21,
        "tolerance_scalar_checks": 4,
        "workspaces_clean": True,
    }
    if any(integration[key] != value for key, value in expected_scalars.items()):
        raise AuditError("integration summary drift")
    if integration["rejections"] != EXPECTED_REJECTIONS:
        raise AuditError("rejection evidence drift")

    expected_models = {
        family: _model_digest(family)
        for family in ("linear", "classifier", "changed_parameters")
    }
    records = integration["records"]
    if type(records) is not list or len(records) != 20:
        raise AuditError("record count drift")
    counts = {"linear": 0, "classifier": 0, "changed_parameters": 0}
    scalar_checks = bitexact_checks = tolerance_checks = 0
    maximum_difference = 0.0
    first_record: dict[str, Any] | None = None
    for raw_record in records:
        record = _object(raw_record)
        if set(record) != {
            "expected",
            "family",
            "inputs",
            "model_digest",
            "outputs",
            "program_digest",
            "request_digest",
            "sequence",
        }:
            raise AuditError("record envelope drift")
        family = record["family"]
        if type(family) is not str or family not in counts:
            raise AuditError("record family drift")
        counts[family] += 1
        if record["sequence"] != counts[family]:
            raise AuditError("record sequence drift")
        inputs = _numbers(record["inputs"], 2)
        if inputs not in ([2.0, 3.0], [-1.0, 2.0]):
            raise AuditError("record input drift")
        if record["model_digest"] != expected_models[family]:
            raise AuditError("model identity drift")
        program = EXPECTED_PROGRAMS[family]
        if record["program_digest"] != program:
            raise AuditError("program identity drift")
        if record["request_digest"] != _request_digest(family, inputs, program):
            raise AuditError("request identity drift")
        reference = _reference(family, inputs)
        expected = _numbers(record["expected"], 2)
        outputs = _numbers(record["outputs"], 2)
        for observed in (expected, outputs):
            for actual, wanted in zip(observed, reference, strict=True):
                difference = abs(actual - wanted)
                maximum_difference = max(maximum_difference, difference)
                if family == "classifier":
                    if difference > 2e-6 + 2e-5 * abs(wanted):
                        raise AuditError("classifier numerical drift")
                    tolerance_checks += 1
                else:
                    if _f32_bytes(actual) != _f32_bytes(wanted):
                        raise AuditError("linear numerical drift")
                    bitexact_checks += 1
                scalar_checks += 1
        if family == "classifier" and abs(sum(outputs) - 1.0) > 8e-6:
            raise AuditError("softmax row-mass drift")
        if first_record is None:
            first_record = record

    if counts != {"linear": 16, "classifier": 2, "changed_parameters": 2}:
        raise AuditError("family coverage drift")
    # Each record contains both the independently produced expected values and
    # observed values. Count each scalar once for the public audit summary.
    scalar_checks //= 2
    bitexact_checks //= 2
    tolerance_checks //= 2
    if (scalar_checks, bitexact_checks, tolerance_checks) != (40, 36, 4):
        raise AuditError("numerical coverage drift")
    if first_record is None:
        raise AuditError("first result absent")
    _validate_preserved_result(_object(integration["before_numeric_failure"]), first_record)
    scalar_checks += 2
    bitexact_checks += 2

    receipt_digest = sha256(raw).hexdigest()
    if receipt_digest != EXPECTED_RECEIPT_SHA256:
        raise AuditError("receipt byte identity drift")
    return {
        "audit_contract": AUDIT_CONTRACT,
        "bitexact_scalar_checks": bitexact_checks,
        "blocked_claims": BLOCKED_CLAIMS,
        "consumer_sha256": EXPECTED_CONSUMER_SHA256,
        "independent_organizational_evidence": False,
        "max_absolute_reference_difference": maximum_difference,
        "model_digests_recomputed": True,
        "models_reconstructed": 3,
        "native_execution_observed_in_receipt": True,
        "new_native_execution": False,
        "numpy_imported": False,
        "program_digests_bound": True,
        "receipt_bytes": len(raw),
        "receipt_sha256": receipt_digest,
        "records_checked": 20,
        "request_bindings": 21,
        "request_digests_recomputed": True,
        "scalar_checks": scalar_checks,
        "schema_version": SCHEMA_VERSION,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "status": "PASS",
        "stdlib_only": True,
        "subprocess_execution": False,
        "third_party_dependencies": False,
        "tolerance_scalar_checks": tolerance_checks,
        "tuc_imported": False,
        "wheel_sha256": EXPECTED_WHEEL_SHA256,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--help"]:
        sys.stdout.write(_USAGE)
        return 0
    if len(arguments) != 1:
        sys.stderr.write(_USAGE)
        return 2
    try:
        report = audit(arguments[0])
    except (
        AuditError,
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        struct.error,
    ):
        sys.stderr.write(_REJECTION)
        return 2
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


def _read_regular_file(path: Path) -> bytes:
    if path.is_symlink():
        raise AuditError("symbolic link rejected")
    stat_result = path.stat()
    if not path.is_file() or not 0 < stat_result.st_size <= MAX_RECEIPT_BYTES:
        raise AuditError("receipt boundary rejected")
    raw = path.read_bytes()
    if len(raw) != stat_result.st_size or len(raw) > MAX_RECEIPT_BYTES:
        raise AuditError("receipt changed while reading")
    return raw


def _load_object(raw: bytes) -> dict[str, Any]:
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_without_duplicates,
        parse_constant=_reject_non_finite,
    )
    return _object(value)


def _without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate JSON key")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise AuditError(f"non-finite JSON number rejected: {value}")


def _object(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuditError("object required")
    return value


def _numbers(value: object, count: int) -> list[float]:
    if type(value) is not list or len(value) != count:
        raise AuditError("numeric vector drift")
    result: list[float] = []
    for item in value:
        if type(item) not in (int, float) or not math.isfinite(float(item)):
            raise AuditError("numeric value drift")
        result.append(float(item))
    return result


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("ascii")


def _model_digest(family: str) -> str:
    softmax = family == "classifier"
    changed = family == "changed_parameters"
    tensors = [
        {"dtype": "float32", "name": name, "shape": shape}
        for name, shape in (
            ("x", [1, 2]),
            ("w", [2, 2]),
            ("b", [2]),
            ("p", [1, 2]),
            ("y", [1, 2]),
        )
    ]
    operations: list[dict[str, object]] = [
        {
            "attributes": {"rhs_transposed": True},
            "family": "matmul",
            "hints": {},
            "inputs": ["x", "w"],
            "name": "linear",
            "outputs": ["p"],
        },
        {
            "attributes": {"elementwise_kind": "add"},
            "family": "elementwise",
            "hints": {},
            "inputs": ["p", "b"],
            "name": "bias",
            "outputs": ["y"],
        },
    ]
    if softmax:
        tensors.append({"dtype": "float32", "name": "s", "shape": [1, 2]})
        operations.append(
            {
                "attributes": {"axis": 1},
                "family": "softmax",
                "hints": {},
                "inputs": ["y"],
                "name": "probability",
                "outputs": ["s"],
            }
        )
    graph = {
        "name": "session_classifier" if softmax else "session_linear",
        "operations": operations,
        "returns": [
            {
                "public_name": "scores",
                "required": True,
                "tensor_name": "s" if softmax else "y",
            }
        ],
        "schema_version": "source_intent.v0",
        "tensors": tensors,
    }
    weights = [3.0 if changed else 2.0, -1.0, 1.0, 3.0]
    identity = {
        "graph": graph,
        "parameter_bits": {
            "b": b"".join(_f32_bytes(value) for value in [0.5, -0.0]).hex(),
            "w": b"".join(_f32_bytes(value) for value in weights).hex(),
        },
        "schema_version": "tuc.bounded_cpu_model.v0",
    }
    return sha256(_canonical(identity)).hexdigest()


def _request_digest(family: str, inputs: list[float], program: str) -> str:
    changed = family == "changed_parameters"
    weights = [3.0 if changed else 2.0, -1.0, 1.0, 3.0]
    payload = b"".join(_f32_bytes(value) for value in [*inputs, *weights, 0.5, -0.0])
    return sha256(bytes.fromhex(program) + payload).hexdigest()


def _reference(family: str, inputs: list[float]) -> list[float]:
    changed = family == "changed_parameters"
    scores = [
        _f32(_f32(_f32(inputs[0] * (3 if changed else 2)) + _f32(-inputs[1])) + 0.5),
        _f32(_f32(inputs[0]) + _f32(3 * inputs[1])),
    ]
    if family == "classifier":
        maximum = max(scores)
        exponentials = [_f32(math.exp(_f32(value - maximum))) for value in scores]
        total = _f32(sum(exponentials))
        return [_f32(value / total) for value in exponentials]
    return scores


def _validate_preserved_result(result: dict[str, Any], first: dict[str, Any]) -> None:
    if set(result) != {"model_digest", "outputs", "program_digest", "request_digest"}:
        raise AuditError("preserved result envelope drift")
    for key in ("model_digest", "program_digest", "request_digest"):
        if result[key] != first[key]:
            raise AuditError("preserved result identity drift")
    if result["outputs"] != [["scores", [1.5, 11.0]]]:
        raise AuditError("preserved result output drift")


def _f32(value: float) -> float:
    return cast(float, struct.unpack("<f", _f32_bytes(value))[0])


def _f32_bytes(value: float) -> bytes:
    return struct.pack("<f", float(value))


if __name__ == "__main__":
    raise SystemExit(main())
