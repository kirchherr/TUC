"""Auditable Objective Delta reproducer using only the Python standard library."""

from __future__ import annotations

import json
import math
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

AUDIT_SCHEMA_VERSION = "tuc.objective_delta_audit_report.v0"
AUDIT_CONTRACT = "objective_delta.contract_reimplementation.stdlib.v0"
MAX_JSON_BYTES = 16 * 1024

SOURCE_FILENAME = "source_intent.v0.json"
PACKAGE_FILENAMES = (
    "external_systolic.v0.json",
    "external_vector.v0.json",
)

BLOCKED_CLAIMS = (
    "independent_organizational_reproduction",
    "arbitrary_source_intent",
    "external_package_code_execution",
    "native_backend_execution",
    "physical_device_portability",
    "native_performance_parity",
)

EXPECTED_SOURCE_DIGEST = (
    "sha256:5c5a6435ff498a159e09b76a99f4103531ab8c1659f28185d3586c5e11c5aace"
)
EXPECTED_PACKAGE_DIGESTS = {
    "external-systolic-reference-package": (
        "sha256:806813974dfde16b46f694566d751b18780d5e43d8455467bf4e5d7ea38b452c"
    ),
    "external-vector-reference-package": (
        "sha256:bf4bf333025a176f20ad927c249747f6ce923e14f224f4cd94ed769d893288ee"
    ),
}
EXPECTED_VECTOR_DIGEST = (
    "sha256:b03d192c1868c2a1c9b0169e4a3bbe2d609ab823ce0f64cf157b80dccccf3aef"
)
EXPECTED_OUTPUT_DIGEST = (
    "sha256:db8ad36b4074749f60a69cb958471064c3311d5343744d75b6e298bd48299039"
)

_USAGE = "usage: python audit_reproducer.py CONTRACT_DIR CONFORMANCE_VECTOR.json\n"
_REJECTION = "objective-delta-audit: input rejected\n"


class AuditError(ValueError):
    """Raised when the fixed audit contract cannot be reproduced."""


