from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import examples.bounded_compiler_emitted_c11_emission as emission
import examples.bounded_compiler_emitted_c11_proof as c11_proof
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from examples.bounded_compiler_emitted_c11_emission import (
    build_c11_compiler_emission_artifacts,
    dump_c11_compiler_emission_plan,
    validate_checked_in_c11_compiler_emission,
)
from examples.bounded_compiler_emitted_c11_proof import (
    C11_DOCKERFILE_PATH,
    C11_GOLDEN_PATH,
    C11_HARNESS_PATH,
    C11_SCHEMA_PATH,
    BoundedCompilerEmittedC11ProofError,
    _expected_labels,
    _expected_worker_response,
    _synthetic_compose_config,
    _validate_compose_config,
    _validate_image_metadata,
    _validate_worker_response,
    _worker_command,
    assert_compiler_emitted_c11_observation_report,
    build_compiler_emitted_c11_observation_report,
    dump_compiler_emitted_c11_observation_report,
    validate_compiler_emitted_c11_sources,
)
from examples.bounded_compiler_target_equivalence_proof import (
    GPU_GOLDEN_PATH,
    TARGET_EQUIVALENCE_GOLDEN_PATH,
    TARGET_EQUIVALENCE_SCHEMA_PATH,
    BoundedCompilerTargetEquivalenceError,
    _load_report,
    assert_bounded_compiler_target_equivalence_proof,
    build_bounded_compiler_target_equivalence_proof,
    dump_bounded_compiler_target_equivalence_proof,
)

C11_IMAGE_DIGEST = (
    "sha256:e5898ceccf0bcecd486808f9b0e93cdfc74e9f27f00185344b833da2e3c54eed"
)
DOC_PATH = Path("docs/BOUNDED_COMPILER_TARGET_EQUIVALENCE_PROOF.md")
THREAT_MODEL_PATH = Path("docs/BOUNDED_COMPILER_EMITTED_C11_THREAT_MODEL.md")
RFC_PATH = Path("rfcs/0303-bounded-compiler-target-equivalence-proof.md")
WORKFLOW_PATH = Path(".github/workflows/bounded-c11-proof.yml")


def _source_intent() -> dict[str, object]:
    return emission._load_json(emission.C11_SOURCE_INTENT_PATH)


def _workload() -> dict[str, object]:
    return emission._load_json(emission.C11_WORKLOAD_MANIFEST_PATH)


def _image_metadata(image_digest: str = C11_IMAGE_DIGEST) -> dict[str, object]:
    return {
        "Architecture": "amd64",
        "Config": {
            "Cmd": ["--preflight"],
            "Entrypoint": [c11_proof.C11_ENTRYPOINT],
            "Env": [
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            ],
            "Labels": _expected_labels(),
            "User": "10001:10001",
            "WorkingDir": "/run/tuc",
        },
        "Id": image_digest,
        "Os": "linux",
    }


def _build_c11_report() -> dict[str, object]:
    return build_compiler_emitted_c11_observation_report(
        _expected_worker_response("execute"),
        _synthetic_compose_config(),
        _image_metadata(),
    )


def test_exact_source_intent_emits_c11_artifacts_byte_for_byte() -> None:
    artifacts = build_c11_compiler_emission_artifacts(_source_intent(), _workload())

    assert validate_checked_in_c11_compiler_emission() == artifacts
    assert artifacts.generated_header == emission.C11_GENERATED_HEADER_PATH.read_text(
        encoding="utf-8"
    )
    assert artifacts.generated_source == emission.C11_GENERATED_SOURCE_PATH.read_text(
        encoding="utf-8"
    )
    assert artifacts.workload_header == emission.C11_WORKLOAD_HEADER_PATH.read_text(
        encoding="utf-8"
    )
    assert dump_c11_compiler_emission_plan(
        artifacts.plan, _source_intent(), _workload()
    ) == emission.C11_EMISSION_PLAN_PATH.read_text(encoding="utf-8")
    assert artifacts.plan["generated_function_count"] == 2
    assert artifacts.plan["runtime_generated_code"] is False
    assert artifacts.plan["target"] == {
        "architecture": "x86_64",
        "binary_format": "elf64",
        "compiler_contract": "gcc-14.2.0",
        "cuda_dependency": False,
        "execution_model": "bounded_sequential_host_functions",
        "linkage": "static",
        "source_language": "c11",
        "target_profile": "linux-x86_64-static-c11-compiler-emitted",
    }


def test_c11_inputs_are_identical_to_the_accepted_cuda_inputs() -> None:
    gpu_context = Path("docker/gpu-observation")

    assert emission.C11_SOURCE_INTENT_PATH.read_bytes() == (
        gpu_context / "compiler_emitted_source_intent.v0.json"
    ).read_bytes()
    assert emission.C11_WORKLOAD_MANIFEST_PATH.read_bytes() == (
        gpu_context / "compiler_emitted_workload.v0.json"
    ).read_bytes()


