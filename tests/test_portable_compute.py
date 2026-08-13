from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from tuc.portable_compute import (
    PORTABLE_COMPUTE_CLI_NAME,
    PORTABLE_COMPUTE_PROOF_CONTRACT,
    PORTABLE_COMPUTE_PUBLIC_API_VERSION,
    PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION,
    PortableComputeProofError,
    assert_portable_compute_proof_report,
    dump_portable_compute_proof,
    main,
    prove_portable_compute,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONSUMER_ROOT = Path("integration/objective_delta")
SOURCE_INTENT_PATH = CONSUMER_ROOT / "source_intent.v0.json"
SYSTOLIC_PACKAGE_PATH = CONSUMER_ROOT / "external_systolic.v0.json"
VECTOR_PACKAGE_PATH = CONSUMER_ROOT / "external_vector.v0.json"
EXPECTED_REPORT_PATH = CONSUMER_ROOT / "expected_report.json"
SCHEMA_PATH = Path("schemas/portable_compute_proof_report.v0.schema.json")


def test_portable_compute_proves_mixed_trusted_execution() -> None:
    report = prove_portable_compute(
        SOURCE_INTENT_PATH,
        (VECTOR_PACKAGE_PATH, SYSTOLIC_PACKAGE_PATH),
    )

    assert report["proof_status"] == "PASS"
    assert report["proof_contract"] == PORTABLE_COMPUTE_PROOF_CONTRACT
    assert report["public_api_version"] == PORTABLE_COMPUTE_PUBLIC_API_VERSION
    assert report["package_backend_sequence"] == [
        "external-systolic",
        "external-vector",
    ]
    assert report["trusted_executor_sequence"] == ["systolic-sim", "vector-sim"]
    assert report["fallback_assignment_count"] == 0
    assert report["layout_conversion_count"] == 1
    assert report["reference_correctness_passed"] is True
    assert report["backend_equivalence_passed"] is True
    assert report["external_package_code_executed"] is False
    assert report["physical_device_execution"] is False


def test_portable_compute_report_matches_external_golden() -> None:
    assert dump_portable_compute_proof(
        SOURCE_INTENT_PATH,
        (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH),
    ) == EXPECTED_REPORT_PATH.read_text(encoding="utf-8")


def test_portable_compute_package_argument_order_is_canonical() -> None:
    canonical = dump_portable_compute_proof(
        SOURCE_INTENT_PATH,
        (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH),
    )
    reversed_order = dump_portable_compute_proof(
        SOURCE_INTENT_PATH,
        (VECTOR_PACKAGE_PATH, SYSTOLIC_PACKAGE_PATH),
    )

    assert canonical == reversed_order


def test_portable_compute_rejects_source_intent_drift(tmp_path: Path) -> None:
    payload = _load_json(SOURCE_INTENT_PATH)
    payload["name"] = "almost_the_same_proof"
    drifted = tmp_path / "source_intent.json"
    drifted.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PortableComputeProofError, match="slice mismatch"):
        prove_portable_compute(
            drifted,
            (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH),
        )


def test_portable_compute_rejects_package_identity_drift(tmp_path: Path) -> None:
    payload = _load_json(SYSTOLIC_PACKAGE_PATH)
    payload["package_version"] = "0.1.1"
    drifted = tmp_path / "external_systolic.json"
    drifted.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PortableComputeProofError, match="identity mismatch"):
        prove_portable_compute(
            SOURCE_INTENT_PATH,
            (drifted, VECTOR_PACKAGE_PATH),
        )


def test_portable_compute_rejects_duplicate_package() -> None:
    with pytest.raises(PortableComputeProofError, match="duplicate package"):
        prove_portable_compute(
            SOURCE_INTENT_PATH,
            (VECTOR_PACKAGE_PATH, VECTOR_PACKAGE_PATH),
        )


def test_portable_compute_report_assertion_rejects_claim_drift() -> None:
    report = prove_portable_compute(
        SOURCE_INTENT_PATH,
        (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH),
    )
    drifted = deepcopy(report)
    drifted["external_plugin_execution"] = True

    with pytest.raises(PortableComputeProofError, match="external_plugin_execution"):
        assert_portable_compute_proof_report(drifted)


def test_portable_compute_report_omits_sensitive_surfaces() -> None:
    text = EXPECTED_REPORT_PATH.read_text(encoding="utf-8")

    for fragment in (
        '"backend_artifact":',
        '"command":',
        '"device_id":',
        '"host_path":',
        '"plugin_entrypoint":',
        '"raw_tensor_value":',
        '"runtime_handle":',
        '"source_intent_payload":',
        '"source_path":',
        '"source_text":',
    ):
        assert fragment not in text


def test_portable_compute_cli_emits_external_golden(
    capfd: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            str(SOURCE_INTENT_PATH),
            str(SYSTOLIC_PACKAGE_PATH),
            str(VECTOR_PACKAGE_PATH),
        ]
    )
    captured = capfd.readouterr()

    assert exit_code == 0
    assert captured.out == EXPECTED_REPORT_PATH.read_text(encoding="utf-8")
    assert captured.err == ""


