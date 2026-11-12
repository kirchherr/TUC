"""The native session observer is inert by default and keeps the prior corpus."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from integration.bounded_model_application import native_consumer as original
from integration.bounded_model_application import native_session_consumer as session


def test_candidate_needs_only_standard_library_and_writes_nothing(tmp_path):
    client = Path(session.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(client)], cwd=tmp_path,
        capture_output=True, check=True, timeout=20,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "candidate" and report["native_execution_observed"] is False
    assert report["planned_builds"] == 2 and report["planned_successful_runs"] == 3
    assert not result.stderr and not list(tmp_path.iterdir())


@pytest.mark.parametrize("weight", [2.0, 4.0])
def test_session_observer_preserves_the_independently_audited_models(weight):
    assert session.fixture(weight) == original.fixture(weight)


@pytest.mark.parametrize("values", [(1.0, -0.0, 3.0, 4.0), (-2.0, 1.0, 0.0, -0.0)])
def test_session_observer_preserves_the_original_input_bits(values):
    assert session.input_bytes(values) == original.input_bytes(values)
