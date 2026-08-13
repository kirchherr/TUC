"""Installed hardware-neutral compute proof over trusted prototype executors."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path

import numpy as np

from tuc.backends.integration_package import (
    BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    BackendIntegrationPackage,
    assert_backend_integration_package,
    dump_backend_integration_package_report,
    evaluate_backend_integration_package,
    load_backend_integration_package,
)
from tuc.compiler import compile_graph
from tuc.frontend.source_intent import SOURCE_INTENT_IR_CONTRACT
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)
from tuc.frontend.source_intent_metadata import source_intent_to_triton_metadata
from tuc.frontend.source_intent_returns import source_intent_return_aliases
from tuc.ir.dialect import HAC_IR_DIALECT_VERSION
from tuc.ir.modules import IRStage
from tuc.manifests import ManifestError, load_json_manifest
from tuc.report_output import (
    PublicReportOutputError,
    emit_public_json_report,
    emit_public_text_report,
)
from tuc.runtime.backend_equivalence import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    assert_runtime_backend_equivalence,
    build_runtime_backend_equivalence_report,
    dump_runtime_backend_equivalence_report,
)
from tuc.runtime.backend_package_execution import (
    BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
    build_backend_package_execution_admission_report,
)
from tuc.runtime.backend_package_execution_portfolio import (
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
    build_backend_package_execution_portfolio_admission,
    build_backend_package_execution_portfolio_report,
    dump_backend_package_execution_portfolio_report,
    execute_backend_package_execution_portfolio,
)
from tuc.runtime.dump import dump_partition_plan
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    execute_graph,
)
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT,
    assert_runtime_output_contract,
    build_runtime_output_contract_report,
)
from tuc.runtime.public_output_bundle import (
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    assert_runtime_public_output_bundle,
    build_runtime_public_output_bundle,
    dump_runtime_public_output_bundle_report,
)
from tuc.runtime.reference_correctness import (
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    assert_runtime_reference_correctness,
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
)

PORTABLE_COMPUTE_PUBLIC_API_VERSION = "tuc.portable_compute_public_api.v0"
PORTABLE_COMPUTE_CLI_NAME = "tuc-prove-portable-compute"
PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION = "tuc.portable_compute_proof_report.v0"
PORTABLE_COMPUTE_PROOF_CONTRACT = "portable_compute.installed_trusted_projection.v0"
PORTABLE_COMPUTE_PROOF_CLAIM = (
    "neutral_source_intent_preserves_observable_semantics_across_external_capabilities"
)
PORTABLE_COMPUTE_PROOF_STATUS = "PASS"
PORTABLE_COMPUTE_INPUT_POLICY = "fixed_internal_test_vectors_not_serialized"
PORTABLE_COMPUTE_RAW_VALUE_POLICY = "omitted_by_policy"
MAX_PORTABLE_COMPUTE_SOURCE_INTENT_BYTES = 64 * 1024
MAX_PORTABLE_COMPUTE_REPORT_BYTES = 64 * 1024

PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS = (
    "external-systolic-reference-package",
    "external-vector-reference-package",
)
PORTABLE_COMPUTE_REQUIRED_PACKAGE_DIGESTS = {
    "external-systolic-reference-package": (
        "sha256:806813974dfde16b46f694566d751b18780d5e43d8455467bf4e5d7ea38b452c"
    ),
    "external-vector-reference-package": (
        "sha256:bf4bf333025a176f20ad927c249747f6ce923e14f224f4cd94ed769d893288ee"
    ),
}
PORTABLE_COMPUTE_BLOCKED_CLAIMS = (
    "general_source_parser",
    "source_text_execution",
    "external_package_code_execution",
    "external_plugin_execution",
    "native_backend_execution",
    "physical_device_residency",
    "native_performance_parity",
)
PORTABLE_COMPUTE_FORBIDDEN_FRAGMENTS = (
    '"backend_artifact":',
    '"command":',
    '"device_id":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_path":',
    '"source_text":',
    '"tensor_values":',
)

_CLI_USAGE = (
    "usage: tuc-prove-portable-compute "
    "SOURCE_INTENT.json PACKAGE_A.json PACKAGE_B.json\n"
)
_CLI_REJECTION = "tuc-prove-portable-compute: proof rejected\n"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "backend_equivalence_contract",
        "backend_equivalence_digest",
        "backend_equivalence_passed",
        "backend_integration_contract",
        "blocked_claims",
        "blocked_execution_surfaces",
        "execution_step_count",
        "external_package_code_executed",
        "external_plugin_execution",
        "fallback_assignment_count",
        "hac_ir_contract",
        "hac_ir_digest",
        "input_value_policy",
        "input_values_serialized",
        "layout_conversion_count",
        "module_name",
        "operation_families",
        "output_contract",
        "package_admission_contract",
        "package_backend_sequence",
        "package_digests",
        "package_ids",
        "package_integration_digests",
        "physical_device_execution",
        "portfolio_contract",
        "portfolio_report_digest",
        "projected_plan_digest",
        "proof_claim",
        "proof_contract",
        "proof_status",
        "public_api_version",
        "public_output_bundle_contract",
        "public_output_bundle_digest",
        "public_output_names",
        "raw_tensor_value_policy",
        "raw_tensor_values_serialized",
        "reference_correctness_contract",
        "reference_correctness_digest",
        "reference_correctness_passed",
        "schema_version",
        "source_intent_contract",
        "source_intent_digest",
        "source_intent_payload_serialized",
        "source_plan_digest",
        "source_text_executed",
        "terminal_output_names",
        "trusted_executor_registry",
        "trusted_executor_sequence",
        "trusted_projection_execution",
    }
)


class PortableComputeProofError(ValueError):
    """Raised when the bounded installed compute proof cannot be established."""


def prove_portable_compute(
    source_intent_path: str | Path,
    backend_package_paths: Sequence[str | Path],
) -> dict[str, object]:
    """Run the bounded neutral-intent proof through trusted executors."""

    source_data = load_json_manifest(
        source_intent_path,
        max_bytes=MAX_PORTABLE_COMPUTE_SOURCE_INTENT_BYTES,
    )
    if source_data != _expected_source_intent_data():
        raise PortableComputeProofError("portable compute Source Intent slice mismatch")
    module = source_intent_from_mapping(source_data)
    packages = _load_required_packages(backend_package_paths)
    integration_reports = tuple(
        evaluate_backend_integration_package(package) for package in packages
    )
    for integration_report in integration_reports:
        assert_backend_integration_package(integration_report)
    admissions = tuple(
        build_backend_package_execution_admission_report(report)
        for report in integration_reports
    )
    portfolio = build_backend_package_execution_portfolio_admission(admissions)
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    compilation = compile_graph(graph, tuple(package.capability for package in packages))
    inputs = _proof_inputs()
    candidate = execute_backend_package_execution_portfolio(
        compilation.hac_ir.graph,
        compilation.partition_plan,
        inputs,
        portfolio,
    )
    baseline = compile_graph(graph, ())
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    backend_equivalence = assert_runtime_backend_equivalence(
        build_runtime_backend_equivalence_report(
            graph,
            baseline.partition_plan,
            baseline_execution,
            candidate.projected_partition_plan,
            candidate.execution,
            baseline_run_id="reference_cpu",
            candidate_run_id="installed_portable_compute",
        )
    )
    portfolio_report = build_backend_package_execution_portfolio_report(
        graph,
        candidate,
        backend_equivalence,
    )
    output_contract = assert_runtime_output_contract(
        build_runtime_output_contract_report(
            graph,
            candidate.execution,
            source_intent_return_aliases(module),
        )
    )
    public_output_bundle = assert_runtime_public_output_bundle(
        build_runtime_public_output_bundle(candidate.execution, output_contract)
    )
    reference_correctness = assert_runtime_reference_correctness(
        build_runtime_reference_correctness_report(
            graph,
            candidate.execution,
            {"activated": inputs["lhs"] @ inputs["rhs"]},
        )
    )

    report: dict[str, object] = {
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_digest": _digest(
            dump_runtime_backend_equivalence_report(backend_equivalence)
        ),
        "backend_equivalence_passed": backend_equivalence.passed,
        "backend_integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "execution_step_count": len(candidate.execution.trace.steps),
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": portfolio_report.fallback_assignment_count,
        "hac_ir_contract": HAC_IR_DIALECT_VERSION,
        "hac_ir_digest": _digest(compilation.dump(IRStage.HAC_IR)),
        "input_value_policy": PORTABLE_COMPUTE_INPUT_POLICY,
        "input_values_serialized": False,
        "layout_conversion_count": len(portfolio_report.layout_conversions),
        "module_name": module.name,
        "operation_families": [operation.family for operation in module.operations],
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "package_admission_contract": BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
        "package_backend_sequence": list(portfolio_report.source_backend_sequence),
        "package_digests": [package.package_digest for package in packages],
        "package_ids": [package.package_id for package in packages],
        "package_integration_digests": [
            _digest(dump_backend_integration_package_report(item))
            for item in integration_reports
        ],
        "physical_device_execution": False,
        "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
        "portfolio_report_digest": _digest(
            dump_backend_package_execution_portfolio_report(portfolio_report)
        ),
        "projected_plan_digest": _digest(
            dump_partition_plan(candidate.projected_partition_plan)
        ),
        "proof_claim": PORTABLE_COMPUTE_PROOF_CLAIM,
        "proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "proof_status": PORTABLE_COMPUTE_PROOF_STATUS,
        "public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_bundle_digest": _digest(
            dump_runtime_public_output_bundle_report(public_output_bundle)
        ),
        "public_output_names": list(public_output_bundle.public_output_names),
        "raw_tensor_value_policy": PORTABLE_COMPUTE_RAW_VALUE_POLICY,
        "raw_tensor_values_serialized": False,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(reference_correctness)
        ),
        "reference_correctness_passed": reference_correctness.passed,
        "schema_version": PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION,
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "source_intent_digest": _digest(module.dump()),
        "source_intent_payload_serialized": False,
        "source_plan_digest": _digest(dump_partition_plan(compilation.partition_plan)),
        "source_text_executed": False,
        "terminal_output_names": list(public_output_bundle.tensor_names),
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_executor_sequence": list(portfolio_report.projected_backend_sequence),
        "trusted_projection_execution": True,
    }
    return assert_portable_compute_proof_report(report)


def dump_portable_compute_proof(
    source_intent_path: str | Path,
    backend_package_paths: Sequence[str | Path],
) -> str:
    """Return stable metadata-only JSON for the installed compute proof."""

    text = json.dumps(
        prove_portable_compute(source_intent_path, backend_package_paths),
        indent=2,
        sort_keys=True,
    ) + "\n"
    if len(text.encode("utf-8")) > MAX_PORTABLE_COMPUTE_REPORT_BYTES:
        raise PortableComputeProofError("portable compute report exceeds size limit")
    return text


def emit_portable_compute_proof(
    source_intent_path: str | Path,
    backend_package_paths: Sequence[str | Path],
) -> None:
    """Emit the bounded installed compute proof through the public output boundary."""

    emit_public_json_report(
        dump_portable_compute_proof(source_intent_path, backend_package_paths)
    )


def assert_portable_compute_proof_report(report: object) -> dict[str, object]:
    """Fail closed unless a report matches the Objective Delta v0 claim."""

    if type(report) is not dict:
        raise TypeError("portable compute proof report must be plain object")
    normalized = report
    if frozenset(normalized) != _TOP_LEVEL_KEYS:
        raise PortableComputeProofError("portable compute proof report key drift")
    expected: dict[str, object] = {
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": True,
        "backend_integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "execution_step_count": 2,
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": 0,
        "hac_ir_contract": HAC_IR_DIALECT_VERSION,
        "input_value_policy": PORTABLE_COMPUTE_INPUT_POLICY,
        "input_values_serialized": False,
        "layout_conversion_count": 1,
        "module_name": "source_intent_backend_package_portfolio",
        "operation_families": ["matmul", "elementwise"],
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "package_admission_contract": BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
        "package_backend_sequence": ["external-systolic", "external-vector"],
        "package_digests": [
            PORTABLE_COMPUTE_REQUIRED_PACKAGE_DIGESTS[package_id]
            for package_id in PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS
        ],
        "package_ids": list(PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS),
        "physical_device_execution": False,
        "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
        "proof_claim": PORTABLE_COMPUTE_PROOF_CLAIM,
        "proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "proof_status": PORTABLE_COMPUTE_PROOF_STATUS,
        "public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_names": ["api_activated"],
        "raw_tensor_value_policy": PORTABLE_COMPUTE_RAW_VALUE_POLICY,
        "raw_tensor_values_serialized": False,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": True,
        "schema_version": PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION,
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "terminal_output_names": ["activated"],
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
        "trusted_projection_execution": True,
    }
    for key, expected_value in expected.items():
        if normalized[key] != expected_value:
            raise PortableComputeProofError(f"portable compute proof {key} drift")
    for key in (
        "backend_equivalence_digest",
        "hac_ir_digest",
        "portfolio_report_digest",
        "projected_plan_digest",
        "public_output_bundle_digest",
        "reference_correctness_digest",
        "source_intent_digest",
        "source_plan_digest",
    ):
        _assert_digest(normalized[key], key)
    integration_digests = normalized["package_integration_digests"]
    if type(integration_digests) is not list or len(integration_digests) != 2:
        raise PortableComputeProofError("portable compute package integration digest drift")
    for digest in integration_digests:
        _assert_digest(digest, "package integration digest")
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    for fragment in PORTABLE_COMPUTE_FORBIDDEN_FRAGMENTS:
        if fragment in encoded:
            raise PortableComputeProofError(
                "portable compute proof contains forbidden evidence surface"
            )
    return normalized


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded installed portable-compute CLI."""

    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments == ("--help",):
        emit_public_text_report(_CLI_USAGE)
        return 0
    if len(arguments) != 3:
        sys.stderr.write(_CLI_USAGE)
        return 2
    try:
        emit_portable_compute_proof(arguments[0], arguments[1:])
    except (
        ManifestError,
        OSError,
        PortableComputeProofError,
        PublicReportOutputError,
        TypeError,
        ValueError,
    ):
        sys.stderr.write(_CLI_REJECTION)
        return 2
    return 0


