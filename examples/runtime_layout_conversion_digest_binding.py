"""Emit Runtime Layout Conversion Digest Binding Report v0."""

from __future__ import annotations

try:
    from examples.runtime_hs_ir_plan_alignment import build_alignment_report
    from examples.runtime_layout_conversion_evidence import (
        build_current_runtime_layout_conversion_evidence_report,
    )
    from examples.runtime_mixed_tensor_store_evidence import (
        build_mixed_tensor_store_evidence_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_hs_ir_plan_alignment import build_alignment_report  # type: ignore[no-redef]
    from runtime_layout_conversion_evidence import (  # type: ignore[no-redef]
        build_current_runtime_layout_conversion_evidence_report,
    )
    from runtime_mixed_tensor_store_evidence import (  # type: ignore[no-redef]
        build_mixed_tensor_store_evidence_report,
    )

from tuc.runtime.layout_conversion_digest_binding import (
    RuntimeLayoutConversionDigestBindingReport,
    build_runtime_layout_conversion_digest_binding_report,
    dump_runtime_layout_conversion_digest_binding_report,
)


def build_current_runtime_layout_conversion_digest_binding_report() -> (
    RuntimeLayoutConversionDigestBindingReport
):
    """Return the current mixed layout-conversion digest binding report."""

    return build_runtime_layout_conversion_digest_binding_report(
        build_current_runtime_layout_conversion_evidence_report(),
        build_alignment_report(),
        build_mixed_tensor_store_evidence_report(),
    )


def main() -> None:
    print(
        dump_runtime_layout_conversion_digest_binding_report(
            build_current_runtime_layout_conversion_digest_binding_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
