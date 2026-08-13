"""Stable public entry points for data-only TUC backend integration."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from tuc.backends.integration_package import (
    BackendIntegrationPackageError,
    BackendIntegrationPackageReport,
    assert_backend_integration_package,
    dump_backend_integration_package_report,
    evaluate_backend_integration_package,
    load_backend_integration_package,
)
from tuc.manifests import ManifestError
from tuc.report_output import (
    PublicReportOutputError,
    emit_public_json_report,
    emit_public_text_report,
)

BACKEND_INTEGRATION_PUBLIC_API_VERSION = "tuc.backend_integration_public_api.v0"
BACKEND_INTEGRATION_CLI_NAME = "tuc-backend-verify"

_CLI_USAGE = "usage: tuc-backend-verify PACKAGE.json\n"
_CLI_REJECTION = "tuc-backend-verify: package rejected\n"


def verify_backend_package(path: str | Path) -> BackendIntegrationPackageReport:
    """Verify one explicit data-only backend package and fail closed on mismatch."""

    package = load_backend_integration_package(path)
    report = evaluate_backend_integration_package(package)
    assert_backend_integration_package(report)
    return report


def dump_verified_backend_package(path: str | Path) -> str:
    """Return the deterministic public report for one verified package."""

    return dump_backend_integration_package_report(verify_backend_package(path))


def emit_verified_backend_package(path: str | Path) -> None:
    """Verify and emit one report through TUC's public output boundary."""

    emit_public_json_report(dump_verified_backend_package(path))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded backend-package verifier console entry point."""

    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments == ("--help",):
        emit_public_text_report(_CLI_USAGE)
        return 0
    if len(arguments) != 1:
        sys.stderr.write(_CLI_USAGE)
        return 2
    try:
        emit_verified_backend_package(arguments[0])
    except (
        BackendIntegrationPackageError,
        ManifestError,
        OSError,
        PublicReportOutputError,
    ):
        # Rejections never echo an untrusted path, payload, or parser detail.
        sys.stderr.write(_CLI_REJECTION)
        return 2
    return 0


__all__ = [
    "BACKEND_INTEGRATION_CLI_NAME",
    "BACKEND_INTEGRATION_PUBLIC_API_VERSION",
    "BackendIntegrationPackageReport",
    "dump_verified_backend_package",
    "emit_verified_backend_package",
    "main",
    "verify_backend_package",
]
