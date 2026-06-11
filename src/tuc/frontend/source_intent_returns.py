"""Execution-free Source Intent public return semantics.

This module turns already validated `SourceIntentModule.returns` into a
bounded, data-only return semantics report and a plain public-name alias map.
It does not parse source text, convert metadata, construct ComputeGraph,
lower IR, execute kernels, or build runtime evidence artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_RETURN_POLICY,
    SourceIntentModule,
    SourceIntentReturn,
)

SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT = (
    "source_intent_return_semantics.data_only.v0"
)
MAX_SOURCE_INTENT_RETURN_REPORT_BYTES = 16 * 1024
_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_inspection",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "file_system_access",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "source_parsing",
    "subprocess_execution",
)
_BLOCKED_COMPILER_OUTPUTS = (
    "metadata",
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
    "runtime_output_contract",
    "runtime_public_output_bundle",
)


@dataclass(frozen=True)
class SourceIntentReturnSemanticsReport:
    """Deterministic evidence for Source Intent return semantics."""

    module_name: str
    source_intent_contract: str
    return_semantics_contract: str
    return_policy: str
    returns: tuple[SourceIntentReturn, ...]
    terminal_tensor_names: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...]
    blocked_compiler_outputs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise ValueError("source-intent return report contract mismatch")
        if self.return_semantics_contract != SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT:
            raise ValueError("source-intent return semantics contract mismatch")
        if self.return_policy != SOURCE_INTENT_RETURN_POLICY:
            raise ValueError("source-intent return policy mismatch")
        if type(self.returns) is not tuple or not self.returns:
            raise ValueError("source-intent return report must contain returns")
        if type(self.terminal_tensor_names) is not tuple:
            raise TypeError("source-intent return terminal tensor names must be tuple")
        for source_return in self.returns:
            if not isinstance(source_return, SourceIntentReturn):
                raise TypeError("source-intent return report contains invalid return")
        expected_tensor_names = tuple(
            source_return.tensor_name for source_return in self.returns
        )
        if self.terminal_tensor_names != expected_tensor_names:
            raise ValueError("source-intent return terminal tensor names mismatch")
        if self.blocked_execution_surfaces != _BLOCKED_EXECUTION_SURFACES:
            raise ValueError("source-intent return blocked execution surfaces changed")
        if self.blocked_compiler_outputs != _BLOCKED_COMPILER_OUTPUTS:
            raise ValueError("source-intent return blocked compiler outputs changed")

    @property
    def return_count(self) -> int:
        """Return the number of explicit public returns."""

        return len(self.returns)

    @property
    def aliases(self) -> MappingProxyType[str, str]:
        """Return a read-only public-name to tensor-name alias mapping."""

        return MappingProxyType(
            {
                source_return.public_name: source_return.tensor_name
                for source_return in self.returns
            }
        )

    def dump(self) -> str:
        """Render deterministic return semantics evidence."""

        returns = (
            ",".join(
                f"{source_return.public_name}:{source_return.tensor_name}"
                for source_return in self.returns
            )
            if self.returns
            else "-"
        )
        terminal_tensor_names = ",".join(self.terminal_tensor_names)
        blocked_execution = ",".join(self.blocked_execution_surfaces)
        blocked_outputs = ",".join(self.blocked_compiler_outputs)
        return "\n".join(
            (
                f"source_intent.return_semantics @{self.module_name} {{",
                f'  source_intent_contract = "{self.source_intent_contract}"',
                f'  return_semantics_contract = "{self.return_semantics_contract}"',
                f'  return_policy = "{self.return_policy}"',
                f"  return_count = {self.return_count}",
                f'  terminal_tensor_names = "{terminal_tensor_names}"',
                f'  returns = "{returns}"',
                f'  blocked_execution_surfaces = "{blocked_execution}"',
                f'  blocked_compiler_outputs = "{blocked_outputs}"',
                "}",
            )
        )


def source_intent_return_aliases(module: SourceIntentModule) -> dict[str, str]:
    """Return a deterministic plain alias map for explicit source returns."""

    _require_source_intent_module(module)
    return {
        source_return.public_name: source_return.tensor_name
        for source_return in _sorted_returns(module.returns)
    }


def build_source_intent_return_semantics_report(
    module: SourceIntentModule,
) -> SourceIntentReturnSemanticsReport:
    """Build data-only evidence for explicit Source Intent return semantics."""

    _require_source_intent_module(module)
    if not module.returns:
        raise ValueError("source-intent return semantics require explicit returns")
    returns = _sorted_returns(module.returns)
    return SourceIntentReturnSemanticsReport(
        module_name=module.name,
        source_intent_contract=module.contract,
        return_semantics_contract=SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT,
        return_policy=SOURCE_INTENT_RETURN_POLICY,
        returns=returns,
        terminal_tensor_names=tuple(
            source_return.tensor_name for source_return in returns
        ),
        blocked_execution_surfaces=_BLOCKED_EXECUTION_SURFACES,
        blocked_compiler_outputs=_BLOCKED_COMPILER_OUTPUTS,
    )


def dump_source_intent_return_semantics_report(
    report: SourceIntentReturnSemanticsReport,
) -> str:
    """Render stable Source Intent return semantics evidence."""

    if not isinstance(report, SourceIntentReturnSemanticsReport):
        raise TypeError("source-intent return semantics report must be report object")
    text = report.dump()
    if len(text.encode("utf-8")) > MAX_SOURCE_INTENT_RETURN_REPORT_BYTES:
        raise ValueError("source-intent return semantics report exceeds byte limit")
    return text + "\n"


def _require_source_intent_module(module: SourceIntentModule) -> None:
    if not isinstance(module, SourceIntentModule):
        raise TypeError("source-intent return semantics require SourceIntentModule")
    if module.contract != SOURCE_INTENT_IR_CONTRACT:
        raise ValueError(
            "source-intent return semantics require contract "
            f"{SOURCE_INTENT_IR_CONTRACT!r}"
        )


def _sorted_returns(
    returns: tuple[SourceIntentReturn, ...],
) -> tuple[SourceIntentReturn, ...]:
    return tuple(sorted(returns, key=lambda item: item.public_name))


__all__ = [
    "MAX_SOURCE_INTENT_RETURN_REPORT_BYTES",
    "SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT",
    "SourceIntentReturnSemanticsReport",
    "build_source_intent_return_semantics_report",
    "dump_source_intent_return_semantics_report",
    "source_intent_return_aliases",
]
