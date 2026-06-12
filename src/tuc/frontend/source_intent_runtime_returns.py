"""Evidence linking Source Intent returns to runtime public outputs.

This adapter is intentionally narrow: it consumes an already validated
`SourceIntentModule`, an already compiled `ComputeGraph`, and an already trusted
`RuntimeExecutionResult`. It does not parse source text, lower IR, plan
runtime placement, execute kernels, discover plugins, or serialize tensor
values.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_RETURN_POLICY,
    SourceIntentModule,
)
from tuc.frontend.source_intent_returns import (
    SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT,
    build_source_intent_return_semantics_report,
    source_intent_return_aliases,
)
from tuc.ir.model import ComputeGraph
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RuntimeExecutionResult,
)
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY,
    RuntimeOutputContractReport,
    build_runtime_output_contract_report,
)
from tuc.runtime.public_output_bundle import (
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    build_runtime_public_output_bundle,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION = (
    "tuc.source_intent_runtime_returns_report.v0"
)
SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT = "source_intent_runtime_returns.evidence.v0"
SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS = "review_evidence"
MAX_SOURCE_INTENT_RUNTIME_RETURNS = 4096
MAX_SOURCE_INTENT_RUNTIME_RETURNS_FIELD_BYTES = 512
MAX_SOURCE_INTENT_RUNTIME_RETURNS_REPORT_BYTES = 128 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "command_line",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "output_value",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_output_value",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
        "value",
        "values",
    }
)


@dataclass(frozen=True)
class SourceIntentRuntimeReturnBinding:
    """One Source Intent public return bound to one runtime terminal tensor."""

    public_name: str
    tensor_name: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.public_name, "source intent runtime public_name")
        _validate_report_text(self.tensor_name, "source intent runtime tensor_name")
        if self.required is not True:
            raise ValueError("source intent runtime returns require required bindings")


@dataclass(frozen=True)
class SourceIntentRuntimeReturnsReport:
    """Deterministic metadata-only evidence for frontend return resolution."""

    module_name: str
    graph_name: str
    bindings: tuple[SourceIntentRuntimeReturnBinding, ...]
    terminal_tensor_names: tuple[str, ...]
    public_output_names: tuple[str, ...]
    output_contract_passed: bool
    public_output_bundle_passed: bool
    contract_metadata_digest: str
    bundle_metadata_digest: str
    source_intent_blocked_execution_surfaces: tuple[str, ...]
    source_intent_blocked_compiler_outputs: tuple[str, ...]
    runtime_blocked_execution_surfaces: tuple[str, ...]
    schema_version: str = SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION
    artifact_status: str = SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS
    runtime_returns_contract: str = SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT
    source_intent_contract: str = SOURCE_INTENT_IR_CONTRACT
    return_semantics_contract: str = SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT
    return_policy: str = SOURCE_INTENT_RETURN_POLICY
    output_contract: str = RUNTIME_OUTPUT_CONTRACT
    public_output_bundle_contract: str = RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    alias_policy: str = RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_report_text(self.module_name, "source intent runtime module_name")
        _validate_report_text(self.graph_name, "source intent runtime graph_name")
        if self.module_name != self.graph_name:
            raise ValueError("source intent runtime module and graph names must match")
        if self.schema_version != SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION:
            raise ValueError("source intent runtime returns schema mismatch")
        if self.artifact_status != SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS:
            raise ValueError("source intent runtime returns artifact status mismatch")
        if self.runtime_returns_contract != SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT:
            raise ValueError("source intent runtime returns contract mismatch")
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise ValueError("source intent runtime source contract mismatch")
        if self.return_semantics_contract != SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT:
            raise ValueError("source intent runtime return semantics mismatch")
        if self.return_policy != SOURCE_INTENT_RETURN_POLICY:
            raise ValueError("source intent runtime return policy mismatch")
        if self.output_contract != RUNTIME_OUTPUT_CONTRACT:
            raise ValueError("source intent runtime output contract mismatch")
        if self.public_output_bundle_contract != RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT:
            raise ValueError("source intent runtime public output bundle mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("source intent runtime executor contract mismatch")
        if self.alias_policy != RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY:
            raise ValueError("source intent runtime alias policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("source intent runtime returns must omit raw values")
        _validate_bindings(self.bindings)
        _validate_text_tuple(self.terminal_tensor_names, "terminal tensor names")
        _validate_text_tuple(self.public_output_names, "public output names")
        _validate_bool_true(
            self.output_contract_passed,
            "source intent runtime output contract status",
        )
        _validate_bool_true(
            self.public_output_bundle_passed,
            "source intent runtime public output bundle status",
        )
        _validate_digest(self.contract_metadata_digest, "contract metadata digest")
        _validate_digest(self.bundle_metadata_digest, "bundle metadata digest")
        _validate_text_tuple(
            self.source_intent_blocked_execution_surfaces,
            "source intent blocked execution surfaces",
        )
        _validate_text_tuple(
            self.source_intent_blocked_compiler_outputs,
            "source intent blocked compiler outputs",
        )
        if self.runtime_blocked_execution_surfaces != (
            RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source intent runtime blocked surfaces changed")
        if set(self.terminal_tensor_names) != {
            binding.tensor_name for binding in self.bindings
        }:
            raise ValueError("source intent runtime terminal tensors mismatch")
        if self.public_output_names != tuple(binding.public_name for binding in self.bindings):
            raise ValueError("source intent runtime public outputs mismatch")

    @property
    def passed(self) -> bool:
        """Return whether Source Intent returns resolved through runtime outputs."""

        return self.output_contract_passed and self.public_output_bundle_passed

    @property
    def return_count(self) -> int:
        """Return the number of explicit Source Intent returns."""

        return len(self.bindings)

    @property
    def link_metadata_digest(self) -> str:
        """Return a digest over link metadata only, never tensor values."""

        payload = {
            "bindings": [
                {
                    "public_name": binding.public_name,
                    "required": binding.required,
                    "tensor_name": binding.tensor_name,
                }
                for binding in self.bindings
            ],
            "bundle_metadata_digest": self.bundle_metadata_digest,
            "contract_metadata_digest": self.contract_metadata_digest,
            "graph_name": self.graph_name,
            "module_name": self.module_name,
            "public_output_names": list(self.public_output_names),
            "terminal_tensor_names": list(self.terminal_tensor_names),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class SourceIntentRuntimeReturnsError(AssertionError):
    """Raised when Source Intent returns cannot resolve through runtime outputs."""


def build_source_intent_runtime_returns_report(
    module: SourceIntentModule,
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
) -> SourceIntentRuntimeReturnsReport:
    """Build evidence that Source Intent public returns resolve at runtime."""

    _require_source_intent_module(module)
    if not isinstance(graph, ComputeGraph):
        raise TypeError("source intent runtime returns graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError(
            "source intent runtime returns execution must be RuntimeExecutionResult"
        )
    if module.name != graph.name:
        raise SourceIntentRuntimeReturnsError(
            "source intent runtime returns module and graph names must match"
        )
    if graph.name != execution.trace.graph_name:
        raise SourceIntentRuntimeReturnsError(
            "source intent runtime returns graph and execution names must match"
        )

    return_semantics = build_source_intent_return_semantics_report(module)
    _require_required_returns(module)
    aliases = source_intent_return_aliases(module)
    output_contract = build_runtime_output_contract_report(graph, execution, aliases)
    _assert_output_contract_passed(output_contract)
    bundle = build_runtime_public_output_bundle(execution, output_contract)

    return SourceIntentRuntimeReturnsReport(
        module_name=module.name,
        graph_name=graph.name,
        bindings=tuple(
            SourceIntentRuntimeReturnBinding(
                public_name=source_return.public_name,
                tensor_name=source_return.tensor_name,
                required=source_return.required,
            )
            for source_return in return_semantics.returns
        ),
        terminal_tensor_names=output_contract.terminal_tensor_names,
        public_output_names=bundle.public_output_names,
        output_contract_passed=output_contract.passed,
        public_output_bundle_passed=bundle.passed,
        contract_metadata_digest=output_contract.contract_metadata_digest,
        bundle_metadata_digest=bundle.bundle_metadata_digest,
        source_intent_blocked_execution_surfaces=(
            return_semantics.blocked_execution_surfaces
        ),
        source_intent_blocked_compiler_outputs=return_semantics.blocked_compiler_outputs,
        runtime_blocked_execution_surfaces=output_contract.blocked_execution_surfaces,
    )


def assert_source_intent_runtime_returns(
    report: SourceIntentRuntimeReturnsReport,
) -> SourceIntentRuntimeReturnsReport:
    """Return the report or raise when Source Intent runtime returns failed."""

    if not isinstance(report, SourceIntentRuntimeReturnsReport):
        raise TypeError("source intent runtime returns report must be report object")
    if not report.passed:
        raise SourceIntentRuntimeReturnsError(
            f"source intent runtime returns failed for {report.module_name!r}"
        )
    return report


def source_intent_runtime_returns_report_to_dict(
    report: SourceIntentRuntimeReturnsReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible Source Intent runtime evidence."""

    if not isinstance(report, SourceIntentRuntimeReturnsReport):
        raise TypeError("source intent runtime returns report must be report object")
    return {
        "alias_policy": report.alias_policy,
        "artifact_status": report.artifact_status,
        "bindings": [
            {
                "public_name": binding.public_name,
                "required": binding.required,
                "tensor_name": binding.tensor_name,
            }
            for binding in report.bindings
        ],
        "bundle_metadata_digest": report.bundle_metadata_digest,
        "contract_metadata_digest": report.contract_metadata_digest,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "link_metadata_digest": report.link_metadata_digest,
        "module_name": report.module_name,
        "output_contract": report.output_contract,
        "output_contract_passed": report.output_contract_passed,
        "passed": report.passed,
        "public_output_bundle_contract": report.public_output_bundle_contract,
        "public_output_bundle_passed": report.public_output_bundle_passed,
        "public_output_count": len(report.public_output_names),
        "public_output_names": list(report.public_output_names),
        "raw_value_policy": report.raw_value_policy,
        "return_count": report.return_count,
        "return_policy": report.return_policy,
        "return_semantics_contract": report.return_semantics_contract,
        "runtime_blocked_execution_surfaces": list(
            report.runtime_blocked_execution_surfaces
        ),
        "runtime_returns_contract": report.runtime_returns_contract,
        "schema_version": report.schema_version,
        "source_intent_blocked_compiler_outputs": list(
            report.source_intent_blocked_compiler_outputs
        ),
        "source_intent_blocked_execution_surfaces": list(
            report.source_intent_blocked_execution_surfaces
        ),
        "source_intent_contract": report.source_intent_contract,
        "terminal_tensor_names": list(report.terminal_tensor_names),
    }


