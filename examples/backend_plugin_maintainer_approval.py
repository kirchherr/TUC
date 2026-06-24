"""Emit backend plugin maintainer approval evidence."""

from tuc import (
    BackendPluginMaintainerApprovalReport,
    build_backend_plugin_maintainer_approval_report,
    dump_backend_plugin_maintainer_approval_report,
)


def build_current_backend_plugin_maintainer_approval_report() -> (
    BackendPluginMaintainerApprovalReport
):
    """Return the current backend plugin maintainer approval report."""

    return build_backend_plugin_maintainer_approval_report()


def main() -> None:
    report = build_current_backend_plugin_maintainer_approval_report()
    print(dump_backend_plugin_maintainer_approval_report(report), end="")


if __name__ == "__main__":
    main()
