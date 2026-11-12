"""The standalone candidate is inert; fixture equivalence preserves the old audit."""

import json
import subprocess
import sys
from pathlib import Path

from integration.bounded_model_application.native_consumer import encoded, fixture, input_bytes
from tuc.compiler import backend_bindings_from_json
from tuc.compiler.bounded_source import BoundedBackendBinding

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "integration/bounded_model_cli"


def test_default_observer_is_stdlib_only_and_creates_nothing(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(CLIENT / "consumer.py")],
        cwd=tmp_path, capture_output=True, timeout=15, check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "candidate"
    assert report["native_execution_observed"] is False
    assert report["planned_successful_requests"] == 3
    assert report["planned_rejections"] == 7
    assert not result.stderr and not list(tmp_path.iterdir())


def test_checked_in_example_preserves_original_numerical_context():
    model = json.loads((CLIENT / "model.json").read_bytes())
    assert encoded(model) == fixture(2.0)
    model["parameters"]["w"][0] = 4.0
    assert encoded(model) == fixture(4.0)
    assert encoded(json.loads((CLIENT / "inputs.json").read_bytes())) == (
        input_bytes((1.0, -0.0, 3.0, 4.0))
    )


def test_batch_retains_both_original_variable_inputs():
    batch = json.loads((CLIENT / "batch.json").read_bytes())
    assert [item["id"] for item in batch["requests"]] == ["base", "variable"]
    for item, values in zip(batch["requests"], (
        (1.0, -0.0, 3.0, 4.0), (-2.0, 1.0, 0.0, -0.0),
    ), strict=True):
        assert encoded({"schema_version": "tuc.bounded_cpu_inputs.v0",
                        "inputs": item["inputs"]}) == input_bytes(values)


def test_example_bindings_use_the_original_capability_identity():
    from tuc.backends.base import BackendCapability
    from tuc.backends.bounded_dag import DAGTarget
    from tuc.ir.memory import MemoryDomainKind
    from tuc.ir.model import OperationKind

    assert backend_bindings_from_json((CLIENT / "backends.json").read_bytes()) == (
        BoundedBackendBinding(BackendCapability(
            "cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                              OperationKind.REDUCTION}), memory_domain=MemoryDomainKind.HOST_RAM,
        ), DAGTarget.C11),
    )
