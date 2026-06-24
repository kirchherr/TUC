"""Emit Runtime Layout Conversion Gate Promotion Policy Report v0."""

from __future__ import annotations

try:
    from examples.runtime_layout_conversion_gate_readiness import (
        build_current_runtime_layout_conversion_gate_readiness_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_layout_conversion_gate_readiness import (  # type: ignore[no-redef]
        build_current_runtime_layout_conversion_gate_readiness_report,
    )

from tuc.runtime.layout_conversion_gate_promotion_policy import (
    RuntimeLayoutConversionGatePromotionPolicyReport,
    build_runtime_layout_conversion_gate_promotion_policy_report,
    dump_runtime_layout_conversion_gate_promotion_policy_report,
)


def build_current_runtime_layout_conversion_gate_promotion_policy_report() -> (
    RuntimeLayoutConversionGatePromotionPolicyReport
):
    """Return the current layout-conversion gate-promotion policy report."""

    return build_runtime_layout_conversion_gate_promotion_policy_report(
        build_current_runtime_layout_conversion_gate_readiness_report()
    )


def main() -> None:
    print(
        dump_runtime_layout_conversion_gate_promotion_policy_report(
            build_current_runtime_layout_conversion_gate_promotion_policy_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