def test_c11_emitter_rejects_source_or_workload_drift() -> None:
    source = copy.deepcopy(_source_intent())
    source["name"] = "untrusted_identifier; system('id')"
    with pytest.raises(BoundedCompilerEmissionError, match="digest drift"):
        build_c11_compiler_emission_artifacts(source, _workload())

    workload = copy.deepcopy(_workload())
    inputs = workload["inputs"]
    assert isinstance(inputs, dict)
    a = inputs["a"]
    assert isinstance(a, list)
    first_row = a[0]
    assert isinstance(first_row, list)
    first_row[0] = 1.0e30
    with pytest.raises(BoundedCompilerEmissionError, match="digest drift"):
        build_c11_compiler_emission_artifacts(_source_intent(), workload)


def test_c11_static_surface_is_non_cuda_and_fail_closed() -> None:
    artifacts = validate_compiler_emitted_c11_sources()
    harness = C11_HARNESS_PATH.read_text(encoding="utf-8")
    dockerfile = C11_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert artifacts.generated_source.count("void tuc_") == 2
    assert not any(line.startswith("void tuc_") for line in harness.splitlines())
    assert "FROM scratch" in dockerfile
    assert "-static" in dockerfile
    assert "grep '(NEEDED)'" in dockerfile
    assert "nvidia" not in dockerfile.lower()
    assert "cuda" not in artifacts.generated_source.lower()
    assert "apt-get" not in dockerfile
    assert "curl " not in dockerfile
    assert "wget " not in dockerfile


def test_compose_contract_has_no_device_mount_or_network() -> None:
    normalized = _validate_compose_config(_synthetic_compose_config())

    assert normalized["devices"] == []
    assert normalized["gpus"] is None
    assert normalized["network_mode"] == "none"
    assert normalized["volumes"] == []
    assert normalized["read_only"] is True
    assert normalized["cap_drop"] == ["ALL"]

    changed = copy.deepcopy(_synthetic_compose_config())
    service = changed["services"][c11_proof.C11_SERVICE]  # type: ignore[index]
    service["volumes"] = [".:/workspace"]  # type: ignore[index]
    with pytest.raises(BoundedCompilerEmittedC11ProofError, match="security contract"):
        _validate_compose_config(changed)


def test_image_contract_binds_sources_and_exact_scratch_runtime() -> None:
    assert _validate_image_metadata(_image_metadata()) == {
        "container_image_digest": C11_IMAGE_DIGEST,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }

    changed = _image_metadata()
    labels = changed["Config"]["Labels"]  # type: ignore[index]
    labels["io.tuc.c11-observation.generated-source-digest"] = (  # type: ignore[index]
        "sha256:" + "0" * 64
    )
    with pytest.raises(BoundedCompilerEmittedC11ProofError, match="provenance"):
        _validate_image_metadata(changed)


def test_worker_preflight_is_zero_call_and_execution_is_exactly_two_calls() -> None:
    preflight = _validate_worker_response(
        _expected_worker_response("preflight"), "preflight"
    )
    execution = _validate_worker_response(
        _expected_worker_response("execute"), "execute"
    )

    assert preflight["generated_function_call_count"] == 0
    assert preflight["working_set_bytes"] == 0
    assert execution["generated_function_call_count"] == 2
    assert execution["working_set_bytes"] == 256
    assert execution["device_access"] is False
    assert execution["cuda_dependency"] is False


def test_worker_command_uses_digest_and_exposes_no_device() -> None:
    command = _worker_command("execute", C11_IMAGE_DIGEST)
    rendered = " ".join(command)

    assert C11_IMAGE_DIGEST in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--gpus" not in rendered
    assert "--device" not in rendered
    assert "--volume" not in rendered
    assert c11_proof.C11_IMAGE not in command


def test_worker_response_rejects_extra_fields_and_reinterpreted_execution() -> None:
    response = _expected_worker_response("execute")
    response["cpu_model"] = "should-not-be-public"
    with pytest.raises(BoundedCompilerEmittedC11ProofError, match="key drift"):
        _validate_worker_response(response, "execute")

    response = _expected_worker_response("execute")
    response["device_access"] = True
    with pytest.raises(BoundedCompilerEmittedC11ProofError, match="invariant drift"):
        _validate_worker_response(response, "execute")


