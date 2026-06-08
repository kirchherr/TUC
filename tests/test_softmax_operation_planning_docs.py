from __future__ import annotations

from pathlib import Path


def _planning_doc() -> str:
    return Path("docs/SOFTMAX_OPERATION_PLANNING.md").read_text(encoding="utf-8")


def test_softmax_planning_doc_defines_reference_semantics() -> None:
    text = _planning_doc()

    for required in (
        "reference_softmax",
        "shifted = input - max(input, axis, keepdims=True)",
        "output = exp / sum(exp, axis, keepdims=True)",
        "axis is an integer",
        "axis is in bounds",
        "input and output shapes match exactly",
        "input values are finite",
    ):
        assert required in text


def test_softmax_planning_doc_protects_hac_ir_boundary() -> None:
    text = _planning_doc()

    for required in (
        "operation family: `softmax`",
        "operation linearity as `nonlinear`",
        "decomposition into backend-specific kernels",
        "approximation algorithms",
        "backend-specific noise modules",
        "future namespaced `tuc.*` axis attribute requires an explicit dialect RFC",
    ):
        assert required in text


def test_softmax_planning_doc_covers_runtime_and_capability_boundaries() -> None:
    text = _planning_doc()

    for required in (
        "compiler decision reports",
        "runtime-plan dumps",
        "candidate score diagnostics",
        "transfer edges",
        "layout conversions",
        "A backend that supports only matmul, reduction, or elementwise pieces",
        "must not be treated as supporting whole-operation softmax",
    ):
        assert required in text


def test_softmax_planning_doc_covers_security_boundaries() -> None:
    text = _planning_doc()
    rfc = Path("rfcs/0045-softmax-operation-planning.md").read_text(encoding="utf-8")
    combined = f"{text}\n{rfc}"

    for forbidden_surface in (
        "execute backend code",
        "discover plugins",
        "import modules",
        "spawn subprocesses",
        "load dynamic libraries",
        "access devices",
        "execute generated artifacts",
        "touch the network",
        "read host paths",
        "read environment variables",
    ):
        assert forbidden_surface in combined


def test_softmax_planning_doc_defines_proof_gate() -> None:
    text = _planning_doc()

    for required in (
        "HAC-IR golden dump",
        "runtime-plan golden dump",
        "compiler decision-report golden dump",
        "proof report ending in `PASS`",
        "explicit axis validation",
    ):
        assert required in text

