"""Emit backend-equivalence evidence bound to layout trace replay."""

from examples.runtime_layout_conversion_trace_replay_verifier import (
    build_layout_conversion_trace_replay_verifier_report,
)
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from tuc.runtime.backend_equivalence import dump_runtime_backend_equivalence_report
from tuc.runtime.backend_equivalence_layout_binding import (
    RuntimeBackendEquivalenceLayoutBindingReport,
    build_runtime_backend_equivalence_layout_binding_report,
    dump_runtime_backend_equivalence_layout_binding_report,
)
from tuc.runtime.layout_conversion_trace_replay_verifier import (
    dump_runtime_layout_conversion_trace_replay_verifier_report,
)


def build_backend_equivalence_layout_binding_report() -> (
    RuntimeBackendEquivalenceLayoutBindingReport
):
    """Return the current backend-equivalence/layout binding report."""

    equivalence_text = dump_runtime_backend_equivalence_report(
        build_mixed_backend_equivalence_report()
    )
    replay_text = dump_runtime_layout_conversion_trace_replay_verifier_report(
        build_layout_conversion_trace_replay_verifier_report()
    )
    return build_runtime_backend_equivalence_layout_binding_report(
        equivalence_text,
        replay_text,
    )


def build_report() -> str:
    """Return stable serialized backend-equivalence/layout binding evidence."""

    return dump_runtime_backend_equivalence_layout_binding_report(
        build_backend_equivalence_layout_binding_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