def _load_required_packages(
    backend_package_paths: Sequence[str | Path],
) -> tuple[BackendIntegrationPackage, ...]:
    if isinstance(backend_package_paths, (str, bytes)):
        raise TypeError("portable compute package paths must be a sequence")
    paths = tuple(backend_package_paths)
    if len(paths) != len(PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS):
        raise PortableComputeProofError("portable compute requires exactly two packages")
    packages_by_id: dict[str, BackendIntegrationPackage] = {}
    for path in paths:
        package = load_backend_integration_package(path)
        if package.package_id in packages_by_id:
            raise PortableComputeProofError("portable compute duplicate package id")
        expected_digest = PORTABLE_COMPUTE_REQUIRED_PACKAGE_DIGESTS.get(package.package_id)
        if expected_digest is None or package.package_digest != expected_digest:
            raise PortableComputeProofError("portable compute package identity mismatch")
        packages_by_id[package.package_id] = package
    if tuple(sorted(packages_by_id)) != tuple(sorted(PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS)):
        raise PortableComputeProofError("portable compute required package set mismatch")
    return tuple(packages_by_id[package_id] for package_id in PORTABLE_COMPUTE_REQUIRED_PACKAGE_IDS)


def _proof_inputs() -> dict[str, np.ndarray[tuple[int, ...], np.dtype[np.float64]]]:
    return {
        "lhs": np.array([[1.0, -2.0], [0.5, 3.0]], dtype=np.float64),
        "rhs": np.array([[2.0, 1.0], [-1.0, 0.25]], dtype=np.float64),
    }


