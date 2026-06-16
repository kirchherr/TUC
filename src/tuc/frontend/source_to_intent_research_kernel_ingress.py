"""Execution-free Triton module ingress for the explicit research parser.

This module accepts a tiny Triton-like module source buffer as data, validates a
bounded import prelude, extracts one `@triton.jit` kernel function, and forwards
only that extracted function source to the existing explicit research parser.

It does not import Python modules, evaluate decorators, inspect live functions,
read files, execute JIT code, or emit compiler artifacts.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParseResult,
    parse_triton_source_to_source_intent,
    source_to_intent_research_parse_report_to_dict,
)
from tuc.frontend.triton_source import (
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_AST_NODES,
    MAX_TRITON_SOURCE_BYTES,
    MAX_TRITON_SOURCE_LINES,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT = (
    "source_to_intent_research_kernel_ingress.execution_free.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY = (
    "single_triton_module_source_buffer_only"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY = (
    "extracted_kernel_source_to_source_intent.v0_plain_data"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES = ("tl", "triton")
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS = (
    "general_triton_source_ingestion",
    "native_performance_claim",
    "production_parser",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS = (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES = tuple(
    sorted(
        {
            *SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
            "module_import_execution",
            "module_top_level_execution",
            "python_function_object_ingestion",
        }
    )
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class SourceToIntentResearchKernelIngressError(ValueError):
    """Raised when module ingress rejects source input."""


@dataclass(frozen=True)
class SourceToIntentResearchKernelIngressReport:
    """Metadata-only evidence for explicit module-source kernel ingress."""

    source_name: str
    kernel_name: str
    module_digest: str
    extracted_kernel_digest: str
    parser_report_digest: str
    source_intent_digest: str
    module_bytes: int
    module_line_count: int
    module_ast_node_count: int
    module_ast_depth: int
    import_count: int
    top_level_function_count: int
    operation_families: tuple[str, ...]
    tensor_count: int
    operation_count: int
    return_count: int
    ingress_contract: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    input_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY
    output_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY
    parser_output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    raw_source_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY
    raw_value_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY
    allowed_import_aliases: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES
    )
    blocked_claims: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS
    )
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_identifier(self.source_name, "kernel ingress source_name")
        _validate_identifier(self.kernel_name, "kernel ingress kernel_name")
        for label, digest in (
            ("module_digest", self.module_digest),
            ("extracted_kernel_digest", self.extracted_kernel_digest),
            ("parser_report_digest", self.parser_report_digest),
            ("source_intent_digest", self.source_intent_digest),
        ):
            if not isinstance(digest, str) or not _SHA256_DIGEST_RE.fullmatch(digest):
                raise ValueError(f"kernel ingress {label} must be sha256 digest")
        for label, value in (
            ("module_bytes", self.module_bytes),
            ("module_line_count", self.module_line_count),
            ("module_ast_node_count", self.module_ast_node_count),
            ("module_ast_depth", self.module_ast_depth),
            ("import_count", self.import_count),
            ("top_level_function_count", self.top_level_function_count),
            ("tensor_count", self.tensor_count),
            ("operation_count", self.operation_count),
            ("return_count", self.return_count),
        ):
            _validate_bounded_int(value, label)
        if self.import_count != 2:
            raise ValueError("kernel ingress requires exactly two allowed imports")
        if self.top_level_function_count != 1:
            raise ValueError("kernel ingress requires exactly one top-level function")
        if self.ingress_contract != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT:
            raise ValueError("kernel ingress contract mismatch")
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("kernel ingress parser status mismatch")
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise ValueError("kernel ingress default parser status mismatch")
        if self.input_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY:
            raise ValueError("kernel ingress input policy mismatch")
        if self.output_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY:
            raise ValueError("kernel ingress output policy mismatch")
        if self.parser_output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("kernel ingress parser output policy mismatch")
        if self.raw_source_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY:
            raise ValueError("kernel ingress raw source policy mismatch")
        if self.raw_value_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY:
            raise ValueError("kernel ingress raw value policy mismatch")
        if self.allowed_import_aliases != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES
        ):
            raise ValueError("kernel ingress allowed import aliases mismatch")
        if self.blocked_claims != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS:
            raise ValueError("kernel ingress blocked claims mismatch")
        if self.blocked_compiler_outputs != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("kernel ingress blocked compiler outputs mismatch")
        if self.blocked_execution_surfaces != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("kernel ingress blocked execution surfaces mismatch")
        _validate_operation_families(self.operation_families)


@dataclass(frozen=True)
class SourceToIntentResearchKernelIngressResult:
    """Module ingress output plus explicit research parser result."""

    parser_result: SourceToIntentResearchParseResult
    report: SourceToIntentResearchKernelIngressReport


def ingest_triton_module_source_to_source_intent(
    module_source: str,
    *,
    source_name: str,
    kernel_name: str,
    tensor_shapes: Mapping[str, Sequence[int]],
) -> SourceToIntentResearchKernelIngressResult:
    """Extract one trusted-shape research kernel from module source as data."""

    if not isinstance(module_source, str):
        raise TypeError("kernel ingress input must be module source text")
    _validate_identifier(source_name, "kernel ingress source_name")
    _validate_identifier(kernel_name, "kernel ingress kernel_name")

    module_bytes = _source_bytes(module_source)
    line_count = len(module_source.splitlines())
    if module_bytes == 0:
        raise SourceToIntentResearchKernelIngressError("module source must not be empty")
    if module_bytes > MAX_TRITON_SOURCE_BYTES:
        raise SourceToIntentResearchKernelIngressError("module source byte budget exceeded")
    if line_count > MAX_TRITON_SOURCE_LINES:
        raise SourceToIntentResearchKernelIngressError("module source line budget exceeded")

    tree = _parse_module(module_source)
    ast_node_count, ast_depth = _measure_ast(tree)
    imports, function = _validate_module_shape(tree, kernel_name)
    extracted_kernel_source = _extract_function_source(module_source, function)

    parser_result = parse_triton_source_to_source_intent(
        extracted_kernel_source,
        source_name=source_name,
        tensor_shapes=tensor_shapes,
    )
    parser_report = source_to_intent_research_parse_report_to_dict(
        parser_result.report
    )
    payload_text = _canonical_json(parser_result.source_intent_payload)
    report = SourceToIntentResearchKernelIngressReport(
        source_name=source_name,
        kernel_name=kernel_name,
        module_digest=_digest(module_source),
        extracted_kernel_digest=_digest(extracted_kernel_source),
        parser_report_digest=_digest(_canonical_json(parser_report)),
        source_intent_digest=_digest(payload_text),
        module_bytes=module_bytes,
        module_line_count=line_count,
        module_ast_node_count=ast_node_count,
        module_ast_depth=ast_depth,
        import_count=len(imports),
        top_level_function_count=1,
        operation_families=tuple(parser_result.report.operation_families),
        tensor_count=parser_result.report.tensor_count,
        operation_count=parser_result.report.operation_count,
        return_count=parser_result.report.return_count,
    )
    return SourceToIntentResearchKernelIngressResult(
        parser_result=parser_result,
        report=report,
    )


def source_to_intent_research_kernel_ingress_report_to_dict(
    report: SourceToIntentResearchKernelIngressReport,
) -> dict[str, object]:
    """Return a JSON-compatible metadata-only kernel ingress report."""

    if not isinstance(report, SourceToIntentResearchKernelIngressReport):
        raise TypeError("kernel ingress report must be report object")
    return {
        "allowed_import_aliases": list(report.allowed_import_aliases),
        "blocked_claims": list(report.blocked_claims),
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "default_parser_status": report.default_parser_status,
        "extracted_kernel_digest": report.extracted_kernel_digest,
        "import_count": report.import_count,
        "ingress_contract": report.ingress_contract,
        "input_policy": report.input_policy,
        "kernel_name": report.kernel_name,
        "module_ast_depth": report.module_ast_depth,
        "module_ast_node_count": report.module_ast_node_count,
        "module_bytes": report.module_bytes,
        "module_digest": report.module_digest,
        "module_line_count": report.module_line_count,
        "operation_count": report.operation_count,
        "operation_families": list(report.operation_families),
        "output_policy": report.output_policy,
        "parser_output_policy": report.parser_output_policy,
        "parser_report_digest": report.parser_report_digest,
        "parser_status": report.parser_status,
        "raw_source_policy": report.raw_source_policy,
        "raw_value_policy": report.raw_value_policy,
        "return_count": report.return_count,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REPORT_SCHEMA_VERSION,
        "source_intent_digest": report.source_intent_digest,
        "source_name": report.source_name,
        "tensor_count": report.tensor_count,
        "top_level_function_count": report.top_level_function_count,
    }


def dump_source_to_intent_research_kernel_ingress_report(
    report: SourceToIntentResearchKernelIngressReport,
) -> str:
    """Render stable, source-free JSON evidence for kernel ingress."""

    payload = source_to_intent_research_kernel_ingress_report_to_dict(report)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_module(module_source: str) -> ast.Module:
    try:
        parsed = ast.parse(module_source, filename="<tuc-triton-module>", mode="exec")
    except SyntaxError as exc:
        raise SourceToIntentResearchKernelIngressError(
            "module source syntax is invalid"
        ) from exc
    except RecursionError as exc:
        raise SourceToIntentResearchKernelIngressError(
            "module parser recursion exceeded"
        ) from exc
    if not isinstance(parsed, ast.Module):
        raise SourceToIntentResearchKernelIngressError(
            "module parser returned non-module AST"
        )
    return parsed


def _measure_ast(tree: ast.AST) -> tuple[int, int]:
    node_count = 0
    max_depth = 0
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        node_count += 1
        max_depth = max(max_depth, depth)
        if node_count > MAX_TRITON_SOURCE_AST_NODES:
            raise SourceToIntentResearchKernelIngressError(
                "module AST node budget exceeded"
            )
        if max_depth > MAX_TRITON_SOURCE_AST_DEPTH:
            raise SourceToIntentResearchKernelIngressError(
                "module AST depth budget exceeded"
            )
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))
    return node_count, max_depth


def _validate_module_shape(
    tree: ast.Module,
    kernel_name: str,
) -> tuple[tuple[str, ...], ast.FunctionDef]:
    imports: list[str] = []
    functions: list[ast.FunctionDef] = []
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            imports.append(_validate_import(statement))
        elif isinstance(statement, ast.ImportFrom):
            raise SourceToIntentResearchKernelIngressError(
                "kernel ingress forbids import-from statements"
            )
        elif isinstance(statement, ast.FunctionDef):
            functions.append(statement)
        else:
            raise SourceToIntentResearchKernelIngressError(
                "kernel ingress supports only imports and one kernel function"
            )
    if tuple(sorted(imports)) != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES:
        raise SourceToIntentResearchKernelIngressError(
            "kernel ingress requires import triton and import triton.language as tl"
        )
    if len(imports) != len(set(imports)):
        raise SourceToIntentResearchKernelIngressError(
            "kernel ingress import aliases must be unique"
        )
    if len(functions) != 1:
        raise SourceToIntentResearchKernelIngressError(
            "kernel ingress requires exactly one top-level kernel function"
        )
    function = functions[0]
    if function.name != kernel_name:
        raise SourceToIntentResearchKernelIngressError(
            "kernel ingress target kernel name mismatch"
        )
    return tuple(imports), function


def _validate_import(statement: ast.Import) -> str:
    if len(statement.names) != 1:
        raise SourceToIntentResearchKernelIngressError(
            "kernel ingress import statements must contain one alias"
        )
    alias = statement.names[0]
    if alias.name == "triton" and alias.asname is None:
        return "triton"
    if alias.name == "triton.language" and alias.asname == "tl":
        return "tl"
    raise SourceToIntentResearchKernelIngressError(
        "kernel ingress supports only import triton and import triton.language as tl"
    )


def _extract_function_source(module_source: str, function: ast.FunctionDef) -> str:
    start_line = function.lineno
    if function.decorator_list:
        start_line = min(
            getattr(decorator, "lineno", start_line)
            for decorator in function.decorator_list
        )
    end_line = getattr(function, "end_lineno", None)
    if not isinstance(end_line, int) or end_line < start_line:
        raise SourceToIntentResearchKernelIngressError("kernel source extraction failed")
    lines = module_source.splitlines(keepends=True)
    extracted = "".join(lines[start_line - 1 : end_line])
    if not extracted.strip():
        raise SourceToIntentResearchKernelIngressError("kernel source extraction failed")
    return extracted


def _source_bytes(source: str) -> int:
    try:
        return len(source.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise SourceToIntentResearchKernelIngressError(
            "module source must be valid UTF-8 text"
        ) from exc


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


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REPORT_SCHEMA_VERSION",
    "SourceToIntentResearchKernelIngressError",
    "SourceToIntentResearchKernelIngressReport",
    "SourceToIntentResearchKernelIngressResult",
    "dump_source_to_intent_research_kernel_ingress_report",
    "ingest_triton_module_source_to_source_intent",
    "source_to_intent_research_kernel_ingress_report_to_dict",
]
