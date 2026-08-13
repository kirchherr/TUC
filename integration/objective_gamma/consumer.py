"""Standalone Objective Gamma consumer using only TUC's public API."""

from pathlib import Path

from tuc.integration import emit_verified_backend_package

PACKAGE_PATH = Path(__file__).resolve().with_name("backend_package.v0.json")


if __name__ == "__main__":
    emit_verified_backend_package(PACKAGE_PATH)
