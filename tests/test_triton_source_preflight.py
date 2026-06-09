from __future__ import annotations

from pathlib import Path

import pytest

from tuc.frontend import (
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_BYTES,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    preflight_triton_source,
)

SAFE_SOURCE = """@triton.jit
def kernel(a, b, c):
    offsets = tl.arange(0, 16)
    acc = tl.dot(a, b)
    y = tl.exp(acc + 1.0)
    tl.store(c + offsets, y)
"""


def test_triton_source_preflight_accepts_bounded_syntax_as_data() -> None:
    report = preflight_triton_source(SAFE_SOURCE, source_name="mvp_kernel")

    assert report.accepted is True
    assert report.intake_contract == TRITON_SOURCE_PREFLIGHT_CONTRACT
    assert report.source_bytes == len(SAFE_SOURCE.encode("utf-8"))
    assert report.line_count == 6
    assert report.operation_families == ("elementwise", "matmul")
    assert "python_import" in report.blocked_execution_surfaces
    assert "decorator_evaluation" in report.blocked_execution_surfaces
    assert "jit_execution" in report.blocked_execution_surfaces
    assert report.rejected_features == ()


def test_triton_source_preflight_dump_is_deterministic() -> None:
    report = preflight_triton_source(SAFE_SOURCE, source_name="mvp_kernel")

    assert report.dump() == Path(
        "tests/golden/frontend/triton_source_preflight.txt"
    ).read_text(encoding="utf-8").rstrip("\n")


@pytest.mark.parametrize(
    ("source", "feature"),
    [
        ("import os\n@triton.jit\ndef kernel(a):\n    return a\n", "import_statement"),
        (
            "@triton.jit()\ndef kernel(a):\n    return a\n",
            "decorator_call",
        ),
        (
            "@other.decorator\ndef kernel(a):\n    return a\n",
            "unsupported_decorator",
        ),
        (
            "@triton.jit\ndef kernel(a=eval('1')):\n    return a\n",
            "default_value",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return eval('1')\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return open('/dev/nvidia0')\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return subprocess.run(['x'])\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return socket.create_connection(('x', 1))\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return ctypes.CDLL('kernel.so')\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return getattr(a, 'shape')\n",
            "forbidden_call",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return tl.secret(a)\n",
            "unsupported_call_target",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return tuc.gpu.device\n",
            "hac_ir_neutrality_leak",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return '../device/kernel.so'\n",
            "path_traversal_literal",
        ),
        (
            "@triton.jit\ndef kernel(a):\n    return 'https://example.invalid/kernel'\n",
            "network_literal",
        ),
    ],
)
def test_triton_source_preflight_rejects_execution_surfaces(
    source: str,
    feature: str,
) -> None:
    report = preflight_triton_source(source)

    assert report.accepted is False
    assert feature in report.rejected_features


def test_triton_source_preflight_rejects_oversized_source_before_parsing() -> None:
    report = preflight_triton_source("x" * (MAX_TRITON_SOURCE_BYTES + 1))

    assert report.accepted is False
    assert "source_bytes_exceeded" in report.rejected_features
    assert report.ast_node_count == 0


def test_triton_source_preflight_rejects_excessive_ast_depth() -> None:
    source = "@triton.jit\ndef kernel(a):\n    return " + "(".join(
        "a" for _ in range(MAX_TRITON_SOURCE_AST_DEPTH + 2)
    )

    report = preflight_triton_source(source)

    assert report.accepted is False
    assert "syntax_error" in report.rejected_features or "ast_depth_exceeded" in (
        report.rejected_features
    )


def test_triton_source_preflight_does_not_return_compute_graph() -> None:
    report = preflight_triton_source(SAFE_SOURCE)

    assert not hasattr(report, "to_compute_graph")