def _expected_source_intent_data() -> dict[str, object]:
    return {
        "name": "source_intent_backend_package_portfolio",
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": [
            {"name": "lhs", "shape": [2, 2], "dtype": "float64"},
            {"name": "rhs", "shape": [2, 2], "dtype": "float64"},
            {"name": "projection", "shape": [2, 2], "dtype": "float64"},
            {"name": "activated", "shape": [2, 2], "dtype": "float64"},
        ],
        "operations": [
            {
                "name": "projection",
                "family": "matmul",
                "inputs": ["lhs", "rhs"],
                "outputs": ["projection"],
                "hints": {
                    "max_error_budget": 0.0,
                    "prefer_linear_accelerator": True,
                },
            },
            {
                "name": "activation",
                "family": "elementwise",
                "inputs": ["projection"],
                "outputs": ["activated"],
            },
        ],
        "returns": [
            {
                "public_name": "api_activated",
                "tensor_name": "activated",
                "required": True,
            }
        ],
    }


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise PortableComputeProofError(f"portable compute {label} drift")


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "PORTABLE_COMPUTE_CLI_NAME",
    "PORTABLE_COMPUTE_PROOF_CONTRACT",
    "PORTABLE_COMPUTE_PUBLIC_API_VERSION",
    "PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION",
    "PortableComputeProofError",
    "assert_portable_compute_proof_report",
    "dump_portable_compute_proof",
    "emit_portable_compute_proof",
    "main",
    "prove_portable_compute",
]


if __name__ == "__main__":
    raise SystemExit(main())
