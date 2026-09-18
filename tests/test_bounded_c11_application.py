"""Pure RFC 0324 protocol tests; synthetic responses are not execution evidence."""

import json
import math
import struct
from dataclasses import fields, replace
from hashlib import sha256

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_c11_application_codegen import emit_application
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_c11_application as api
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def source(name="application_test"):
    return SourceIntentModule(
        name,
        tuple(SourceIntentTensor(name, shape) for name, shape in (
            ("a", (1, 2)), ("b", (2, 1)), ("p", (1, 1)), ("positive", (1, 1)), ("raw", (1,)),
        )),
        (
            SourceIntentOperation("dot", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation("activate", "elementwise", ("p",), ("positive",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("reduce", "reduction", ("p",), ("raw",), attributes={"axis": 1}),
        ), returns=(SourceIntentReturn("z_positive", "positive"),
                    SourceIntentReturn("a_raw", "raw")),
    )


def bindings():
    return (BoundedBackendBinding(BackendCapability(
        "cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                          OperationKind.REDUCTION}),
        memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11),)


@pytest.fixture
def compiled():
    module, backends = source(), bindings()
    return module, backends, api.prepare_bounded_c11_application(module, backends)


def inputs():
    return {"a": (2.0, -3.0), "b": (4.0, 5.0)}


def request(compiled):
    return api.encode_bounded_c11_inputs(*compiled, inputs())


def synthetic_response(compiled, *, values=(0.0, -7.0), status=0):
    """A labelled host-side protocol fixture, never an observed native result."""
    frame = request(compiled)
    return b"TUCOUT01" + frame[8:72] + struct.pack("<I", status) + (
        struct.pack("<" + "f" * len(values), *values) if status == 0 else b"")


def corrupt(value, **changes):
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(value, field.name)))
    return result


def test_preparation_is_deterministic_inert_and_has_closed_build_context(compiled):
    module, backends, application = compiled
    api.validate_bounded_c11_application(*compiled)
    assert application == api.prepare_bounded_c11_application(module, backends)
    files = application.files()
    assert set(files) == {"entrypoint.c", "entrypoint.h", "entrypoint.json", "application.c",
                          "application.h", "application.json", "Dockerfile",
                          "Dockerfile.dockerignore", "build.sh"}
    files.clear()
    assert len(application.files()) == 9
    manifest = json.loads(application.application_json)
    assert manifest["request_bytes"] == 88
    assert manifest["response_bytes"] == 84
    assert manifest["error_response_bytes"] == 76
    assert manifest["native_execution_observed"] is False
    assert manifest["normal_runtime_admission"] is False
    assert manifest["cuda_execution_observed"] is False
    assert manifest["latency_ns"] is manifest["energy_pj"] is None
    assert manifest["declared_storage_budget_bytes"] <= 1048576
    assert manifest["protocol"]["digests_are_authentication"] is False
    for filename, digest in manifest["source_digests"].items():
        assert sha256(application.files()[filename].encode()).hexdigest() == digest


def test_program_digest_reconstructs_exact_zero_binding_template(compiled):
    application = compiled[2]
    files = application.files()
    program = application.program_digest
    files["application.h"] = files["application.h"].replace(program, "0" * 64)
    encoded = ", ".join(f"0x{program[i:i + 2]}U" for i in range(0, 64, 2))
    files["application.c"] = files["application.c"].replace(encoded, ", ".join(["0x00U"] * 32))
    manifest = json.loads(files["application.json"])
    manifest["program_digest"] = "0" * 64
    manifest["source_digests"] = {
        name: sha256(text.encode()).hexdigest() for name, text in files.items()
        if name != "application.json"
    }
    files["application.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n"
    assert sha256(canonical.encode()).hexdigest() == program


def test_program_identity_changes_with_source_and_fixed_recipe(compiled, monkeypatch):
    original = compiled[2].program_digest
    changed = api.prepare_bounded_c11_application(source("changed"), bindings())
    assert changed.program_digest != original
    monkeypatch.setattr(api, "BUILD_SH", api.BUILD_SH + "# changed fixed recipe\n")
    assert api.prepare_bounded_c11_application(*compiled[:2]).program_digest != original
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled)


def test_request_is_exact_little_endian_and_bound_to_public_input_order(compiled):
    encoded = request(compiled)
    assert type(encoded) is bytes
    assert encoded[:8] == b"TUCIN001"
    assert encoded[8:40] == bytes.fromhex(compiled[2].program_digest)
    assert encoded[72:] == struct.pack("<ffff", 2.0, -3.0, 4.0, 5.0)
    assert encoded[40:72] == sha256(encoded[8:40] + encoded[72:]).digest()
    reverse = {"b": (4.0, 5.0), "a": (2.0, -3.0)}
    assert api.encode_bounded_c11_inputs(*compiled, reverse) == encoded


def test_synthetic_success_decodes_public_aliases_in_declared_order(compiled):
    result = api.decode_bounded_c11_outputs(*compiled, request(compiled),
                                           synthetic_response(compiled), 0)
    assert list(result) == ["z_positive", "a_raw"]
    assert result == {"z_positive": (0.0,), "a_raw": (-7.0,)}
    assert all(type(values) is tuple for values in result.values())


def test_fp32_rounding_and_signed_zero_are_preserved(compiled):
    values = {"a": (1.0 / 7.0, -0.0), "b": (0.0, -1.0)}
    encoded = api.encode_bounded_c11_inputs(*compiled, values)
    actual = struct.unpack("<ffff", encoded[72:])
    assert actual[0] == struct.unpack("<f", struct.pack("<f", 1.0 / 7.0))[0]
    assert actual[0] != values["a"][0]
    assert math.copysign(1.0, actual[1]) == -1.0
    response = b"TUCOUT01" + encoded[8:72] + struct.pack("<Iff", 0, -0.0, 0.0)
    result = api.decode_bounded_c11_outputs(*compiled, encoded, response, 0)
    assert math.copysign(1.0, result["z_positive"][0]) == -1.0


class Hook:
    def __eq__(self, other):
        raise AssertionError("caller equality")

    def __iter__(self):
        raise AssertionError("caller iteration")


class HookFloat(float):
    def __float__(self):
        raise AssertionError("caller float conversion")


class HookDict(dict):
    def __iter__(self):
        raise AssertionError("caller mapping iteration")


class HookTuple(tuple):
    def __iter__(self):
        raise AssertionError("caller tuple iteration")


class HookBytes(bytes):
    def __len__(self):
        raise AssertionError("caller bytes length")


@pytest.mark.parametrize("bad", (None, False, 0, 2 ** 10000, Hook(), HookFloat(1.0),
                                float("nan"), float("inf"), -float("inf"),
                                2.0 ** -149, -(2.0 ** -149), 2.0 ** -200,
                                -(2.0 ** -200), 2.0 ** 128), ids=map(str, range(14)))
def test_invalid_python_scalar_rejected_before_conversion(compiled, bad):
    values = inputs()
    values["a"] = (bad, 1.0)
    with pytest.raises(ValueError):
        api.encode_bounded_c11_inputs(*compiled, values)


@pytest.mark.parametrize("bad", (None, (), [], Hook(), HookDict(), {},
                                {"a": (1.0, 2.0)}, {"x": (1.0, 2.0), "b": (1.0, 2.0)},
                                {"a": [1.0, 2.0], "b": (1.0, 2.0)},
                                {"a": HookTuple((1.0, 2.0)), "b": (1.0, 2.0)},
                                {"a": (1.0,), "b": (1.0, 2.0)},
                                {"a": (1.0,) * 10000, "b": (1.0, 2.0)}),
                         ids=map(str, range(12)))
def test_input_container_names_counts_and_types_rejected(compiled, bad):
    with pytest.raises(ValueError):
        api.encode_bounded_c11_inputs(*compiled, bad)


@pytest.mark.parametrize("status", (1, 2, 3, 4, 0xffffffff))
@pytest.mark.parametrize("exit_code", (0, 1, 2, -1, 3, True, 0.0, None, Hook()))
def test_no_error_status_or_exit_mismatch_can_be_decoded(compiled, status, exit_code):
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, request(compiled),
                                       synthetic_response(compiled, status=status), exit_code)


@pytest.mark.parametrize("exit_code", (1, 2, True, False, 0.0, "0", None, -9, Hook()))
def test_success_response_requires_exact_zero_exit(compiled, exit_code):
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, request(compiled),
                                       synthetic_response(compiled), exit_code)


