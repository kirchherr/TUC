"""Emit external frontend package conformance evidence."""

from __future__ import annotations

try:
    from examples.source_intent_frontend_conformance import (
        build_source_intent_frontend_conformance_cases,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_intent_frontend_conformance import (  # type: ignore[no-redef]
        build_source_intent_frontend_conformance_cases,
    )

from tuc.frontend import (
    build_external_frontend_package_conformance_report,
    default_external_frontend_package_manifest,
    dump_external_frontend_package_conformance_report,
)


def build_current_external_frontend_package_conformance_report():
    """Build the current data-only external frontend package conformance report."""

    return build_external_frontend_package_conformance_report(
        default_external_frontend_package_manifest(),
        build_source_intent_frontend_conformance_cases(),
    )


def build_report() -> str:
    """Return stable external frontend package conformance evidence."""

    return dump_external_frontend_package_conformance_report(
        build_current_external_frontend_package_conformance_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
