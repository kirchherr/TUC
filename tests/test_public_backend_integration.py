from __future__ import annotations

import ast
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tuc.integration import (
    BACKEND_INTEGRATION_CLI_NAME,
    BACKEND_INTEGRATION_PUBLIC_API_VERSION,
    dump_verified_backend_package,
    main,
    verify_backend_package,
)

CONSUMER_ROOT = Path("integration/objective_gamma")
PACKAGE_PATH = CONSUMER_ROOT / "backend_package.v0.json"
EXPECTED_REPORT_PATH = CONSUMER_ROOT / "expected_report.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_backend_integration_api_matches_external_golden() -> None:
    report = verify_backend_package(PACKAGE_PATH)
    report_text = dump_verified_backend_package(PACKAGE_PATH)

    assert report.integration_status == "PASS"
    assert report_text == EXPECTED_REPORT_PATH.read_text(encoding="utf-8")
    assert BACKEND_INTEGRATION_PUBLIC_API_VERSION == (
        "tuc.backend_integration_public_api.v0"
    )


def test_public_backend_integration_cli_emits_external_golden(
    capfd: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(PACKAGE_PATH)])
    captured = capfd.readouterr()

    assert exit_code == 0
    assert captured.out == EXPECTED_REPORT_PATH.read_text(encoding="utf-8")
    assert captured.err == ""


def test_public_backend_integration_cli_rejects_without_input_disclosure(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    rejected_path = tmp_path / "private-backend-package.json"
    rejected_path.write_text(
        json.dumps({"api_key": "PRIVATE_TEST_VALUE_SHOULD_NOT_APPEAR"}),
        encoding="utf-8",
    )

    exit_code = main([str(rejected_path)])
    captured = capfd.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "tuc-backend-verify: package rejected\n"
    assert str(rejected_path) not in captured.err
    assert "PRIVATE_TEST_VALUE" not in captured.err
    assert "api_key" not in captured.err


@pytest.mark.parametrize("arguments", ([], ["one.json", "two.json"]))
def test_public_backend_integration_cli_rejects_ambiguous_arity(
    arguments: list[str],
    capfd: pytest.CaptureFixture[str],
) -> None:
    assert main(arguments) == 2
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == "usage: tuc-backend-verify PACKAGE.json\n"


def test_public_backend_integration_cli_has_bounded_help(
    capfd: pytest.CaptureFixture[str],
) -> None:
    assert main(["--help"]) == 0
    captured = capfd.readouterr()
    assert captured.out == "usage: tuc-backend-verify PACKAGE.json\n"
    assert captured.err == ""


def test_objective_gamma_consumer_uses_only_public_tuc_surface() -> None:
    source = (CONSUMER_ROOT / "consumer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imports == {"pathlib", "tuc.integration"}
    assert "examples" not in source
    assert "tests" not in source
    assert "tuc.backends" not in source


def test_objective_gamma_files_are_plain_non_symlink_files() -> None:
    for path in (
        CONSUMER_ROOT / "consumer.py",
        PACKAGE_PATH,
        EXPECTED_REPORT_PATH,
    ):
        assert path.is_file()
        assert not path.is_symlink()


def test_wheel_registers_public_backend_verifier_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"][BACKEND_INTEGRATION_CLI_NAME] == (
        "tuc.integration:main"
    )


def test_built_wheel_runs_standalone_external_consumer(tmp_path: Path) -> None:
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
            str(PROJECT_ROOT / "scripts" / "verify_external_backend_consumer.py"),
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
        timeout=180,
    )