@pytest.mark.parametrize("status", (1, 2, 3))
def test_checked_native_error_is_distinct_only_after_full_protocol_validation(compiled, status):
    response = synthetic_response(compiled, status=status)
    with pytest.raises(api.BoundedC11ApplicationExecutionError) as caught:
        api.decode_bounded_c11_outputs(*compiled, request(compiled), response, 1)
    assert caught.value.status == status
    with pytest.raises(AttributeError):
        caught.value.status = 0
    with pytest.raises(AttributeError):
        caught.value._status = 0
    for bad_response, code in ((response, 0), (response + b"\x00", 1),
                               (b"x" + response[1:], 1)):
        with pytest.raises(ValueError) as malformed:
            api.decode_bounded_c11_outputs(*compiled, request(compiled), bad_response, code)
        assert type(malformed.value) is ValueError


@pytest.mark.parametrize("position", (0, 7, 8, 20, 39, 40, 55, 71, 72, 75))
def test_response_header_status_and_bindings_reject_mutation(compiled, position):
    response = bytearray(synthetic_response(compiled))
    response[position] ^= 1
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, request(compiled), bytes(response), 0)


@pytest.mark.parametrize("position", (0, 7, 8, 39, 40, 71, 72, 80, 87))
def test_supplied_request_must_still_match_its_digest(compiled, position):
    frame = bytearray(request(compiled))
    frame[position] ^= 1
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, bytes(frame), synthetic_response(compiled), 0)


