"""Emit Runtime Transfer Trace Replay Verifier v0."""

from examples.runtime_transfer_evidence import (
    build_current_runtime_transfer_evidence_report,
)
from examples.runtime_transfer_trace_index import (
    build_current_runtime_transfer_trace_index_report,
)
from tuc.runtime.transfer_evidence import dump_runtime_transfer_evidence_report
from tuc.runtime.transfer_trace_index import dump_runtime_transfer_trace_index_report
from tuc.runtime.transfer_trace_replay_verifier import (
    RuntimeTransferTraceReplayVerifierReport,
    build_runtime_transfer_trace_replay_verifier_report,
    dump_runtime_transfer_trace_replay_verifier_report,
)


def build_transfer_trace_replay_verifier_report() -> (
    RuntimeTransferTraceReplayVerifierReport
):
    """Return the current metadata-only transfer trace replay verifier report."""

    evidence_text = dump_runtime_transfer_evidence_report(
        build_current_runtime_transfer_evidence_report()
    )
    trace_index_text = dump_runtime_transfer_trace_index_report(
        build_current_runtime_transfer_trace_index_report()
    )
    return build_runtime_transfer_trace_replay_verifier_report(
        evidence_text,
        trace_index_text,
    )


def build_report() -> str:
    """Return the stable serialized runtime transfer trace replay verifier report."""

    return dump_runtime_transfer_trace_replay_verifier_report(
        build_transfer_trace_replay_verifier_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
