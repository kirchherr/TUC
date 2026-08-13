"""Run the portable data-only Backend Integration Package v0 proof."""

from __future__ import annotations

from pathlib import Path

from tuc.backends.integration_package import (
    assert_backend_integration_package,
    dump_backend_integration_package_report,
    evaluate_backend_integration_package,
    load_backend_integration_package,
)

PACKAGE_PATH = (
    Path(__file__).with_name("backend_packages") / "external_vector.v0.json"
)


def build_report() -> str:
    """Return the deterministic reference backend integration report."""

    package = load_backend_integration_package(PACKAGE_PATH)
    report = evaluate_backend_integration_package(package)
    assert_backend_integration_package(report)
    return dump_backend_integration_package_report(report)


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
