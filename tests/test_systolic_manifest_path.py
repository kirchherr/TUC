from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.systolic_manifest_path import MANIFEST_PATH, run_systolic_manifest_path
from tuc.ir import LayoutKind, MemoryDomainKind, OperationKind
from tuc.manifests import load_backend_capability_manifest

_GOLDEN = Path(__file__).parent / "golden" / "proofs" / "systolic_manifest_path.txt"


def test_systolic_manifest_loads_as_declarative_capability() -> None:
    capability = load_backend_capability_manifest(MANIFEST_PATH)

    assert capability.name == "systolic-sim"
    assert capability.supported_ops == frozenset({OperationKind.MATMUL})
    assert capability.preferred_for == frozenset({OperationKind.MATMUL})
    assert capability.memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert capability.supported_layouts == frozenset({LayoutKind.ROW_MAJOR})
    assert capability.produced_layouts == frozenset({LayoutKind.BLOCKED})


def test_systolic_manifest_path_plans_and_executes_through_trusted_registry() -> None:
    report = run_systolic_manifest_path()

    assert report.registry.names() == ("systolic-sim",)
    assert report.readiness.status == "ready"
    assert report.compiled.partition_plan.backend_for(
        "manifest_systolic_projection"
    ) == "systolic-sim"
    assert report.compiled.partition_plan.backend_for(
        "manifest_host_activation"
    ) == "reference-cpu"
    assert report.compiled.partition_plan.layout_conversions[0].source_layout is (
        LayoutKind.BLOCKED
    )
    assert report.passed


def test_systolic_manifest_path_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/systolic_manifest_path.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "source_label: systolic_sim_backend.json" in completed.stdout
    assert "manifest_systolic_projection -> systolic-sim" in completed.stdout
    assert "manifest_host_activation -> reference-cpu" in completed.stdout
    assert "blocked->row_major" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN.read_text(
        encoding="utf-8"
    ).rstrip("\n")
