"""Emit a diagnostic versioned toolchain-environment report."""

from tuc import (
    ToolchainComponent,
    build_toolchain_environment_report,
    dump_toolchain_environment_report,
)


def main() -> None:
    report = build_toolchain_environment_report(
        "phase1_toolchain_environment_candidate",
        components=(
            ToolchainComponent(
                component_id="python_runtime",
                component_kind="python_runtime",
                version_id="python_3.11",
                provenance_id="docker_dev_container",
            ),
            ToolchainComponent(
                component_id="numpy_package",
                component_kind="python_package",
                version_id="numpy_runtime_version",
                provenance_id="pyproject_dependency_set",
            ),
        ),
    )
    print(dump_toolchain_environment_report(report), end="")


if __name__ == "__main__":
    main()