def test_bounded_c11_workflow_is_read_only_and_sha_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read\n" in workflow
    assert "pull_request_target" not in workflow
    assert "@v" not in workflow
    assert "secrets." not in workflow
    assert (
        "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd" in workflow
    )
    assert (
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405"
        in workflow
    )
    assert "pip install --require-hashes -r requirements/ci.txt" in workflow
    assert "build --pull compiler-emitted-c11" in workflow
    assert "bounded_compiler_emitted_c11_proof.py --preflight" in workflow
    assert "bounded_compiler_emitted_c11_proof.py --execute" in workflow


def test_c11_report_is_closed_metadata_only_evidence() -> None:
    report = _build_c11_report()
    rendered = dump_compiler_emitted_c11_observation_report(report)
    schema = json.loads(C11_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert assert_compiler_emitted_c11_observation_report(report) == report
    assert schema["additionalProperties"] is False
    assert report["proof"]["status"] == "PASS"  # type: ignore[index]
    assert report["execution"]["dynamic_linking"] is False  # type: ignore[index]
    assert report["execution"]["tuc_native_backend_admitted"] is False  # type: ignore[index]
    assert '"raw_tensor_values":' not in rendered
    assert "generated_compiler_emitted_c11_functions.c" not in rendered


def test_c11_report_rejects_claim_promotion_even_with_recomputed_digest() -> None:
    report = _build_c11_report()
    execution = report["execution"]
    assert isinstance(execution, dict)
    execution["tuc_native_backend_admitted"] = True
    digest_source = dict(report)
    digest_source.pop("report_digest")
    report["report_digest"] = emission._digest_payload(digest_source)

    with pytest.raises(BoundedCompilerEmittedC11ProofError, match="execution invariant"):
        assert_compiler_emitted_c11_observation_report(report)


def test_checked_in_c11_observation_is_valid() -> None:
    rendered = C11_GOLDEN_PATH.read_text(encoding="utf-8")
    report = json.loads(rendered)

    assert dump_compiler_emitted_c11_observation_report(report) == rendered
    assert report["execution"]["generated_function_call_count"] == 2
    assert report["claim_boundary"]["external_reproduction"] == "not_yet_supplied"


def test_compiler_target_equivalence_binds_both_accepted_observations() -> None:
    report = build_bounded_compiler_target_equivalence_proof(
        _load_report(GPU_GOLDEN_PATH),
        _load_report(C11_GOLDEN_PATH),
    )
    rendered = dump_bounded_compiler_target_equivalence_proof(report)
    expected = TARGET_EQUIVALENCE_GOLDEN_PATH.read_text(encoding="utf-8")
    schema = json.loads(TARGET_EQUIVALENCE_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert rendered == expected
    assert schema["additionalProperties"] is False
    assert report["proof"]["status"] == "PASS"  # type: ignore[index]
    assert report["claim_boundary"]["compiler_target_count"] == 2  # type: ignore[index]
    assert report["claim_boundary"]["non_cuda_target_count"] == 1  # type: ignore[index]
    assert (  # type: ignore[index]
        report["claim_boundary"]["universal_compute_claim_proven"] is False
    )
    assert '"raw_tensor_values":' not in rendered


def test_compiler_target_equivalence_rejects_child_provenance_drift() -> None:
    c11 = _load_report(C11_GOLDEN_PATH)
    provenance = c11["provenance"]
    assert isinstance(provenance, dict)
    provenance["source_intent_payload_digest"] = "sha256:" + "0" * 64
    digest_source = dict(c11)
    digest_source.pop("report_digest")
    c11["report_digest"] = emission._digest_payload(digest_source)

    with pytest.raises(BoundedCompilerTargetEquivalenceError, match="observation rejected"):
        build_bounded_compiler_target_equivalence_proof(
            _load_report(GPU_GOLDEN_PATH),
            c11,
        )


def test_checked_in_target_equivalence_is_valid() -> None:
    rendered = TARGET_EQUIVALENCE_GOLDEN_PATH.read_text(encoding="utf-8")
    report = json.loads(rendered)

    assert assert_bounded_compiler_target_equivalence_proof(report) == report
    assert dump_bounded_compiler_target_equivalence_proof(report) == rendered


def test_public_docs_preserve_scope_and_host_privacy() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (DOC_PATH, THREAT_MODEL_PATH, RFC_PATH)
    )

    documented_artifacts = (
        C11_SCHEMA_PATH,
        TARGET_EQUIVALENCE_SCHEMA_PATH,
        C11_GOLDEN_PATH,
        TARGET_EQUIVALENCE_GOLDEN_PATH,
    )
    for path in documented_artifacts:
        assert path.relative_to(c11_proof.REPOSITORY_ROOT).as_posix() in combined
    assert "independent reproduction" in combined
    assert "universal hardware" in combined.lower()
    assert "dev001" not in combined
    assert "dev002" not in combined
    assert "192.168." not in combined
    assert "id_ed25519" not in combined
