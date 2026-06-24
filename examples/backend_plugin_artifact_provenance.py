"""Emit backend plugin artifact provenance evidence."""

from tuc import (
    BackendPluginArtifactProvenanceReport,
    build_backend_plugin_artifact_provenance_report,
    dump_backend_plugin_artifact_provenance_report,
)


def build_current_backend_plugin_artifact_provenance_report() -> (
    BackendPluginArtifactProvenanceReport
):
    """Return the current backend plugin artifact provenance report."""

    return build_backend_plugin_artifact_provenance_report()


def main() -> None:
    report = build_current_backend_plugin_artifact_provenance_report()
    print(dump_backend_plugin_artifact_provenance_report(report), end="")


if __name__ == "__main__":
    main()
