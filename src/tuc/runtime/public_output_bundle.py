"""Read-only public output bundle derived from Runtime Output Contract evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from tuc.ir.model import MAX_TENSOR_DIMENSION, MAX_TENSOR_RANK
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimeExecutionResult,
)
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT,
    RuntimeOutputContractReport,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_public_output_bundle_report.v0"
)
RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT = (
    "runtime_public_output_bundle.readonly_values.v0"
)
RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT = (
    "runtime_public_output_value.readonly_numpy.v0"
)
RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS = "review_evidence"
MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_OUTPUTS = 4096
MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_FIELD_BYTES = 512

_PUBLIC_OUTPUT_BUNDLE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_VALUE_ROLES = frozenset({"input", "computed"})
_PRODUCER_KINDS = frozenset({"external_input", "operation"})
_FORBIDDEN_PUBLIC_OUTPUT_BUNDLE_TEXT = frozenset(
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
    }
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class RuntimePublicOutputValue:
    """One read-only public output value resolved from a runtime tensor record."""

    public_name: str
    tensor_name: str
    value: FloatArray
    shape: tuple[int, ...]
    dtype: str
    value_role: str
    producer_kind: str
    producer_id: str
    value_contract: str = RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT
    record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    raw_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_bundle_text(self.public_name, "public output value public_name")
        _validate_bundle_text(self.tensor_name, "public output value tensor_name")
        _validate_shape(self.shape, "public output value shape")
        _validate_bundle_text(self.dtype, "public output value dtype")
        _validate_value_role(self.value_role)
        _validate_producer(self.value_role, self.producer_kind, self.producer_id)
        if self.value_contract != RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT:
            raise ValueError("runtime public output value contract mismatch")
        if self.record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime public output record contract mismatch")
        if self.raw_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime public output bundle must omit raw values")
        if not isinstance(self.value, np.ndarray):
            raise TypeError("runtime public output value must be NumPy array")
        if tuple(int(dimension) for dimension in self.value.shape) != self.shape:
            raise ValueError("runtime public output value shape mismatch")
        if str(self.value.dtype) != self.dtype:
            raise ValueError("runtime public output value dtype mismatch")
        stored_value = np.array(self.value, copy=True)
        stored_value.setflags(write=False)
        object.__setattr__(self, "value", stored_value)

    @property
    def readonly(self) -> bool:
        """Return whether the public output value is read-only."""

        return not self.value.flags.writeable


@dataclass(frozen=True)
class RuntimePublicOutputBundle:
    """Read-only public runtime outputs keyed by explicit output aliases."""

    graph_name: str
    outputs: tuple[RuntimePublicOutputValue, ...]
    bundle_contract: str = RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    output_contract: str = RUNTIME_OUTPUT_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    artifact_status: str = RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_bundle_text(self.graph_name, "public output bundle graph_name")
        if self.bundle_contract != RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT:
            raise ValueError("runtime public output bundle contract mismatch")
        if self.output_contract != RUNTIME_OUTPUT_CONTRACT:
            raise ValueError("runtime public output bundle output contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime public output bundle executor contract mismatch")
        if self.artifact_status != RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS:
            raise ValueError("runtime public output bundle artifact status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime public output bundle must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime public output blocked execution surfaces changed")
        _validate_public_output_values(self.outputs)

    @property
    def values(self) -> MappingProxyType[str, FloatArray]:
        """Return a read-only public-name to output-value mapping."""

        return MappingProxyType(
            {output.public_name: output.value for output in self.outputs}
        )

    @property
    def public_output_names(self) -> tuple[str, ...]:
        """Return public output names in bundle order."""

        return tuple(output.public_name for output in self.outputs)

    @property
    def tensor_names(self) -> tuple[str, ...]:
        """Return backing terminal tensor names in bundle order."""

        return tuple(output.tensor_name for output in self.outputs)

    @property
    def passed(self) -> bool:
        """Return whether bundle construction passed."""

        return True

    @property
    def bundle_metadata_digest(self) -> str:
        """Return a digest over public output metadata only."""

        payload = [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "public_name": output.public_name,
                "raw_value_status": output.raw_value_status,
                "readonly": output.readonly,
                "record_contract": output.record_contract,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_contract": output.value_contract,
                "value_role": output.value_role,
            }
            for output in self.outputs
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"

    def value_for(self, public_name: str) -> FloatArray:
        """Return one read-only public output value by public name."""

        _validate_bundle_text(public_name, "public output name")
        for output in self.outputs:
            if output.public_name == public_name:
                return output.value
        raise KeyError(public_name)


class RuntimePublicOutputBundleError(AssertionError):
    """Raised when runtime public output bundle construction is invalid."""


def build_runtime_public_output_bundle(
    execution: RuntimeExecutionResult,
    output_contract: RuntimeOutputContractReport,
) -> RuntimePublicOutputBundle:
    """Resolve public output aliases to read-only runtime values."""

    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime public output bundle execution must be result object")
    if not isinstance(output_contract, RuntimeOutputContractReport):
        raise TypeError("runtime public output bundle contract must be report object")
    if execution.trace.graph_name != output_contract.graph_name:
        raise RuntimePublicOutputBundleError(
            "runtime public output bundle graph name mismatch"
        )
    if not output_contract.passed:
        issues = ",".join(
            f"{issue.public_name}:{issue.tensor_name}:{issue.issue_code}"
            for issue in output_contract.issues
        )
        raise RuntimePublicOutputBundleError(
            f"runtime public output contract failed: {issues}"
        )

    outputs: list[RuntimePublicOutputValue] = []
    for public_output in output_contract.public_outputs:
        try:
            record = execution.record_for(public_output.tensor_name)
        except KeyError as exc:
            raise RuntimePublicOutputBundleError(
                "runtime public output bundle tensor missing: "
                f"{public_output.tensor_name}"
            ) from exc
        outputs.append(
            RuntimePublicOutputValue(
                public_name=public_output.public_name,
                tensor_name=public_output.tensor_name,
                value=record.value,
                shape=public_output.shape,
                dtype=public_output.dtype,
                value_role=record.value_role,
                producer_kind=record.producer_kind,
                producer_id=record.producer_id,
                record_contract=record.record_contract,
            )
        )
    return RuntimePublicOutputBundle(
        graph_name=output_contract.graph_name,
        outputs=tuple(outputs),
    )


def assert_runtime_public_output_bundle(
    bundle: RuntimePublicOutputBundle,
) -> RuntimePublicOutputBundle:
    """Return the bundle or raise when it is not a valid public output bundle."""

    if not isinstance(bundle, RuntimePublicOutputBundle):
        raise TypeError("runtime public output bundle must be bundle object")
    return bundle


def runtime_public_output_bundle_report_to_dict(
    bundle: RuntimePublicOutputBundle,
) -> dict[str, object]:
    """Return deterministic JSON-compatible public output bundle metadata."""

    if not isinstance(bundle, RuntimePublicOutputBundle):
        raise TypeError("runtime public output bundle must be bundle object")
    return {
        "artifact_status": bundle.artifact_status,
        "blocked_execution_surfaces": list(bundle.blocked_execution_surfaces),
        "bundle_contract": bundle.bundle_contract,
        "bundle_metadata_digest": bundle.bundle_metadata_digest,
        "executor_contract": bundle.executor_contract,
        "graph_name": bundle.graph_name,
        "output_contract": bundle.output_contract,
        "passed": bundle.passed,
        "public_output_count": len(bundle.outputs),
        "public_output_names": list(bundle.public_output_names),
        "public_outputs": [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "public_name": output.public_name,
                "raw_value_status": output.raw_value_status,
                "readonly": output.readonly,
                "record_contract": output.record_contract,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_contract": output.value_contract,
                "value_role": output.value_role,
            }
            for output in bundle.outputs
        ],
        "raw_value_policy": bundle.raw_value_policy,
        "schema_version": RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION,
        "tensor_names": list(bundle.tensor_names),
    }


def dump_runtime_public_output_bundle_report(
    bundle: RuntimePublicOutputBundle,
) -> str:
    """Render stable metadata-only public output bundle evidence."""

    text = json.dumps(
        runtime_public_output_bundle_report_to_dict(bundle),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_BYTES:
        raise ValueError("runtime public output bundle report exceeds byte limit")
    return text + "\n"


def _validate_public_output_values(
    outputs: tuple[RuntimePublicOutputValue, ...],
) -> None:
    if type(outputs) is not tuple:
        raise TypeError("runtime public output bundle outputs must be a tuple")
    if not outputs:
        raise ValueError("runtime public output bundle outputs must not be empty")
    if len(outputs) > MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_OUTPUTS:
        raise ValueError("runtime public output bundle output count exceeds limit")
    public_names: list[str] = []
    tensor_names: list[str] = []
    for output in outputs:
        if not isinstance(output, RuntimePublicOutputValue):
            raise TypeError(
                "runtime public output bundle outputs must be public output values"
            )
        public_names.append(output.public_name)
        tensor_names.append(output.tensor_name)
        if not output.readonly:
            raise ValueError("runtime public output bundle values must be read-only")
    if len(public_names) != len(set(public_names)):
        raise ValueError("runtime public output bundle public names must be unique")
    if len(tensor_names) != len(set(tensor_names)):
        raise ValueError("runtime public output bundle tensor names must be unique")


def _validate_value_role(value: str) -> None:
    if value not in _VALUE_ROLES:
        raise ValueError("runtime public output bundle value role unsupported")


def _validate_producer(value_role: str, producer_kind: str, producer_id: str) -> None:
    if producer_kind not in _PRODUCER_KINDS:
        raise ValueError("runtime public output bundle producer kind unsupported")
    _validate_bundle_text(producer_id, "producer_id")
    if value_role == "input" and producer_kind != "external_input":
        raise ValueError(
            "runtime public output bundle input producer must be external_input"
        )
    if value_role == "computed" and producer_kind != "operation":
        raise ValueError(
            "runtime public output bundle computed producer must be operation"
        )


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


def _validate_bundle_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PUBLIC_OUTPUT_BUNDLE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime public output identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime public output bundle field limit")
    if value in _FORBIDDEN_PUBLIC_OUTPUT_BUNDLE_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_FIELD_BYTES",
    "MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_OUTPUTS",
    "MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_BYTES",
    "RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS",
    "RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT",
    "RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION",
    "RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT",
    "RuntimePublicOutputBundle",
    "RuntimePublicOutputBundleError",
    "RuntimePublicOutputValue",
    "assert_runtime_public_output_bundle",
    "build_runtime_public_output_bundle",
    "dump_runtime_public_output_bundle_report",
    "runtime_public_output_bundle_report_to_dict",
]