def test_portable_compute_cli_rejects_without_input_disclosure(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    private_path = tmp_path / "private-source-intent.json"
    private_path.write_text('{"secret":"DO_NOT_LOG_THIS"}', encoding="utf-8")

    exit_code = main(
        [str(private_path), str(SYSTOLIC_PACKAGE_PATH), str(VECTOR_PACKAGE_PATH)]
    )
    captured = capfd.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "tuc-prove-portable-compute: proof rejected\n"
    assert str(private_path) not in captured.err
    assert "DO_NOT_LOG_THIS" not in captured.err


@pytest.mark.parametrize("arguments", ([], ["one.json"], ["a", "b", "c", "d"]))
def test_portable_compute_cli_rejects_ambiguous_arity(
    arguments: list[str],
    capfd: pytest.CaptureFixture[str],
) -> None:
    assert main(arguments) == 2
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "usage: tuc-prove-portable-compute "
        "SOURCE_INTENT.json PACKAGE_A.json PACKAGE_B.json\n"
    )


def test_portable_compute_module_entrypoint_matches_golden() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tuc.portable_compute",
            str(SOURCE_INTENT_PATH),
            str(SYSTOLIC_PACKAGE_PATH),
            str(VECTOR_PACKAGE_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.stderr == ""
    assert completed.stdout == EXPECTED_REPORT_PATH.read_text(encoding="utf-8")


def test_objective_delta_consumer_uses_only_public_tuc_surface() -> None:
    source = (CONSUMER_ROOT / "consumer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imports == {"pathlib", "tuc.portable_compute"}
    assert "examples" not in source
    assert "tests" not in source
    assert "tuc.runtime" not in source
    assert "tuc.backends" not in source


def test_wheel_registers_portable_compute_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"][PORTABLE_COMPUTE_CLI_NAME] == (
        "tuc.portable_compute:main"
    )


def test_portable_compute_schema_is_closed_and_matches_golden() -> None:
    schema = _load_json(SCHEMA_PATH)
    report = _load_json(EXPECTED_REPORT_PATH)

    assert schema["additionalProperties"] is False
    assert set(cast(list[str], schema["required"])) == set(report)
    assert schema["properties"]["schema_version"]["const"] == (
        PORTABLE_COMPUTE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["proof_status"]["const"] == "PASS"
    assert schema["properties"]["external_package_code_executed"]["const"] is False
    assert schema["properties"]["raw_tensor_values_serialized"]["const"] is False


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        (
            Path("docs/OBJECTIVE_DELTA_INSTALLED_PORTABLE_COMPUTE.md"),
            "# Objective Delta Installed Portable Compute",
        ),
        (
            Path("rfcs/0292-objective-delta-installed-portable-compute.md"),
            "# RFC 0292: Objective Delta Installed Portable Compute",
        ),
        (Path("README.md"), "Objective Delta Installed Portable Compute"),
        (Path("ROADMAP.md"), "Objective Delta v0 semantic integration"),
        (Path("TUC_MASTER_PLAN.md"), "### Objective Delta"),
        (Path("docs/ROADMAP_STATUS.md"), "Objective Delta Installed Portable Compute"),
        (Path("docs/BACKEND_API.md"), "Objective Delta adds a separate installed"),
    ),
)
def test_objective_delta_is_bound_into_project_guidance(
    path: Path,
    marker: str,
) -> None:
    assert marker in path.read_text(encoding="utf-8")


def test_delta_verifier_rejects_unexpected_consumer_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _load_delta_verifier(monkeypatch)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    for filename in verifier.OBJECTIVE_DELTA_CONSUMER_FILES:
        (consumer / filename).write_bytes((CONSUMER_ROOT / filename).read_bytes())
    (consumer / "unexpected.py").write_text("raise SystemExit(1)\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file set changed"):
        verifier._validate_consumer_tree(consumer)


def test_built_wheel_runs_objective_delta_consumer(tmp_path: Path) -> None:
    wheel_directory = tmp_path / "wheel"
    wheel_directory.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheel_directory),
        ],
        check=True,
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=120,
    )
    wheels = tuple(wheel_directory.glob("*.whl"))
    assert len(wheels) == 1

    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_external_portable_compute_consumer.py"),
            "--wheel",
            str(wheels[0]),
            "--consumer",
            str(PROJECT_ROOT / CONSUMER_ROOT),
            "--source-root",
            str(PROJECT_ROOT),
        ],
        check=True,
        cwd=tmp_path,
        capture_output=True,
        timeout=240,
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict:
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], payload)


def _load_delta_verifier(monkeypatch: pytest.MonkeyPatch) -> Any:
    scripts = PROJECT_ROOT / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    script_path = scripts / "verify_external_portable_compute_consumer.py"
    spec = importlib.util.spec_from_file_location("objective_delta_verifier", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
