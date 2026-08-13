"""Emit the current backend plugin lifecycle blocking policy."""

from tuc import (
    BackendPluginLifecyclePolicyReport,
    build_backend_plugin_lifecycle_policy_report,
    dump_backend_plugin_lifecycle_policy_report,
)


def build_current_backend_plugin_lifecycle_policy_report() -> (
    BackendPluginLifecyclePolicyReport
):
    """Return the current executable backend plugin lifecycle policy report."""

    return build_backend_plugin_lifecycle_policy_report()


def main() -> None:
    report = build_current_backend_plugin_lifecycle_policy_report()
    print(dump_backend_plugin_lifecycle_policy_report(report), end="")


if __name__ == "__main__":
    main()
