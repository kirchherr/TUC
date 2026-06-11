"""Data-only runtime output contract for public output aliases."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.model import MAX_TENSOR_DIMENSION, MAX_TENSOR_RANK, ComputeGraph
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RuntimeExecutionResult,
)
from tuc.runtime.output_manifest import (
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY,
    build_runtime_output_manifest_report,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
)

RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION = "tuc.runtime_output_contract_report.v0"
RUNTIME_OUTPUT_CONTRACT = "runtime_output_contract.data_only.v0"
RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS = "review_evidence"
RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY = "explicit_output_aliases"
MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES = 4096
MAX_RUNTIME_OUTPUT_CONTRACT_ISSUES = 256
MAX_RUNTIME_OUTPUT_CONTRACT_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_OUTPUT_CONTRACT_FIELD_BYTES = 512

_OUTPUT_CONTRACT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_VALUE_ROLES = frozenset({"input", "computed"})
_PRODUCER_KINDS = frozenset({"external_input", "operation"})
_FORBIDDEN_OUTPUT_CONTRACT_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
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
    }
)


@dataclass(frozen=True)
class RuntimeOutputAlias:
    """One explicit public output name bound to one terminal graph tensor."""

    public_name: str
    tensor_name: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_output_contract_text(self.public_name, "output alias public_name")
        _validate_output_contract_text(self.tensor_name, "output alias tensor_name")
        if self.required is not True:
            raise ValueError("runtime output aliases are required in v0")


@dataclass(frozen=True)
class RuntimePublicOutput:
    """Public output metadata resolved from a terminal runtime output."""

    public_name: str
    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    value_role: str
    producer_kind: str
    producer_id: str
    raw_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_output_contract_text(self.public_name, "public output public_name")
        _validate_output_contract_text(self.tensor_name, "public output tensor_name")
        _validate_shape(self.shape, "public output shape")
        _validate_output_contract_text(self.dtype, "public output dtype")
        _validate_value_role(self.value_role)
        _validate_producer(self.value_role, self.producer_kind, self.producer_id)
        if self.raw_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime output contract must omit raw values")


@dataclass(frozen=True)
class RuntimeOutputContractIssue:
    """One derived runtime output contract issue."""

    public_name: str
    tensor_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_output_contract_text(self.public_name, "output contract issue public_name")
        _validate_output_contract_text(self.tensor_name, "output contract issue tensor_name")
        _validate_output_contract_text(self.issue_code, "output contract issue_code")


@dataclass(frozen=True)
class RuntimeOutputContractReport:
    """Deterministic, data-only public output contract report."""

    graph_name: str
    aliases: tuple[RuntimeOutputAlias, ...]
    terminal_tensor_names: tuple[str, ...]
    available_tensor_names: tuple[str, ...]
    public_outputs: tuple[RuntimePublicOutput, ...]
    output_manifest_passed: bool
    issues: tuple[RuntimeOutputContractIssue, ...]
    output_contract: str = RUNTIME_OUTPUT_CONTRACT
    output_manifest_contract: str = RUNTIME_OUTPUT_MANIFEST_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    artifact_status: str = RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS
    alias_policy: str = RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    terminal_output_policy: str = RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_output_contract_text(self.graph_name, "output contract graph_name")
        if self.output_contract != RUNTIME_OUTPUT_CONTRACT:
            raise ValueError("runtime output contract mismatch")
        if self.output_manifest_contract != RUNTIME_OUTPUT_MANIFEST_CONTRACT:
            raise ValueError("runtime output contract manifest contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime output contract executor contract mismatch")
        if self.artifact_status != RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS:
            raise ValueError("runtime output contract artifact status mismatch")
        if self.alias_policy != RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY:
            raise ValueError("runtime output contract alias policy mismatch")
        if self.terminal_output_policy != RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY:
            raise ValueError("runtime output contract terminal output policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime output contract must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime output contract blocked execution surfaces changed")
        _validate_aliases(self.aliases)
        _validate_name_inventory(self.terminal_tensor_names, "terminal tensor names")
        _validate_name_inventory(
            self.available_tensor_names,
            "available tensor names",
            allow_empty=True,
        )
        _validate_public_outputs(self.public_outputs)
        if not isinstance(self.output_manifest_passed, bool):
            raise TypeError("runtime output contract manifest status must be bool")
        if type(self.issues) is not tuple:
            raise TypeError("runtime output contract issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_OUTPUT_CONTRACT_ISSUES:
            raise ValueError("runtime output contract issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeOutputContractIssue):
                raise TypeError(
                    "runtime output contract issues must be output contract issues"
                )
        expected_issues = _derive_issues(
            self.aliases,
            self.terminal_tensor_names,
            self.available_tensor_names,
            self.public_outputs,
            self.output_manifest_passed,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime output contract issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the runtime output contract passed."""

        return not self.issues

    @property
    def contract_metadata_digest(self) -> str:
        """Return a digest over public output metadata only."""

        payload = {
            "aliases": [
                {
                    "public_name": alias.public_name,
                    "required": alias.required,
                    "tensor_name": alias.tensor_name,
                }
                for alias in self.aliases
            ],
            "output_manifest_passed": self.output_manifest_passed,
            "public_outputs": [
                {
                    "dtype": output.dtype,
                    "producer_id": output.producer_id,
                    "producer_kind": output.producer_kind,
                    "public_name": output.public_name,
                    "raw_value_status": output.raw_value_status,
                    "shape": list(output.shape),
                    "tensor_name": output.tensor_name,
                    "value_role": output.value_role,
                }
                for output in self.public_outputs
            ],
            "terminal_tensor_names": list(self.terminal_tensor_names),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeOutputContractError(AssertionError):
    """Raised when runtime output contract evidence does not pass."""


def build_runtime_output_contract_report(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
    aliases: Mapping[str, str],
) -> RuntimeOutputContractReport:
    """Build data-only public output contract evidence from an executed graph."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime output contract graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime output contract execution must be RuntimeExecutionResult")
    if type(aliases) is not dict:
        raise TypeError("runtime output contract aliases must be a plain dict")

    output_manifest = build_runtime_output_manifest_report(graph, execution)
    alias_records = tuple(
        sorted(
            (
                RuntimeOutputAlias(public_name=public_name, tensor_name=tensor_name)
                for public_name, tensor_name in aliases.items()
            ),
            key=lambda alias: alias.public_name,
        )
    )
    terminal_tensor_names = tuple(
        output.tensor_name for output in output_manifest.expected_outputs
    )
    available_tensor_names = tuple(output.tensor_name for output in output_manifest.outputs)
    outputs_by_name = {output.tensor_name: output for output in output_manifest.outputs}
    public_outputs = tuple(
        RuntimePublicOutput(
            public_name=alias.public_name,
            tensor_name=alias.tensor_name,
            shape=output.shape,
            dtype=output.dtype,
            value_role=output.value_role,
            producer_kind=output.producer_kind,
            producer_id=output.producer_id,
        )
        for alias in alias_records
        for output in (outputs_by_name.get(alias.tensor_name),)
        if output is not None
    )
    return RuntimeOutputContractReport(
        graph_name=graph.name,
        aliases=alias_records,
        terminal_tensor_names=terminal_tensor_names,
        available_tensor_names=available_tensor_names,
        public_outputs=public_outputs,
        output_manifest_passed=output_manifest.passed,
        issues=_derive_issues(
            alias_records,
            terminal_tensor_names,
            available_tensor_names,
            public_outputs,
            output_manifest.passed,
        ),
    )


def assert_runtime_output_contract(
    report: RuntimeOutputContractReport,
) -> RuntimeOutputContractReport:
    """Return the report or raise when runtime output contract evidence fails."""

    if not isinstance(report, RuntimeOutputContractReport):
        raise TypeError("runtime output contract report must be report object")
    if report.issues:
        lines = [f"runtime output contract failed for {report.graph_name!r}:"]
        lines.extend(
            f"- {issue.public_name}:{issue.tensor_name}:{issue.issue_code}"
            for issue in report.issues
        )
        raise RuntimeOutputContractError("\n".join(lines))
    return report


def runtime_output_contract_report_to_dict(
    report: RuntimeOutputContractReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible output contract report."""

    if not isinstance(report, RuntimeOutputContractReport):
        raise TypeError("runtime output contract report must be report object")
    return {
        "alias_count": len(report.aliases),
        "alias_policy": report.alias_policy,
        "aliases": [
            {
                "public_name": alias.public_name,
                "required": alias.required,
                "tensor_name": alias.tensor_name,
            }
            for alias in report.aliases
        ],
        "artifact_status": report.artifact_status,
        "available_tensor_names": list(report.available_tensor_names),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "contract_metadata_digest": report.contract_metadata_digest,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "public_name": issue.public_name,
                "tensor_name": issue.tensor_name,
            }
            for issue in report.issues
        ],
        "output_contract": report.output_contract,
        "output_manifest_contract": report.output_manifest_contract,
        "output_manifest_passed": report.output_manifest_passed,
        "passed": report.passed,
        "public_output_count": len(report.public_outputs),
        "public_outputs": [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "public_name": output.public_name,
                "raw_value_status": output.raw_value_status,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_role": output.value_role,
            }
            for output in report.public_outputs
        ],
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION,
        "terminal_output_policy": report.terminal_output_policy,
        "terminal_tensor_names": list(report.terminal_tensor_names),
    }