def dump_source_intent_runtime_returns_report(
    report: SourceIntentRuntimeReturnsReport,
) -> str:
    """Render stable Source Intent runtime returns evidence."""

    text = json.dumps(
        source_intent_runtime_returns_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_INTENT_RUNTIME_RETURNS_REPORT_BYTES:
        raise ValueError("source intent runtime returns report exceeds byte limit")
    return text + "\n"


def _require_source_intent_module(module: SourceIntentModule) -> None:
    if not isinstance(module, SourceIntentModule):
        raise TypeError("source intent runtime returns require SourceIntentModule")
    if module.contract != SOURCE_INTENT_IR_CONTRACT:
        raise ValueError(
            "source intent runtime returns require contract "
            f"{SOURCE_INTENT_IR_CONTRACT!r}"
        )


def _require_required_returns(module: SourceIntentModule) -> None:
    for source_return in module.returns:
        if source_return.required is not True:
            raise SourceIntentRuntimeReturnsError(
                "source intent runtime returns require required returns in v0"
            )


def _assert_output_contract_passed(report: RuntimeOutputContractReport) -> None:
    if report.passed:
        return
    issues = ",".join(
        f"{issue.public_name}:{issue.tensor_name}:{issue.issue_code}"
        for issue in report.issues
    )
    raise SourceIntentRuntimeReturnsError(
        f"source intent runtime returns output contract failed: {issues}"
    )


def _validate_bindings(
    bindings: tuple[SourceIntentRuntimeReturnBinding, ...],
) -> None:
    if type(bindings) is not tuple:
        raise TypeError("source intent runtime return bindings must be tuple")
    if not bindings:
        raise ValueError("source intent runtime return bindings must not be empty")
    if len(bindings) > MAX_SOURCE_INTENT_RUNTIME_RETURNS:
        raise ValueError("source intent runtime return binding count exceeds limit")
    public_names: list[str] = []
    tensor_names: list[str] = []
    for binding in bindings:
        if not isinstance(binding, SourceIntentRuntimeReturnBinding):
            raise TypeError("source intent runtime return bindings must be bindings")
        public_names.append(binding.public_name)
        tensor_names.append(binding.tensor_name)
    if len(public_names) != len(set(public_names)):
        raise ValueError("source intent runtime public names must be unique")
    if len(tensor_names) != len(set(tensor_names)):
        raise ValueError("source intent runtime tensor names must be unique")


def _validate_text_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be tuple")
    if not values:
        raise ValueError(f"{label} must not be empty")
    if len(values) > MAX_SOURCE_INTENT_RUNTIME_RETURNS:
        raise ValueError(f"{label} count exceeds limit")
    for value in values:
        _validate_report_text(value, label)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _validate_bool_true(value: bool, label: str) -> None:
    if value is not True:
        raise ValueError(f"{label} must be true")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 digest")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe report identifier")
    if len(value.encode("utf-8")) > MAX_SOURCE_INTENT_RUNTIME_RETURNS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds source intent runtime returns field limit")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_SOURCE_INTENT_RUNTIME_RETURNS",
    "MAX_SOURCE_INTENT_RUNTIME_RETURNS_FIELD_BYTES",
    "MAX_SOURCE_INTENT_RUNTIME_RETURNS_REPORT_BYTES",
    "SOURCE_INTENT_RUNTIME_RETURNS_ARTIFACT_STATUS",
    "SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT",
    "SOURCE_INTENT_RUNTIME_RETURNS_REPORT_SCHEMA_VERSION",
    "SourceIntentRuntimeReturnBinding",
    "SourceIntentRuntimeReturnsError",
    "SourceIntentRuntimeReturnsReport",
    "assert_source_intent_runtime_returns",
    "build_source_intent_runtime_returns_report",
    "dump_source_intent_runtime_returns_report",
    "source_intent_runtime_returns_report_to_dict",
]
