from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from examples.bounded_cross_architecture_gpu_proof import (
    SM70_OBSERVATION_PATH,
    SM86_OBSERVATION_PATH,
    assert_bounded_cross_architecture_gpu_proof,
    build_bounded_cross_architecture_gpu_proof,
    dump_bounded_cross_architecture_gpu_proof,
)
from examples.bounded_gpu_observation_proof import GpuObservationError, _digest_payload

SCHEMA_PATH = Path("schemas/bounded_cross_architecture_gpu_proof.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/proofs/bounded_cross_architecture_gpu_proof.json"
)

pytestmark = pytest.mark.skipif(
    not SM70_OBSERVATION_PATH.exists() or not SM86_OBSERVATION_PATH.exists(),
    reason="cross-architecture proof awaits both physical observations",
)


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert type(payload) is dict
    return payload


def _build() -> dict[str, object]:
    return build_bounded_cross_architecture_gpu_proof(
        _load(SM70_OBSERVATION_PATH),
        _load(SM86_OBSERVATION_PATH),
    )


def test_cross_architecture_proof_binds_two_exact_physical_observations() -> None:
    report = _build()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert assert_bounded_cross_architecture_gpu_proof(report) == report
    assert schema["additionalProperties"] is False
    assert [item["accelerator_class"] for item in report["observations"]] == [
        "nvidia_cuda_sm70",
        "nvidia_cuda_sm86",
    ]
    assert report["claim_boundary"]["vendor_count"] == 1
    assert report["claim_boundary"]["universal_compute_claim_proven"] is False
    assert report["claim_boundary"]["independent_reproduction"] == (
        "not_yet_supplied"
    )


def test_cross_architecture_proof_fails_closed_on_claim_widening() -> None:
    report = _build()
    tampered = deepcopy(report)
    tampered["claim_boundary"]["universal_compute_claim_proven"] = True
    digest_source = dict(tampered)
    digest_source.pop("report_digest")
    tampered["report_digest"] = _digest_payload(digest_source)

    with pytest.raises(GpuObservationError, match="claim boundary drift"):
        assert_bounded_cross_architecture_gpu_proof(tampered)


def test_cross_architecture_proof_fails_closed_on_profile_substitution() -> None:
    report = _build()
    tampered = deepcopy(report)
    tampered["observations"][1]["sass_target"] = "sm_90"
    digest_source = dict(tampered)
    digest_source.pop("report_digest")
    tampered["report_digest"] = _digest_payload(digest_source)

    with pytest.raises(GpuObservationError, match="identity drift"):
        assert_bounded_cross_architecture_gpu_proof(tampered)


def test_checked_in_cross_architecture_proof_is_deterministic_and_sanitized() -> None:
    rendered = GOLDEN_PATH.read_text(encoding="utf-8")
    report = _load(GOLDEN_PATH)

    assert dump_bounded_cross_architecture_gpu_proof(report) == rendered
    assert report == _build()
    assert "device_uuid" not in rendered
    assert "driver_version" not in rendered
    assert "host_path" not in rendered
    assert '"raw_tensor_values":' not in rendered