def dump_runtime_output_contract_report(report: RuntimeOutputContractReport) -> str:
    """Render stable data-only runtime output contract evidence."""

    text = json.dumps(
        runtime_output_contract_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_OUTPUT_CONTRACT_REPORT_BYTES:
        raise ValueError("runtime output contract report exceeds byte limit")
    return text + "\n"


def _derive_issues(
    aliases: tuple[RuntimeOutputAlias, ...],
    terminal_tensor_names: tuple[str, ...],
    available_tensor_names: tuple[str, ...],
    public_outputs: tuple[RuntimePublicOutput, ...],
    output_manifest_passed: bool,
) -> tuple[RuntimeOutputContractIssue, ...]:
    terminal_names = set(terminal_tensor_names)
    available_names = set(available_tensor_names)
    alias_targets = tuple(alias.tensor_name for alias in aliases)
    target_counts = Counter(alias_targets)
    public_output_pairs = {
        (output.public_name, output.tensor_name) for output in public_outputs
    }
    expected_public_output_pairs = {
        (alias.public_name, alias.tensor_name)
        for alias in aliases
        if alias.tensor_name in terminal_names and alias.tensor_name in available_names
    }
    issues: list[RuntimeOutputContractIssue] = []

    if not output_manifest_passed:
        issues.append(
            RuntimeOutputContractIssue(
                public_name="output_manifest",
                tensor_name="output_manifest",
                issue_code="output_manifest_failed",
            )
        )

    for alias in aliases:
        if alias.tensor_name not in terminal_names:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name=alias.public_name,
                    tensor_name=alias.tensor_name,
                    issue_code="alias_target_not_terminal",
                )
            )
        if target_counts[alias.tensor_name] > 1:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name=alias.public_name,
                    tensor_name=alias.tensor_name,
                    issue_code="duplicate_tensor_binding",
                )
            )
        if alias.tensor_name in terminal_names and alias.tensor_name not in available_names:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name=alias.public_name,
                    tensor_name=alias.tensor_name,
                    issue_code="bound_output_missing",
                )
            )

    for tensor_name in terminal_tensor_names:
        if tensor_name not in alias_targets:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name="unbound",
                    tensor_name=tensor_name,
                    issue_code="terminal_output_unbound",
                )
            )

    for public_name, tensor_name in sorted(expected_public_output_pairs):
        if (public_name, tensor_name) not in public_output_pairs:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name=public_name,
                    tensor_name=tensor_name,
                    issue_code="public_output_missing",
                )
            )

    for output in public_outputs:
        if (output.public_name, output.tensor_name) not in expected_public_output_pairs:
            issues.append(
                RuntimeOutputContractIssue(
                    public_name=output.public_name,
                    tensor_name=output.tensor_name,
                    issue_code="unexpected_public_output",
                )
            )

    return tuple(issues)


