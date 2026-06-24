"""Emit backend plugin resource budget evidence."""

from tuc import (
    BackendPluginResourceBudgetReport,
    build_backend_plugin_resource_budget_report,
    dump_backend_plugin_resource_budget_report,
)


def build_current_backend_plugin_resource_budget_report() -> (
    BackendPluginResourceBudgetReport
):
    """Return the current backend plugin resource budget report."""

    return build_backend_plugin_resource_budget_report()


def main() -> None:
    report = build_current_backend_plugin_resource_budget_report()
    print(dump_backend_plugin_resource_budget_report(report), end="")


if __name__ == "__main__":
    main()