def test_response_cannot_be_replayed_for_changed_request_or_graph(compiled):
    altered = inputs()
    altered["a"] = (3.0, 4.0)
    changed = api.encode_bounded_c11_inputs(*compiled, altered)
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, changed, synthetic_response(compiled), 0)
    other = source("other")
    application = api.prepare_bounded_c11_application(other, compiled[1])
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(other, compiled[1], application,
                                       request(compiled), synthetic_response(compiled), 0)


@pytest.mark.parametrize("bits", (1, 0x80000001, 0x007fffff, 0x7f800000, 0xff800000,
                                 0x7fc00001, 0x7f800001))
def test_output_and_consistently_hashed_request_reject_exceptional_fp32_bits(compiled, bits):
    response = bytearray(synthetic_response(compiled))
    response[76:80] = struct.pack("<I", bits)
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, request(compiled), bytes(response), 0)
    frame = bytearray(request(compiled))
    frame[72:76] = struct.pack("<I", bits)
    frame[40:72] = sha256(frame[8:40] + frame[72:]).digest()
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, bytes(frame), synthetic_response(compiled), 0)


@pytest.mark.parametrize("kind", ("request", "response"))
@pytest.mark.parametrize("bad", (None, False, [], bytearray(), memoryview(b""), Hook(),
                                HookBytes(b""), b"", b"x" * (api.MAX_FRAME_BYTES + 1)),
                         ids=map(str, range(9)))
def test_frames_are_exact_bytes_and_bounded_before_use(compiled, kind, bad):
    frame, response = request(compiled), synthetic_response(compiled)
    if kind == "request":
        frame = bad
    else:
        response = bad
    with pytest.raises(ValueError):
        api.decode_bounded_c11_outputs(*compiled, frame, response, 0)


def test_every_truncation_and_extra_byte_rejected(compiled):
    frame, response = request(compiled), synthetic_response(compiled)
    for length in range(len(frame)):
        with pytest.raises(ValueError):
            api.decode_bounded_c11_outputs(*compiled, frame[:length], response, 0)
    for length in range(len(response)):
        with pytest.raises(ValueError):
            api.decode_bounded_c11_outputs(*compiled, frame, response[:length], 0)
    for suffix in (b"\x00", b"\xff", b"\x00" * 10000):
        with pytest.raises(ValueError):
            api.decode_bounded_c11_outputs(*compiled, frame + suffix, response, 0)
        with pytest.raises(ValueError):
            api.decode_bounded_c11_outputs(*compiled, frame, response + suffix, 0)


@pytest.mark.parametrize("field", ("application_c", "application_h", "application_json",
                                  "dockerfile", "dockerignore", "build_sh", "program_digest"))