def _validate_aliases(aliases: tuple[RuntimeOutputAlias, ...]) -> None:
    if type(aliases) is not tuple:
        raise TypeError("runtime output contract aliases must be a tuple")
    if len(aliases) > MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES:
        raise ValueError("runtime output contract alias count exceeds limit")
    public_names: list[str] = []
    for alias in aliases:
        if not isinstance(alias, RuntimeOutputAlias):
            raise TypeError("runtime output contract aliases must be output aliases")
        public_names.append(alias.public_name)
    if len(public_names) != len(set(public_names)):
        raise ValueError("runtime output contract public names must be unique")


def _validate_public_outputs(outputs: tuple[RuntimePublicOutput, ...]) -> None:
    if type(outputs) is not tuple:
        raise TypeError("runtime output contract public outputs must be a tuple")
    if len(outputs) > MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES:
        raise ValueError("runtime output contract public output count exceeds limit")
    public_names: list[str] = []
    for output in outputs:
        if not isinstance(output, RuntimePublicOutput):
            raise TypeError(
                "runtime output contract public outputs must be public outputs"
            )
        public_names.append(output.public_name)
    if len(public_names) != len(set(public_names)):
        raise ValueError("runtime output contract public output names must be unique")


def _validate_name_inventory(
    names: tuple[str, ...],
    label: str,
    *,
    allow_empty: bool = False,
) -> None:
    if type(names) is not tuple:
        raise TypeError(f"runtime output contract {label} must be a tuple")
    if not names and not allow_empty:
        raise ValueError(f"runtime output contract {label} must not be empty")
    if len(names) > MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES:
        raise ValueError(f"runtime output contract {label} count exceeds limit")
    for name in names:
        _validate_output_contract_text(name, label)
    if len(names) != len(set(names)):
        raise ValueError(f"runtime output contract {label} must be unique")