def reproduce(contract_root: str | Path, vector_path: str | Path) -> dict[str, object]:
    """Reimplement the fixed planner and semantics without importing TUC or NumPy."""

    root = Path(contract_root)
    source = _load_json_object(root / SOURCE_FILENAME)
    source_digest = _digest(source)
    if source_digest != EXPECTED_SOURCE_DIGEST:
        raise AuditError("Source Intent contract drift")

    packages = tuple(
        _validate_package(_load_json_object(root / filename))
        for filename in PACKAGE_FILENAMES
    )
    vector = _load_json_object(Path(vector_path))
    vector_digest = _digest(vector)
    if vector_digest != EXPECTED_VECTOR_DIGEST:
        raise AuditError("conformance vector drift")

    assignments, conversions = _plan(source, packages)
    public_outputs = _execute(source, vector)
    expected_outputs = vector["expected_public_outputs"]
    if public_outputs != expected_outputs:
        raise AuditError("public output mismatch")
    output_digest = _digest(public_outputs)
    if output_digest != EXPECTED_OUTPUT_DIGEST:
        raise AuditError("public output digest drift")

    report: dict[str, object] = {
        "assignment_count": len(assignments),
        "assignments": assignments,
        "audit_contract": AUDIT_CONTRACT,
        "audit_status": "PASS",
        "blocked_claims": list(BLOCKED_CLAIMS),
        "conformance_vector_contains_public_values": True,
        "conformance_vector_digest": vector_digest,
        "external_code_executed": False,
        "independent_organizational_evidence": False,
        "layout_conversion_count": len(conversions),
        "layout_conversions": conversions,
        "native_backend_execution": False,
        "native_performance_claim": False,
        "network_access": False,
        "numpy_imported": False,
        "output_digest": output_digest,
        "outputs_match": True,
        "package_digests": [_digest(package) for package in packages],
        "package_ids": [package["package_id"] for package in packages],
        "physical_device_execution": False,
        "proof_scope": "fixed_2x2_matmul_then_identity",
        "public_output_names": list(public_outputs),
        "python_code_executed": True,
        "raw_tensor_values_serialized": False,
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_intent_digest": source_digest,
        "stdlib_only": True,
        "subprocess_execution": False,
        "third_party_dependencies": False,
        "tuc_imported": False,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    """Run the reduced-dependency audit CLI."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--help"]:
        sys.stdout.write(_USAGE)
        return 0
    if len(arguments) != 2:
        sys.stderr.write(_USAGE)
        return 2
    try:
        report = reproduce(arguments[0], arguments[1])
    except (AuditError, OSError, TypeError, UnicodeError, ValueError):
        sys.stderr.write(_REJECTION)
        return 2
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


def _validate_package(package: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "schema_version",
        "package_id",
        "package_version",
        "interface_contract",
        "package_policy",
        "import_policy",
        "backend_code_included",
        "execution_permission",
        "capability_manifest",
        "conformance_cases",
    }
    if set(package) != required_keys:
        raise AuditError("backend package key drift")
    package_id = package["package_id"]
    if type(package_id) is not str or package_id not in EXPECTED_PACKAGE_DIGESTS:
        raise AuditError("backend package identity drift")
    expected_scalars = {
        "schema_version": "tuc.backend_integration_package.v0",
        "package_version": "0.1.0",
        "interface_contract": "backend_integration.data_only.v0",
        "package_policy": "capability_and_planning_conformance_only",
        "import_policy": "no_import_or_plugin_discovery",
        "backend_code_included": False,
        "execution_permission": False,
    }
    for key, expected in expected_scalars.items():
        if package[key] != expected:
            raise AuditError("backend package policy drift")
    cases = package["conformance_cases"]
    if type(cases) is not list or len(cases) != 3:
        raise AuditError("backend conformance case drift")
    if _digest(package) != EXPECTED_PACKAGE_DIGESTS[package_id]:
        raise AuditError("backend package digest drift")
    return package


def _plan(
    source: dict[str, Any],
    packages: tuple[dict[str, Any], ...],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    capabilities = [package["capability_manifest"] for package in packages]
    layouts = {"lhs": "row_major", "rhs": "row_major"}
    producers: dict[str, str] = {"lhs": "external_input", "rhs": "external_input"}
    assignments: list[dict[str, object]] = []
    conversions: list[dict[str, str]] = []

    for operation in source["operations"]:
        family = operation["family"]
        candidates = [
            capability
            for capability in capabilities
            if family in capability["supported_ops"]
            and family in capability["preferred_for"]
        ]
        if len(candidates) != 1:
            raise AuditError("operation does not have one preferred backend")
        capability = candidates[0]
        accepted_layouts = capability["supported_layouts"]
        if type(accepted_layouts) is not list or len(accepted_layouts) != 1:
            raise AuditError("backend layout contract drift")
        accepted_layout = accepted_layouts[0]
        for input_name in operation["inputs"]:
            current_layout = layouts[input_name]
            if current_layout != accepted_layout:
                conversions.append(
                    {
                        "consumer": operation["name"],
                        "from_layout": current_layout,
                        "producer": producers[input_name],
                        "tensor": input_name,
                        "to_layout": accepted_layout,
                    }
                )
                layouts[input_name] = accepted_layout
        produced_layouts = capability["produced_layouts"]
        if type(produced_layouts) is not list or len(produced_layouts) != 1:
            raise AuditError("backend produced-layout contract drift")
        output_layout = produced_layouts[0]
        assignments.append(
            {
                "backend": capability["name"],
                "family": family,
                "operation": operation["name"],
                "output_layout": output_layout,
            }
        )
        for output_name in operation["outputs"]:
            layouts[output_name] = output_layout
            producers[output_name] = operation["name"]

    if [item["backend"] for item in assignments] != [
        "external-systolic",
        "external-vector",
    ]:
        raise AuditError("backend sequence drift")
    if conversions != [
        {
            "consumer": "activation",
            "from_layout": "blocked",
            "producer": "projection",
            "tensor": "projection",
            "to_layout": "row_major",
        }
    ]:
        raise AuditError("layout conversion drift")
    return assignments, conversions


def _execute(source: dict[str, Any], vector: dict[str, Any]) -> dict[str, object]:
    inputs = vector["inputs"]
    values: dict[str, list[list[float]]] = {
        "lhs": _matrix(inputs["lhs"]),
        "rhs": _matrix(inputs["rhs"]),
    }
    for operation in source["operations"]:
        family = operation["family"]
        output_name = operation["outputs"][0]
        if family == "matmul":
            values[output_name] = _matmul(
                values[operation["inputs"][0]],
                values[operation["inputs"][1]],
            )
        elif family == "elementwise":
            if vector["elementwise_semantics"] != "identity":
                raise AuditError("elementwise semantics drift")
            values[output_name] = [row[:] for row in values[operation["inputs"][0]]]
        else:
            raise AuditError("unsupported operation family")
    return {
        item["public_name"]: values[item["tensor_name"]]
        for item in source["returns"]
        if item["required"] is True
    }


def _matrix(value: object) -> list[list[float]]:
    if type(value) is not list or len(value) != 2:
        raise AuditError("matrix shape drift")
    matrix: list[list[float]] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise AuditError("matrix shape drift")
        converted: list[float] = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(float(item)):
                raise AuditError("matrix value drift")
            converted.append(float(item))
        matrix.append(converted)
    return matrix


def _matmul(lhs: list[list[float]], rhs: list[list[float]]) -> list[list[float]]:
    return [
        [sum(lhs[row][k] * rhs[k][column] for k in range(2)) for column in range(2)]
        for row in range(2)
    ]


def _load_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise AuditError("symbolic links are not accepted")
    stat_result = path.stat()
    if not path.is_file() or stat_result.st_size > MAX_JSON_BYTES:
        raise AuditError("JSON input boundary rejected")
    raw = path.read_bytes()
    if len(raw) != stat_result.st_size or len(raw) > MAX_JSON_BYTES:
        raise AuditError("JSON input changed while reading")
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_object_without_duplicates,
        parse_constant=_reject_non_finite,
    )
    if type(payload) is not dict:
        raise AuditError("JSON input must be an object")
    return payload


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate JSON key")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise AuditError(f"non-finite JSON number rejected: {value}")


def _digest(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    raise SystemExit(main())