def test_all_application_fields_revalidated_before_input_or_response_use(compiled, field):
    application = corrupt(compiled[2], **{field: getattr(compiled[2], field) + " "})
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled[:2], application)
    with pytest.raises(ValueError):
        api.encode_bounded_c11_inputs(*compiled[:2], application, inputs())


@pytest.mark.parametrize("bad", (None, Hook(), [], "\ud800", "x" * (api.MAX_APPLICATION_BYTES + 1)),
                         ids=map(str, range(5)))
def test_forged_application_text_is_bounded_exact_data(compiled, bad):
    application = corrupt(compiled[2], application_c=bad)
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled[:2], application)


def test_nested_entrypoint_symbol_and_shadowed_methods_reject(compiled):
    application = compiled[2]
    wrong = corrupt(application.entrypoint, entrypoint_symbol="tuc_c11_" + "0" * 64 + "_run")
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled[:2], corrupt(application, entrypoint=wrong))
    wrong = corrupt(application.entrypoint)
    object.__setattr__(wrong, "files", Hook())
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled[:2], corrupt(application, entrypoint=wrong))
    wrong = corrupt(application)
    object.__setattr__(wrong, "files", Hook())
    with pytest.raises(ValueError):
        api.validate_bounded_c11_application(*compiled[:2], wrong)


def test_selected_gpu_cannot_prepare_an_application():
    host = bindings()[0]
    gpu = BoundedBackendBinding(replace(host.capability, memory_domain=MemoryDomainKind.UNKNOWN),
                                DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError):
        api.prepare_bounded_c11_application(source(), (gpu,))


def test_fixed_native_parser_has_no_untrusted_extents_and_checks_eof_first(compiled):
    application = compiled[2]
    text = application.application_c
    process = text.split("int tuc_application_process", 1)[1].split("#ifndef", 1)[0]
    assert process.index("request_size != TUC_APPLICATION_REQUEST_BYTES") < process.index("memcmp")
    assert process.index("memcmp(request + 8U, tuc_program") < process.index("tuc_load_u32")
    assert (process.index(application.entrypoint.entrypoint_symbol) <
            process.index("memcpy(response"))
    assert "*response_size = 0U;" in process
    assert "malloc(" not in text
    assert "calloc(" not in text
    main = text.split("int main(", 1)[1]
    assert "alarm(5U)" in main
    assert "TUC_APPLICATION_REQUEST_BYTES + 1U" in main
    assert main.index("!feof(stdin)") < main.index("tuc_application_process")
    assert "fwrite(response, 1U, response_size, stdout) != response_size" in main
    assert "fflush(stdout) != 0" in main
    assert "TUC_APPLICATION_NO_MAIN" in text
    assert "TUC_APPLICATION_REQUEST_BYTES 88U" in application.application_h
    assert "TUC_APPLICATION_RESPONSE_BYTES 84U" in application.application_h


def test_recipe_builds_only_fixed_static_and_sanitized_application(compiled):
    application = compiled[2]
    assert application.build_sh.count("-frounding-math") == 2
    assert application.build_sh.count("-ffp-contract=off") == 2
    assert application.build_sh.count("-fno-fast-math") == 2
    assert "-fsanitize=address,undefined" in application.build_sh
    assert "-static" in application.build_sh
    assert "RUN --network=none sh build.sh" in application.dockerfile
    assert "FROM scratch AS static" in application.dockerfile
    assert "USER 10001:10001" in application.dockerfile
    assert "application.json" not in application.dockerignore


@pytest.mark.parametrize("elements", (None, [], (), (True,), (0,), (4097,), (Hook(),),
                                     (1,) * 25, (4096,) * 24))
def test_private_emitter_rejects_nondata_and_unbounded_extents(elements):
    with pytest.raises(ValueError):
        emit_application("tuc_c11_" + "a" * 64 + "_run", elements, (1,), "b" * 64)


@pytest.mark.parametrize("symbol,digest", ((Hook(), "a" * 64), ("bad", "a" * 64),
                                          ("tuc_c11_" + "a" * 64 + "_run", "A" * 64),
                                          ("tuc_c11_" + "a" * 64 + "_run", Hook())))
def test_private_emitter_cannot_accept_arbitrary_source_text(symbol, digest):
    with pytest.raises(ValueError):
        emit_application(symbol, (1,), (1,), digest)