def _validate_value_role(value: str) -> None:
    if value not in _VALUE_ROLES:
        raise ValueError("runtime output contract value role unsupported")


def _validate_producer(value_role: str, producer_kind: str, producer_id: str) -> None:
    if producer_kind not in _PRODUCER_KINDS:
        raise ValueError("runtime output contract producer kind unsupported")
    _validate_output_contract_text(producer_id, "producer_id")
    if value_role == "input" and producer_kind != "external_input":
        raise ValueError("runtime output contract input producer must be external_input")
    if value_role == "computed" and producer_kind != "operation":
        raise ValueError("runtime output contract computed producer must be operation")


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
    if len(value) > MAX_TENSOR_RANK:
        raise ValueError(f"{label} exceeds tensor rank limit")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_TENSOR_DIMENSION
        ):
            raise ValueError(f"{label} must contain bounded positive integers")


def _validate_output_contract_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _OUTPUT_CONTRACT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime output contract identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_OUTPUT_CONTRACT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime output contract field limit")
    if value in _FORBIDDEN_OUTPUT_CONTRACT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES",
    "MAX_RUNTIME_OUTPUT_CONTRACT_FIELD_BYTES",
    "MAX_RUNTIME_OUTPUT_CONTRACT_ISSUES",
    "MAX_RUNTIME_OUTPUT_CONTRACT_REPORT_BYTES",
    "RUNTIME_OUTPUT_CONTRACT",
    "RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY",
    "RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS",
    "RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION",
    "RuntimeOutputAlias",
    "RuntimeOutputContractError",
    "RuntimeOutputContractIssue",
    "RuntimeOutputContractReport",
    "RuntimePublicOutput",
    "assert_runtime_output_contract",
    "build_runtime_output_contract_report",
    "dump_runtime_output_contract_report",
    "runtime_output_contract_report_to_dict",
]
