"""Execution-free Triton source preflight checks.

This module does not implement Triton source ingestion. It parses caller-
provided source text as bounded syntax data and returns a deterministic report
that proves which source-parser gates passed or failed.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

TRITON_SOURCE_PREFLIGHT_CONTRACT = "triton_source_preflight.execution_free.v0"
MAX_TRITON_SOURCE_BYTES = 64 * 1024
MAX_TRITON_SOURCE_LINES = 2048
MAX_TRITON_SOURCE_AST_NODES = 8192
MAX_TRITON_SOURCE_AST_DEPTH = 64
MAX_TRITON_SOURCE_IDENTIFIERS = 4096
MAX_TRITON_SOURCE_IDENTIFIER_BYTES = 128
MAX_TRITON_SOURCE_LITERALS = 4096
MAX_TRITON_SOURCE_LITERAL_BYTES = 4096
MAX_TRITON_SOURCE_DIAGNOSTICS = 32
MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES = 4096

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_inspection",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "python_import",
    "subprocess_execution",
)
_DANGEROUS_CALLS = frozenset(
    {
        "__import__",
        "compile",
        "dir",
        "eval",
        "exec",
        "getattr",
        "globals",
        "hasattr",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
)
_DANGEROUS_CALL_PREFIXES = (
    "ctypes.",
    "importlib.",
    "os.environ",
    "os.getenv",
    "os.popen",
    "os.system",
    "pathlib.",
    "socket.",
    "subprocess.",
)
_ALLOWED_TL_CALLS = frozenset(
    {
        "tl.arange",
        "tl.dot",
        "tl.exp",
        "tl.full",
        "tl.load",
        "tl.max",
        "tl.program_id",
        "tl.reshape",
        "tl.softmax",
        "tl.store",
        "tl.sum",
        "tl.trans",
        "tl.where",
        "tl.zeros",
    }
)
_ELEMENTWISE_TL_CALLS = frozenset({"tl.exp", "tl.max", "tl.where"})
_REDUCTION_TL_CALLS = frozenset({"tl.sum"})
_SOFTMAX_TL_CALLS = frozenset({"tl.softmax"})
_MATMUL_TL_CALLS = frozenset({"tl.dot"})


@dataclass(frozen=True)
class TritonSourcePreflightReport:
    """Deterministic evidence for execution-free Triton source preflight."""

    source_name: str
    intake_contract: str
    accepted: bool
    source_bytes: int
    line_count: int
    ast_node_count: int
    ast_depth: int
    identifier_count: int
    literal_count: int
    operation_families: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...]
    rejected_features: tuple[str, ...]
    diagnostics: tuple[str, ...]

    def dump(self) -> str:
        """Render a stable source preflight report."""

        status = "accepted" if self.accepted else "rejected"
        operation_families = _joined_or_dash(self.operation_families)
        blocked = ",".join(self.blocked_execution_surfaces)
        rejected = _joined_or_dash(self.rejected_features)
        diagnostics = _joined_or_dash(self.diagnostics, separator=";")
        return "\n".join(
            (
                f"triton.source_preflight @{self.source_name} {{",
                f'  intake_contract = "{self.intake_contract}"',
                f'  status = "{status}"',
                f"  source_bytes = {self.source_bytes}",
                f"  line_count = {self.line_count}",
                f"  ast_node_count = {self.ast_node_count}",
                f"  ast_depth = {self.ast_depth}",
                f"  identifier_count = {self.identifier_count}",
                f"  literal_count = {self.literal_count}",
                f'  operation_families = "{operation_families}"',
                f'  blocked_execution_surfaces = "{blocked}"',
                f'  rejected_features = "{rejected}"',
                f'  diagnostics = "{diagnostics}"',
                "}",
            )
        )


@dataclass
class _PreflightState:
    source_name: str
    source_bytes: int
    line_count: int
    ast_node_count: int = 0
    ast_depth: int = 0
    identifier_count: int = 0
    literal_count: int = 0
    operation_families: set[str] = field(default_factory=set)
    rejected_features: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


def preflight_triton_source(
    source: str,
    *,
    source_name: str = "triton_source",
) -> TritonSourcePreflightReport:
    """Preflight Triton source text without executing imports, decorators, or JIT."""

    if not isinstance(source, str):
        raise TypeError("triton source preflight input must be source text")
    _validate_source_name(source_name)

    source_bytes, source_utf8_valid = _utf8_byte_length(source)
    line_count = len(source.splitlines())
    state = _PreflightState(
        source_name=source_name,
        source_bytes=source_bytes,
        line_count=line_count,
    )

    if source_bytes == 0:
        _reject(state, "empty_source", "source text must not be empty")
    if not source_utf8_valid:
        _reject(state, "invalid_unicode", "source text must be valid UTF-8 text")
    if source_bytes > MAX_TRITON_SOURCE_BYTES:
        _reject(state, "source_bytes_exceeded", "source byte budget exceeded")
    if line_count > MAX_TRITON_SOURCE_LINES:
        _reject(state, "line_count_exceeded", "source line budget exceeded")
    if state.rejected_features:
        return _report(state)

    try:
        tree = ast.parse(source, filename="<tuc-triton-source>", mode="exec")
    except SyntaxError as exc:
        _reject(state, "syntax_error", f"syntax error at line {_line_or_unknown(exc.lineno)}")
        return _report(state)
    except ValueError:
        _reject(state, "syntax_error", "source text cannot be parsed as Python syntax data")
        return _report(state)
    except RecursionError:
        _reject(state, "parser_recursion", "parser recursion budget exceeded")
        return _report(state)

    _measure_ast(tree, state)
    if _has_budget_rejection(state):
        return _report(state)

    _inspect_tree(tree, state)
    return _report(state)


def _measure_ast(tree: ast.AST, state: _PreflightState) -> None:
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        state.ast_node_count += 1
        state.ast_depth = max(state.ast_depth, depth)
        if state.ast_node_count > MAX_TRITON_SOURCE_AST_NODES:
            _reject(state, "ast_node_count_exceeded", "AST node budget exceeded")
            return
        if state.ast_depth > MAX_TRITON_SOURCE_AST_DEPTH:
            _reject(state, "ast_depth_exceeded", "AST depth budget exceeded")
            return
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))


def _inspect_tree(tree: ast.Module, state: _PreflightState) -> None:
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if not functions:
        _reject(state, "missing_kernel_function", "source must contain a kernel function")
    if len(functions) > 1:
        _reject(state, "multiple_kernel_functions", "source must contain one kernel function")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            _reject(state, "import_statement", f"import statement at line {_node_line(node)}")
        elif isinstance(node, ast.FunctionDef):
            _inspect_function(node, state)
        elif isinstance(node, ast.Call):
            _inspect_call(node, state)
        elif isinstance(node, ast.Attribute):
            _inspect_attribute(node, state)
        elif isinstance(node, ast.Name):
            _record_identifier(node.id, state)
        elif isinstance(node, ast.arg):
            _record_identifier(node.arg, state)
            if node.annotation is not None:
                _reject(state, "annotation", f"annotation at line {_node_line(node)}")
        elif isinstance(node, ast.Constant):
            _inspect_literal(node.value, node, state)
        elif isinstance(node, ast.JoinedStr | ast.FormattedValue):
            _reject(state, "formatted_string", f"formatted string at line {_node_line(node)}")
        elif isinstance(node, ast.ClassDef | ast.AsyncFunctionDef | ast.Lambda):
            _reject(state, "unsupported_syntax", f"unsupported syntax at line {_node_line(node)}")
        elif isinstance(
            node,
            ast.Await
            | ast.Global
            | ast.Nonlocal
            | ast.Raise
            | ast.Try
            | ast.With
            | ast.Yield
            | ast.YieldFrom,
        ):
            _reject(
                state,
                "unsupported_control_flow",
                f"unsupported control flow at line {_node_line(node)}",
            )
        elif isinstance(node, ast.BinOp | ast.BoolOp | ast.Compare | ast.UnaryOp):
            state.operation_families.add("elementwise")


def _inspect_function(node: ast.FunctionDef, state: _PreflightState) -> None:
    _record_identifier(node.name, state)
    if not node.decorator_list:
        _reject(
            state,
            "missing_triton_jit_decorator",
            f"missing @triton.jit decorator at line {_node_line(node)}",
        )
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            _reject(
                state,
                "decorator_call",
                f"decorator call at line {_node_line(decorator)}",
            )
            continue
        name = _expression_name(decorator)
        if name != "triton.jit":
            _reject(
                state,
                "unsupported_decorator",
                f"unsupported decorator at line {_node_line(decorator)}",
            )
    if node.args.defaults or node.args.kw_defaults:
        _reject(state, "default_value", f"default value at line {_node_line(node)}")
    if node.args.vararg is not None or node.args.kwarg is not None:
        _reject(state, "variadic_arguments", f"variadic arguments at line {_node_line(node)}")
    if node.returns is not None:
        _reject(state, "annotation", f"return annotation at line {_node_line(node)}")


def _inspect_call(node: ast.Call, state: _PreflightState) -> None:
    name = _expression_name(node.func)
    if name is None:
        _reject(state, "dynamic_call", f"dynamic call at line {_node_line(node)}")
        return
    if name in _DANGEROUS_CALLS or name.startswith(_DANGEROUS_CALL_PREFIXES):
        _reject(state, "forbidden_call", f"forbidden call at line {_node_line(node)}")
        return
    if name.startswith("tuc."):
        _reject(state, "hac_ir_neutrality_leak", f"tuc.* reference at line {_node_line(node)}")
        return
    if name.startswith("tl."):
        if name not in _ALLOWED_TL_CALLS:
            _reject(
                state,
                "unsupported_call_target",
                f"unsupported Triton call at line {_node_line(node)}",
            )
            return
        _record_operation_family(name, state)
        return
    _reject(state, "unsupported_call_target", f"unsupported call at line {_node_line(node)}")


def _inspect_attribute(node: ast.Attribute, state: _PreflightState) -> None:
    name = _expression_name(node)
    if name is None:
        return
    if name.startswith("tuc."):
        _reject(state, "hac_ir_neutrality_leak", f"tuc.* reference at line {_node_line(node)}")
    if name.startswith("os.environ"):
        _reject(state, "environment_access", f"environment access at line {_node_line(node)}")


def _inspect_literal(value: object, node: ast.AST, state: _PreflightState) -> None:
    if isinstance(value, str | bytes | int | float | complex | bool | type(None)):
        state.literal_count += 1
    if state.literal_count > MAX_TRITON_SOURCE_LITERALS:
        _reject(state, "literal_count_exceeded", "literal count budget exceeded")
        return
    if isinstance(value, str):
        literal_bytes, literal_utf8_valid = _utf8_byte_length(value)
        if not literal_utf8_valid:
            _reject(
                state,
                "invalid_unicode_literal",
                f"string literal must be valid UTF-8 text at line {_node_line(node)}",
            )
        if literal_bytes > MAX_TRITON_SOURCE_LITERAL_BYTES:
            _reject(
                state,
                "literal_bytes_exceeded",
                f"literal byte budget exceeded at line {_node_line(node)}",
            )
        _inspect_string_literal(value, node, state)
    elif isinstance(value, bytes):
        if len(value) > MAX_TRITON_SOURCE_LITERAL_BYTES:
            _reject(
                state,
                "literal_bytes_exceeded",
                f"bytes literal budget exceeded at line {_node_line(node)}",
            )


def _inspect_string_literal(value: str, node: ast.AST, state: _PreflightState) -> None:
    lowered = value.lower()
    if "://" in value:
        _reject(state, "network_literal", f"network-like literal at line {_node_line(node)}")
    if "../" in value or "..\\" in value:
        _reject(
            state,
            "path_traversal_literal",
            f"path traversal literal at line {_node_line(node)}",
        )
    if value.startswith("/dev/") or _WINDOWS_PATH_RE.match(value) is not None:
        _reject(state, "host_path_literal", f"host-path literal at line {_node_line(node)}")
    if lowered.endswith((".dll", ".dylib", ".exe", ".so")):
        _reject(
            state,
            "dynamic_library_literal",
            f"dynamic library literal at line {_node_line(node)}",
        )
    if "tuc." in lowered:
        _reject(state, "hac_ir_neutrality_leak", f"tuc.* literal at line {_node_line(node)}")


def _record_identifier(identifier: str, state: _PreflightState) -> None:
    state.identifier_count += 1
    if state.identifier_count > MAX_TRITON_SOURCE_IDENTIFIERS:
        _reject(state, "identifier_count_exceeded", "identifier count budget exceeded")
    identifier_bytes, identifier_utf8_valid = _utf8_byte_length(identifier)
    if not identifier_utf8_valid:
        _reject(state, "invalid_identifier_unicode", "identifier must be valid UTF-8 text")
    if identifier_bytes > MAX_TRITON_SOURCE_IDENTIFIER_BYTES:
        _reject(state, "identifier_bytes_exceeded", "identifier byte budget exceeded")


def _record_operation_family(call_name: str, state: _PreflightState) -> None:
    if call_name in _MATMUL_TL_CALLS:
        state.operation_families.add("matmul")
    elif call_name in _REDUCTION_TL_CALLS:
        state.operation_families.add("reduction")
    elif call_name in _SOFTMAX_TL_CALLS:
        state.operation_families.add("softmax")
    elif call_name in _ELEMENTWISE_TL_CALLS:
        state.operation_families.add("elementwise")


def _expression_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expression_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _reject(state: _PreflightState, feature: str, diagnostic: str) -> None:
    if feature not in state.rejected_features:
        state.rejected_features.append(feature)
    if _diagnostic_budget_available(state, diagnostic):
        state.diagnostics.append(diagnostic)
    elif "diagnostics_truncated" not in state.rejected_features:
        state.rejected_features.append("diagnostics_truncated")


def _diagnostic_budget_available(state: _PreflightState, diagnostic: str) -> bool:
    if len(state.diagnostics) >= MAX_TRITON_SOURCE_DIAGNOSTICS:
        return False
    current_bytes = sum(len(item.encode("utf-8")) for item in state.diagnostics)
    return current_bytes + len(diagnostic.encode("utf-8")) <= MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES


def _has_budget_rejection(state: _PreflightState) -> bool:
    return any(feature.endswith("_exceeded") for feature in state.rejected_features)


def _report(state: _PreflightState) -> TritonSourcePreflightReport:
    return TritonSourcePreflightReport(
        source_name=state.source_name,
        intake_contract=TRITON_SOURCE_PREFLIGHT_CONTRACT,
        accepted=not state.rejected_features,
        source_bytes=state.source_bytes,
        line_count=state.line_count,
        ast_node_count=state.ast_node_count,
        ast_depth=state.ast_depth,
        identifier_count=state.identifier_count,
        literal_count=state.literal_count,
        operation_families=tuple(sorted(state.operation_families)),
        blocked_execution_surfaces=_BLOCKED_EXECUTION_SURFACES,
        rejected_features=tuple(sorted(state.rejected_features)),
        diagnostics=tuple(state.diagnostics),
    )


def _validate_source_name(source_name: str) -> None:
    if not isinstance(source_name, str) or not _IDENTIFIER_RE.fullmatch(source_name):
        raise ValueError("triton source preflight source_name must be a simple identifier")


def _node_line(node: ast.AST) -> str:
    line = getattr(node, "lineno", None)
    if isinstance(line, int):
        return str(line)
    return "unknown"


def _line_or_unknown(line: object) -> str:
    if isinstance(line, int):
        return str(line)
    return "unknown"


def _utf8_byte_length(value: str) -> tuple[int, bool]:
    try:
        return len(value.encode("utf-8")), True
    except UnicodeEncodeError:
        return len(value.encode("utf-8", errors="backslashreplace")), False


def _joined_or_dash(values: tuple[str, ...], *, separator: str = ",") -> str:
    return separator.join(values) if values else "-"


__all__ = [
    "MAX_TRITON_SOURCE_AST_DEPTH",
    "MAX_TRITON_SOURCE_AST_NODES",
    "MAX_TRITON_SOURCE_BYTES",
    "MAX_TRITON_SOURCE_LINES",
    "TRITON_SOURCE_PREFLIGHT_CONTRACT",
    "TritonSourcePreflightReport",
    "preflight_triton_source",
]
