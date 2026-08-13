"""Emit the current backend plugin sandbox model."""

from tuc import (
    BackendPluginSandboxModelReport,
    build_backend_plugin_sandbox_model_report,
    dump_backend_plugin_sandbox_model_report,
)


def build_current_backend_plugin_sandbox_model_report() -> (
    BackendPluginSandboxModelReport
):
    """Return the current backend plugin sandbox model report."""

    return build_backend_plugin_sandbox_model_report()


def main() -> None:
    report = build_current_backend_plugin_sandbox_model_report()
    print(dump_backend_plugin_sandbox_model_report(report), end="")


if __name__ == "__main__":
    main()
