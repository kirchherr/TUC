"""Emit backend-equivalence evidence bound to transfer trace replay."""

from examples.runtime_backend_equivalence import (
    build_backend_equivalence_report,
)
from examples.runtime_transfer_trace_replay_verifier import (
    build_transfer_trace_replay_verifier_report,
)
from tuc.report_output import emit_public_json_report
from tuc.runtime.backend_equivalence import dump_runtime_backend_equivalence_report
from tuc.runtime.backend_equivalence_transfer_binding import (
    RuntimeBackendEquivalenceTransferBindingReport,
    build_runtime_backend_equivalence_transfer_binding_report,
    dump_runtime_backend_equivalence_transfer_binding_report,
)
from tuc.runtime.transfer_trace_replay_verifier import (
    dump_runtime_transfer_trace_replay_verifier_report,
)


def build_backend_equivalence_transfer_binding_report() -> (
    RuntimeBackendEquivalenceTransferBindingReport
):
    """Return the current backend-equivalence/transfer binding report."""

    equivalence_text = dump_runtime_backend_equivalence_report(
        build_backend_equivalence_report()
    )
    replay_text = dump_runtime_transfer_trace_replay_verifier_report(
        build_transfer_trace_replay_verifier_report()
    )
    return build_runtime_backend_equivalence_transfer_binding_report(
        equivalence_text,
        replay_text,
    )


def build_report() -> str:
    """Return stable serialized backend-equivalence/transfer binding evidence."""

    return dump_runtime_backend_equivalence_transfer_binding_report(
        build_backend_equivalence_transfer_binding_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
