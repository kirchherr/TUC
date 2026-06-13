"""Explicit, execution-free Source-to-Intent research parser slice.

This module implements a deliberately tiny Triton-like parser for research
evidence. It accepts caller-provided source text plus a caller-provided tensor
shape manifest, runs the existing execution-free Triton preflight first, parses
Python syntax as data with `ast.parse`, and emits only `source_intent.v0` plain
data.

It is not connected to metadata lowering, graph construction, runtime planning,
backend decisions, file reads, imports, decorator evaluation, JIT, or plugin
discovery.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
)
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)
from tuc.frontend.triton_source import (
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    TritonSourcePreflightReport,
    preflight_triton_source,
)

SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_parser_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT = (
    "source_to_intent_research_parser.execution_free.v0"
)
SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS = "research_explicit_only"
SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS = "default_parser_blocked"
SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY = (
    "source_intent.v0_plain_data_only"
)
SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS = (
    "metadata",
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
)
SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES = (
    "backend_artifact_execution",
    "bytecode_compilation",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "environment_dependent_behavior",
    "file_system_access",
    "frontend_module_import",
    "generated_artifact_execution",
    "network_access",
    "plugin_discovery",
    "python_function_inspection",
    "subprocess_execution",
    "triton_jit_execution",
)
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_SHAPES = 64
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_OPERATIONS = 32
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_RETURNS = 16
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_BYTES = 64 * 1024
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_RANK = 8
MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_DIMENSION = 2**31 - 1

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SUPPORTED_CALLS = frozenset({"tl.dot", "tl.softmax", "tl.sum", "tl.where"})


class SourceToIntentResearchParserError(ValueError):
    """Raised when the explicit research parser rejects source input."""


@dataclass(frozen=True)
class SourceToIntentResearchParseReport:
    """Metadata-only evidence for an explicit Source-to-Intent parse."""

    source_name: str
    source_digest: str
    source_bytes: int
    line_count: int
    preflight_contract: str
    preflight_ast_node_count: int
    preflight_ast_depth: int
    operation_families: tuple[str, ...]
    tensor_count: int
    operation_count: int
    return_count: int
    parser_contract: str = SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    source_intent_contract: str = SOURCE_INTENT_IR_CONTRACT
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_identifier(self.source_name, "source-to-intent parser source_name")
        if not self.source_digest.startswith("sha256:"):
            raise ValueError("source-to-intent research parser digest must be sha256")
        _validate_bounded_int(self.source_bytes, "source_bytes")
        _validate_bounded_int(self.line_count, "line_count")
        _validate_bounded_int(self.preflight_ast_node_count, "preflight_ast_node_count")
        _validate_bounded_int(self.preflight_ast_depth, "preflight_ast_depth")
        _validate_bounded_int(self.tensor_count, "tensor_count")
        _validate_bounded_int(self.operation_count, "operation_count")
        _validate_bounded_int(self.return_count, "return_count")
        if self.preflight_contract != TRITON_SOURCE_PREFLIGHT_CONTRACT:
            raise ValueError("source-to-intent parser preflight contract mismatch")
        if self.parser_contract != SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT:
            raise ValueError("source-to-intent research parser contract mismatch")
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("source-to-intent research parser status mismatch")
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise ValueError("source-to-intent default parser status mismatch")
        if self.output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("source-to-intent parser output policy mismatch")
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise ValueError("source-to-intent parser source-intent schema mismatch")
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise ValueError("source-to-intent parser source-intent contract mismatch")
        if self.blocked_compiler_outputs != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent parser blocked compiler outputs changed")
        if self.blocked_execution_surfaces != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent parser blocked surfaces changed")
        _validate_operation_families(self.operation_families)
        if self.operation_count > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_OPERATIONS:
            raise ValueError("source-to-intent parser operation count exceeds limit")
        if self.return_count > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_RETURNS:
            raise ValueError("source-to-intent parser return count exceeds limit")


@dataclass(frozen=True)
class SourceToIntentResearchParseResult:
    """Explicit research parser output and its metadata-only report."""

    module: SourceIntentModule
    source_intent_payload: Mapping[str, object]
    report: SourceToIntentResearchParseReport


@dataclass
class _ParseState:
    function: ast.FunctionDef
    shape_manifest: Mapping[str, tuple[int, ...]]
    tensors: list[dict[str, object]]
    operations: list[dict[str, object]]
    returns: list[dict[str, object]]
    value_shapes: dict[str, tuple[int, ...]]
    module_tensor_names: set[str]
    produced_names: set[str]


def parse_triton_source_to_source_intent(
    source: str,
    *,
    source_name: str,
    tensor_shapes: Mapping[str, Sequence[int]],
) -> SourceToIntentResearchParseResult:
    """Parse a tiny Triton-like source subset into Source Intent plain data.

    The parser is explicit research evidence only. It accepts no file paths,
    imports no modules, evaluates no decorators, executes no bytecode, and emits
    no compiler artifacts beyond validated `source_intent.v0` plain data.
    """

    if not isinstance(source, str):
        raise TypeError("source-to-intent research parser input must be source text")
    _validate_identifier(source_name, "source-to-intent parser source_name")
    shape_manifest = _shape_manifest_from_mapping(tensor_shapes)

    preflight = preflight_triton_source(source, source_name=source_name)
    if not preflight.accepted:
        rejected = ",".join(preflight.rejected_features)
        raise SourceToIntentResearchParserError(
            f"source-to-intent preflight rejected source: {rejected}"
        )

    tree = _parse_ast(source)
    function = _single_function(tree)
    _validate_shape_manifest_covers_function(function, shape_manifest)
    state = _ParseState(
        function=function,
        shape_manifest=shape_manifest,
        tensors=[],
        operations=[],
        returns=[],
        value_shapes=dict(shape_manifest),
        module_tensor_names=set(),
        produced_names=set(),
    )
    _parse_function_body(state)

    payload: dict[str, object] = {
        "name": source_name,
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": state.tensors,
        "operations": state.operations,
        "returns": state.returns,
    }
    try:
        module = source_intent_from_mapping(payload)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchParserError(
            f"source intent validation failed: {exc}"
        ) from exc

    report = _build_report(source, source_name, preflight, module)
    return SourceToIntentResearchParseResult(
        module=module,
        source_intent_payload=payload,
        report=report,
    )


def source_to_intent_research_parse_report_to_dict(
    report: SourceToIntentResearchParseReport,
) -> dict[str, object]:
    """Return a JSON-compatible research parser report."""

    if not isinstance(report, SourceToIntentResearchParseReport):
        raise TypeError("source-to-intent research parser report must be report object")
    return {
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "default_parser_status": report.default_parser_status,
        "line_count": report.line_count,
        "operation_count": report.operation_count,
        "operation_families": list(report.operation_families),
        "output_policy": report.output_policy,
        "parser_contract": report.parser_contract,
        "parser_status": report.parser_status,
        "preflight_ast_depth": report.preflight_ast_depth,
        "preflight_ast_node_count": report.preflight_ast_node_count,
        "preflight_contract": report.preflight_contract,
        "return_count": report.return_count,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION,
        "source_bytes": report.source_bytes,
        "source_digest": report.source_digest,
        "source_intent_contract": report.source_intent_contract,
        "source_intent_schema_version": report.source_intent_schema_version,
        "source_name": report.source_name,
        "tensor_count": report.tensor_count,
    }


def dump_source_to_intent_research_parse_result(
    result: SourceToIntentResearchParseResult,
) -> str:
    """Render stable JSON evidence for an explicit research parse result."""

    if not isinstance(result, SourceToIntentResearchParseResult):
        raise TypeError("source-to-intent research parser result must be result object")
    payload = {
        "report": source_to_intent_research_parse_report_to_dict(result.report),
        "source_intent": result.source_intent_payload,
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if (
        len(text.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_BYTES
    ):
        raise ValueError("source-to-intent research parser report exceeds byte limit")
    return text + "\n"


def _parse_ast(source: str) -> ast.Module:
    try:
        parsed = ast.parse(source, filename="<tuc-source-to-intent>", mode="exec")
    except SyntaxError as exc:
        raise SourceToIntentResearchParserError("source syntax is invalid") from exc
    except RecursionError as exc:
        raise SourceToIntentResearchParserError("source parser recursion exceeded") from exc
    if not isinstance(parsed, ast.Module):
        raise SourceToIntentResearchParserError("source parser returned non-module AST")
    return parsed


def _single_function(tree: ast.Module) -> ast.FunctionDef:
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or len(tree.body) != 1:
        raise SourceToIntentResearchParserError(
            "source-to-intent parser requires exactly one kernel function"
        )
    function = functions[0]
    if len(function.decorator_list) != 1:
        raise SourceToIntentResearchParserError(
            "source-to-intent parser requires one @triton.jit decorator"
        )
    if _expression_name(function.decorator_list[0]) != "triton.jit":
        raise SourceToIntentResearchParserError(
            "source-to-intent parser requires @triton.jit decorator data"
        )
    return function


def _validate_shape_manifest_covers_function(
    function: ast.FunctionDef,
    shape_manifest: Mapping[str, tuple[int, ...]],
) -> None:
    if (
        function.args.posonlyargs
        or function.args.kwonlyargs
        or function.args.vararg is not None
        or function.args.kwarg is not None
        or function.args.defaults
        or function.args.kw_defaults
    ):
        raise SourceToIntentResearchParserError(
            "kernel arguments must be simple positional arguments"
        )
    arg_names = tuple(argument.arg for argument in function.args.args)
    for name in arg_names:
        _validate_identifier(name, "source-to-intent parser argument")
    if len(set(arg_names)) != len(arg_names):
        raise SourceToIntentResearchParserError("kernel arguments must be unique")
    missing = sorted(set(arg_names) - set(shape_manifest))
    unknown = sorted(set(shape_manifest) - set(arg_names))
    if missing:
        raise SourceToIntentResearchParserError("tensor shape manifest missing argument")
    if unknown:
        raise SourceToIntentResearchParserError("tensor shape manifest has unknown key")


def _parse_function_body(state: _ParseState) -> None:
    for statement in state.function.body:
        if isinstance(statement, ast.Assign):
            _parse_assignment(statement, state)
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            if _expression_name(statement.value.func) != "tl.store":
                raise SourceToIntentResearchParserError(
                    "source-to-intent parser supports only tl.store expression calls"
                )
            _parse_store(statement.value, state)
        else:
            raise SourceToIntentResearchParserError(
                "source-to-intent parser supports only assignments and tl.store"
            )
    if not state.operations:
        raise SourceToIntentResearchParserError("source-to-intent parser found no operations")
    if not state.returns:
        raise SourceToIntentResearchParserError("source-to-intent parser found no returns")


def _parse_assignment(statement: ast.Assign, state: _ParseState) -> None:
    if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
        raise SourceToIntentResearchParserError("assignment target must be a name")
    target = statement.targets[0].id
    _validate_identifier(target, "source-to-intent parser assignment target")
    if target in state.value_shapes:
        raise SourceToIntentResearchParserError("assignment target must be new")
    if not isinstance(statement.value, ast.Call):
        raise SourceToIntentResearchParserError("assignment value must be a supported call")
    call_name = _expression_name(statement.value.func)
    if call_name not in _SUPPORTED_CALLS:
        raise SourceToIntentResearchParserError("assignment call target unsupported")
    if call_name == "tl.dot":
        family, inputs, shape, attributes = _parse_dot(statement.value, state)
    elif call_name == "tl.where":
        family, inputs, shape, attributes = _parse_where(statement.value, state)
    elif call_name == "tl.softmax":
        family, inputs, shape, attributes = _parse_softmax(statement.value, state)
    elif call_name == "tl.sum":
        family, inputs, shape, attributes = _parse_sum(statement.value, state)
    else:
        raise SourceToIntentResearchParserError("assignment call target unsupported")

    state.value_shapes[target] = shape
    state.produced_names.add(target)
    for input_name in inputs:
        _add_tensor_if_absent(input_name, state.value_shapes[input_name], state)
    _add_tensor_if_absent(target, shape, state)
    operation: dict[str, object] = {
        "family": family,
        "hints": {},
        "inputs": list(inputs),
        "name": target,
        "outputs": [target],
    }
    if attributes:
        operation["attributes"] = attributes
    state.operations.append(operation)


def _parse_dot(
    call: ast.Call,
    state: _ParseState,
) -> tuple[str, tuple[str, ...], tuple[int, ...], dict[str, object]]:
    if len(call.args) != 2 or call.keywords:
        raise SourceToIntentResearchParserError("tl.dot requires two positional tensors")
    lhs = _name_argument(call.args[0], "tl.dot lhs")
    rhs = _name_argument(call.args[1], "tl.dot rhs")
    lhs_shape = _known_shape(lhs, state)
    rhs_shape = _known_shape(rhs, state)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2:
        raise SourceToIntentResearchParserError("tl.dot requires rank-2 tensors")
    if lhs_shape[1] != rhs_shape[0]:
        raise SourceToIntentResearchParserError("tl.dot inner dimensions must match")
    return "matmul", (lhs, rhs), (lhs_shape[0], rhs_shape[1]), {}


def _parse_where(
    call: ast.Call,
    state: _ParseState,
) -> tuple[str, tuple[str, ...], tuple[int, ...], dict[str, object]]:
    if len(call.args) != 3 or call.keywords:
        raise SourceToIntentResearchParserError("tl.where requires three positional inputs")
    inputs = _unique_names(
        name
        for argument in call.args
        for name in _names_in_expression(argument)
    )
    if not inputs:
        raise SourceToIntentResearchParserError("tl.where requires tensor input data")
    shapes = tuple(_known_shape(name, state) for name in inputs)
    if len(set(shapes)) != 1:
        raise SourceToIntentResearchParserError("tl.where tensor input shapes must match")
    return "elementwise", inputs, shapes[0], {}


def _parse_softmax(
    call: ast.Call,
    state: _ParseState,
) -> tuple[str, tuple[str, ...], tuple[int, ...], dict[str, object]]:
    if len(call.args) != 1:
        raise SourceToIntentResearchParserError("tl.softmax requires one tensor input")
    input_name = _name_argument(call.args[0], "tl.softmax input")
    shape = _known_shape(input_name, state)
    axis = _require_axis(call, shape, "tl.softmax")
    return "softmax", (input_name,), shape, {"axis": axis}


def _parse_sum(
    call: ast.Call,
    state: _ParseState,
) -> tuple[str, tuple[str, ...], tuple[int, ...], dict[str, object]]:
    if len(call.args) != 1:
        raise SourceToIntentResearchParserError("tl.sum requires one tensor input")
    input_name = _name_argument(call.args[0], "tl.sum input")
    input_shape = _known_shape(input_name, state)
    axis = _require_axis(call, input_shape, "tl.sum")
    output_shape = input_shape[:axis] + input_shape[axis + 1 :]
    if not output_shape:
        raise SourceToIntentResearchParserError("tl.sum scalar output unsupported")
    return "reduction", (input_name,), output_shape, {"axis": axis}


def _parse_store(call: ast.Call, state: _ParseState) -> None:
    if len(call.args) != 2 or call.keywords:
        raise SourceToIntentResearchParserError("tl.store requires target and value")
    public_name = _name_argument(call.args[0], "tl.store target")
    tensor_name = _name_argument(call.args[1], "tl.store value")
    if public_name not in state.shape_manifest:
        raise SourceToIntentResearchParserError("tl.store target must be a kernel argument")
    if tensor_name not in state.produced_names:
        raise SourceToIntentResearchParserError("tl.store value must be produced by an op")
    if state.shape_manifest[public_name] != state.value_shapes[tensor_name]:
        raise SourceToIntentResearchParserError("tl.store target shape mismatch")
    state.returns.append(
        {
            "public_name": public_name,
            "required": True,
            "tensor_name": tensor_name,
        }
    )


def _require_axis(call: ast.Call, shape: tuple[int, ...], label: str) -> int:
    if len(call.keywords) != 1 or call.keywords[0].arg != "axis":
        raise SourceToIntentResearchParserError(f"{label} requires explicit axis keyword")
    value = call.keywords[0].value
    if not isinstance(value, ast.Constant) or not isinstance(value.value, int):
        raise SourceToIntentResearchParserError(f"{label} axis must be an integer literal")
    axis = value.value
    if isinstance(axis, bool) or axis < 0 or axis >= len(shape):
        raise SourceToIntentResearchParserError(f"{label} axis is out of bounds")
    return axis


def _add_tensor_if_absent(
    name: str,
    shape: tuple[int, ...],
    state: _ParseState,
) -> None:
    if name in state.module_tensor_names:
        return
    state.module_tensor_names.add(name)
    state.tensors.append({"dtype": "float32", "name": name, "shape": list(shape)})


def _known_shape(name: str, state: _ParseState) -> tuple[int, ...]:
    if name not in state.value_shapes:
        raise SourceToIntentResearchParserError("source expression references unknown tensor")
    return state.value_shapes[name]


def _name_argument(node: ast.AST, label: str) -> str:
    if not isinstance(node, ast.Name):
        raise SourceToIntentResearchParserError(f"{label} must be a simple name")
    _validate_identifier(node.id, label)
    return node.id


def _names_in_expression(node: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            _validate_identifier(child.id, "source expression name")
            names.append(child.id)
    return tuple(names)


def _unique_names(values: Iterable[str]) -> tuple[str, ...]:
    names: list[str] = []
    for value in values:
        if value not in names:
            names.append(value)
    return tuple(names)


def _expression_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expression_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _shape_manifest_from_mapping(
    tensor_shapes: Mapping[str, Sequence[int]],
) -> Mapping[str, tuple[int, ...]]:
    if not isinstance(tensor_shapes, Mapping):
        raise TypeError("tensor shape manifest must be a mapping")
    if not tensor_shapes:
        raise ValueError("tensor shape manifest must not be empty")
    if len(tensor_shapes) > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_SHAPES:
        raise ValueError("tensor shape manifest exceeds entry limit")
    parsed: dict[str, tuple[int, ...]] = {}
    for name, shape in tensor_shapes.items():
        _validate_identifier(name, "tensor shape manifest key")
        parsed[name] = _shape_from_sequence(shape)
    return parsed


def _shape_from_sequence(shape: Sequence[int]) -> tuple[int, ...]:
    if type(shape) not in (list, tuple):
        raise TypeError("tensor shape must be a plain list or tuple")
    dimensions = tuple(shape)
    if not dimensions:
        raise ValueError("tensor shape must not be empty")
    if len(dimensions) > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_RANK:
        raise ValueError("tensor shape rank exceeds limit")
    for dimension in dimensions:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_DIMENSION
        ):
            raise ValueError("tensor shape dimensions must be positive bounded integers")
    return dimensions


def _build_report(
    source: str,
    source_name: str,
    preflight: TritonSourcePreflightReport,
    module: SourceIntentModule,
) -> SourceToIntentResearchParseReport:
    source_bytes = source.encode("utf-8")
    return SourceToIntentResearchParseReport(
        source_name=source_name,
        source_digest=f"sha256:{sha256(source_bytes).hexdigest()}",
        source_bytes=len(source_bytes),
        line_count=preflight.line_count,
        preflight_contract=preflight.intake_contract,
        preflight_ast_node_count=preflight.ast_node_count,
        preflight_ast_depth=preflight.ast_depth,
        operation_families=tuple(sorted({op.family for op in module.operations})),
        tensor_count=len(module.tensors),
        operation_count=len(module.operations),
        return_count=len(module.returns),
    )


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple identifier")


def _validate_bounded_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _validate_operation_families(values: tuple[str, ...]) -> None:
    if type(values) is not tuple:
        raise TypeError("operation families must be a tuple")
    if tuple(sorted(values)) != values:
        raise ValueError("operation families must be sorted")
    if len(set(values)) != len(values):
        raise ValueError("operation families must be unique")
    for value in values:
        if value not in {"elementwise", "matmul", "reduction", "softmax"}:
            raise ValueError("operation family unsupported")


__all__ = [
    "MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_OPERATIONS",
    "MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_BYTES",
    "MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_RETURNS",
    "MAX_SOURCE_TO_INTENT_RESEARCH_PARSER_SHAPES",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS",
    "SourceToIntentResearchParseReport",
    "SourceToIntentResearchParseResult",
    "SourceToIntentResearchParserError",
    "dump_source_to_intent_research_parse_result",
    "parse_triton_source_to_source_intent",
    "source_to_intent_research_parse_report_to_dict",
]
