"""Emit backend plugin fuzz and negative-test evidence."""

from tuc import (
    BackendPluginFuzzNegativeTestsReport,
    build_backend_plugin_fuzz_negative_tests_report,
    dump_backend_plugin_fuzz_negative_tests_report,
)


def build_current_backend_plugin_fuzz_negative_tests_report() -> (
    BackendPluginFuzzNegativeTestsReport
):
    """Return the current backend plugin fuzz/negative evidence report."""

    return build_backend_plugin_fuzz_negative_tests_report()


def main() -> None:
    report = build_current_backend_plugin_fuzz_negative_tests_report()
    print(dump_backend_plugin_fuzz_negative_tests_report(report), end="")


if __name__ == "__main__":
    main()
