"""Emit Runtime Layout Conversion Trace Replay Verifier v0."""

from examples.runtime_layout_conversion_evidence import (
    build_current_runtime_layout_conversion_evidence_report,
)
from examples.runtime_layout_conversion_trace_index import (
    build_current_runtime_layout_conversion_trace_index_report,
)
from tuc.runtime.layout_conversion_evidence import (
    dump_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.layout_conversion_trace_index import (
    dump_runtime_layout_conversion_trace_index_report,
)
from tuc.runtime.layout_conversion_trace_replay_verifier import (
    RuntimeLayoutConversionTraceReplayVerifierReport,
    build_runtime_layout_conversion_trace_replay_verifier_report,
    dump_runtime_layout_conversion_trace_replay_verifier_report,
)


def build_layout_conversion_trace_replay_verifier_report() -> (
    RuntimeLayoutConversionTraceReplayVerifierReport
):
    """Return the current layout-conversion trace replay verifier report."""

    evidence_text = dump_runtime_layout_conversion_evidence_report(
        build_current_runtime_layout_conversion_evidence_report()
    )
    trace_index_text = dump_runtime_layout_conversion_trace_index_report(
        build_current_runtime_layout_conversion_trace_index_report()
    )
    return build_runtime_layout_conversion_trace_replay_verifier_report(
        evidence_text,
        trace_index_text,
    )


def build_report() -> str:
    """Return stable serialized layout-conversion trace replay verification."""

    return dump_runtime_layout_conversion_trace_replay_verifier_report(
        build_layout_conversion_trace_replay_verifier_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
