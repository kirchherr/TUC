"""Synthetic protocol tests; no worker, source parser or native execution."""

import ast
import copy
import json
from hashlib import sha256

import pytest

from tuc.compiler import bounded_cpu_source as api
from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    SourceToIntentResearchKernelIngressReport,
    source_to_intent_research_kernel_ingress_report_to_dict,
)

SOURCE = b"""import triton
import triton.language as tl
@triton.jit
def project(a, b, y, z):
    p = tl.dot(a, b)
    r = tl.where(p > 0.0, p, 0.0)
    s = tl.sum(p, axis=1)
    tl.store(y, r)
    tl.store(z, s)
"""
SECURITY = {
    "address_space_bytes": 805306368, "capability_effective_hex": "0000000000000000",
    "core_dump_disabled": True, "cpu_period_micros": 100000, "cpu_quota_micros": 100000,
    "cpu_seconds": 4, "empty_working_directory": True, "file_size_bytes": 262144,
    "filesystem_namespace_isolation": True, "gid": 10001, "isolated_python_mode": True,
    "kernel_network_isolation": True, "memory_limit_bytes": 1073741824,
    "network_route_count": 0, "no_new_privileges": True, "open_files": 32,
    "pids_limit": 32, "repository_bind_mount": False, "root_filesystem_read_only": True,
    "seccomp_mode": 2, "shell": False, "tmpfs_nodev": True, "tmpfs_noexec": True,
    "tmpfs_nosuid": True, "uid": 10001,
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return "sha256:" + sha256(value).hexdigest()


def signature():
    return {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "projection",
            "kernel_name": "project", "tensor_shapes": {
                "a": [2, 3], "b": [3, 2], "y": [2, 2], "z": [2]}}


def graph():
    return {
        "schema_version": "source_intent.v0", "name": "projection",
        "tensors": [
            {"name": name, "shape": shape, "dtype": "float32"}
            for name, shape in (("a", [2, 3]), ("b", [3, 2]), ("p", [2, 2]),
                                ("r", [2, 2]), ("s", [2]))
        ],
        "operations": [
            {"name": "p", "family": "matmul", "inputs": ["a", "b"],
             "outputs": ["p"], "hints": {}},
            {"name": "r", "family": "elementwise", "inputs": ["p"], "outputs": ["r"],
             "hints": {}, "attributes": {"elementwise_kind": "relu"}},
            {"name": "s", "family": "reduction", "inputs": ["p"], "outputs": ["s"],
             "hints": {}, "attributes": {"axis": 1}},
        ],
        "returns": [
            {"public_name": "y", "tensor_name": "r", "required": True},
            {"public_name": "z", "tensor_name": "s", "required": True},
        ],
    }


def request(source=SOURCE, declared=None):
    chosen = signature() if declared is None else declared
    return api.prepare_source_request(source, encoded(chosen))


def response(req=None, payload=None):
    """Build explicitly synthetic worker data, never an observed execution fixture."""
    req = request() if req is None else req
    asked = json.loads(req)
    source = asked["payload"]["module_source"]
    payload = graph() if payload is None else payload
    report = SourceToIntentResearchKernelIngressReport(
        source_name=asked["payload"]["source_name"],
        kernel_name=asked["payload"]["kernel_name"], module_digest=digest(source.encode()),
        extracted_kernel_digest="sha256:" + "1" * 64,
        parser_report_digest="sha256:" + "2" * 64,
        source_intent_digest=digest(encoded(payload)), module_bytes=len(source.encode()),
        module_line_count=len(source.splitlines()), module_ast_node_count=91, module_ast_depth=9,
        import_count=2, top_level_function_count=1,
        operation_families=tuple(sorted({op["family"] for op in payload["operations"]})),
        tensor_count=len(payload["tensors"]), operation_count=len(payload["operations"]),
        return_count=len(payload["returns"]),
    )
    return {"protocol": "tuc.oci_source_ingestion_worker.v0",
            "request_digest": asked["request_digest"], "status": "accepted",
            "security": dict(SECURITY), "source_intent_payload": payload,
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(report)}


def rejected(call, reason):
    with pytest.raises(api.BoundedCPUSourceError) as exc:
        call()
    assert exc.value.reason == reason
    assert str(exc.value) == reason
    assert exc.value.__cause__ is None


def test_request_matches_existing_worker_protocol_and_digest():
    actual = request()
    payload = {"module_source": SOURCE.decode(), "source_name": "projection",
               "kernel_name": "project", "tensor_shapes": signature()["tensor_shapes"]}
    assert actual == encoded({"protocol": "tuc.oci_source_ingestion_worker.v0",
                              "payload": payload, "request_digest": digest(encoded(payload))})
    assert len(actual) <= api.MAX_REQUEST_BYTES


def test_signature_key_order_does_not_change_request():
    declared = signature()
    declared["tensor_shapes"] = dict(reversed(list(declared["tensor_shapes"].items())))
    assert api.prepare_source_request(SOURCE, json.dumps(declared, indent=4).encode()) == request()


def test_response_returns_canonical_graph_with_original_public_order():
    actual = api.decode_source_response(request(), encoded(response()))
    assert actual == encoded(graph()) + b"\n"
    assert actual.endswith(b"\n") and not actual.endswith(b"\n\n")
    module = source_intent_from_json(actual)
    assert [r.public_name for r in module.returns] == ["y", "z"]


def test_no_host_ast_or_research_parser_call(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source parsing must occur only in the OCI worker")

    import tuc.frontend.source_to_intent_research_kernel_ingress as ingress
    import tuc.frontend.source_to_intent_research_parser as parser

    monkeypatch.setattr(ast, "parse", forbidden)
    monkeypatch.setattr(ingress, "ingest_triton_module_source_to_source_intent", forbidden)
    monkeypatch.setattr(parser, "parse_triton_source_to_source_intent", forbidden)
    req = request()
    assert api.decode_source_response(req, encoded(response(req))) == encoded(graph()) + b"\n"
    # Invalid syntax is still inert data at the host boundary, not parsed here.
    assert json.loads(request(b"this is not python (["))["payload"]["module_source"]


@pytest.mark.parametrize("data", [b"", b"x" * 65537, b"\xff", b"\xed\xa0\x80",
                                  b"\xef\xbb\xbfx", b"x\x00y", b"\n" * 2049,
                                  "source", bytearray(b"source"), None, 1],
                         ids=lambda value: type(value).__name__)
def test_source_rejections_are_closed(data):
    rejected(lambda: api.prepare_source_request(data, encoded(signature())), "source_rejected")


def test_source_bytes_and_line_boundaries():
    assert request(b"#" + b"a" * 65535)
    assert request(b"\n" * 2048)
    assert request("# \u00e9\n".encode())
    # A legal byte count can still overflow the worker request after JSON escaping.
    rejected(lambda: request(b"\x01" * 65536), "source_rejected")


@pytest.mark.parametrize("data", [
    b"", b" " * 16385, b"\xff", b"\xef\xbb\xbf{}", b'{"x":"\\ud800"}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e309}', b'{"x":1e-999}',
    b'{"x":' + b"1" * 65 + b"}", b'"x"', b"null", b"[]", b"{} garbage",
    b"[" * 7 + b"0" + b"]" * 7, b"[" + b"0," * 1100 + b"0]",
    b'{"x":0,"x":1}', b'{"x":0,"\\u0078":1}',
    b'{"x":{"y":0,"y":1}}', "{}", bytearray(b"{}"), None,
], ids=lambda value: type(value).__name__)
def test_signature_json_is_strict_and_bounded(data):
    rejected(lambda: api.prepare_source_request(SOURCE, data), "signature_rejected")


@pytest.mark.parametrize("key", tuple(signature()))
def test_signature_requires_exact_keys(key):
    declared = signature()
    del declared[key]
    rejected(lambda: request(declared=declared), "signature_rejected")


@pytest.mark.parametrize("key,value", [
    ("extra", 0), ("schema_version", "source_intent.v0"), ("schema_version", True),
    ("source_name", "a/b"), ("kernel_name", "../kernel"), ("source_name", "a" * 65),
    ("kernel_name", "\u00e9"), ("source_name", "1foo"), ("source_name", ""),
    ("kernel_name", []), ("tensor_shapes", []), ("tensor_shapes", {}),
    ("tensor_shapes", {"a": [1], **{f"x{i}": [1] for i in range(24)}}),
])
def test_signature_fields_reject(key, value):
    declared = signature()
    declared[key] = value
    rejected(lambda: request(declared=declared), "signature_rejected")


@pytest.mark.parametrize("shape", [[], [1, 2, 3], 2, "x", None, {},
                                   [0], [-1], [65], [True], [1.0], ["2"], [None],
                                   [2, {}], [10**50]])
def test_signature_shapes_reject(shape):
    declared = signature()
    declared["tensor_shapes"]["a"] = shape
    rejected(lambda: request(declared=declared), "signature_rejected")


@pytest.mark.parametrize("name", ["", "x" * 65, "\u03b1", "a/b", "2x", "x\n"])
def test_signature_tensor_names_reject(name):
    declared = signature()
    declared["tensor_shapes"][name] = [1]
    rejected(lambda: request(declared=declared), "signature_rejected")


@pytest.mark.parametrize("data", [
    b"", b" " * 262145, b"\xff", b"\xef\xbb\xbf{}", b'{"x":"\\udfff"}',
    b'{"x":NaN}', b'{"x":-Infinity}', b'{"x":1e309}', b'{"x":1e-999}',
    b'{"x":' + b"2" * 65 + b"}", b"[]", b"true", b"{}{}",
    b"[" * 17 + b"0" + b"]" * 17, b"[" + b"0," * 9000 + b"0]",
    b'{"x":0,"\\u0078":1}', b'{"x":{"y":0,"y":1}}', "{}", bytearray(b"{}"), None,
], ids=lambda value: type(value).__name__)
def test_response_json_is_strict_and_bounded(data):
    rejected(lambda: api.decode_source_response(request(), data), "protocol_rejected")


@pytest.mark.parametrize("key", tuple(response()))
def test_response_requires_exact_keys(key):
    wire = response()
    del wire[key]
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("key,value", [
    ("extra", True), ("protocol", "tuc.isolated_source_ingestion_worker.v0"),
    ("status", True), ("status", "success"), ("request_digest", "sha256:" + "0" * 64),
    ("security", []), ("security", {}),
])
def test_response_envelope_rejects(key, value):
    wire = response()
    wire[key] = value
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("key", tuple(SECURITY))
@pytest.mark.parametrize("change", ["missing", "different", "wrong_type"])
def test_every_security_fact_is_exact(key, change):
    wire = response()
    expected = wire["security"][key]
    if change == "missing":
        del wire["security"][key]
    elif change == "different":
        wire["security"][key] = (not expected if type(expected) is bool else
                                 expected + 1 if type(expected) is int else "1" * 16)
    else:
        wire["security"][key] = (int(expected) if type(expected) is bool else
                                 float(expected) if type(expected) is int else [])
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


def test_extra_security_fact_rejects():
    wire = response()
    wire["security"]["approved"] = True
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("key", tuple(response()["ingress_report"]))
def test_report_fields_are_required_and_source_bound(key):
    wire = response()
    del wire["ingress_report"][key]
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("key", [key for key, value in response()["ingress_report"].items()
                                  if type(value) is int])
@pytest.mark.parametrize("value", [True, 0.0, "1", None, [], {}, -1, 10**50])
def test_report_numeric_fields_require_bounded_exact_integers(key, value):
    wire = response()
    wire["ingress_report"][key] = value
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("key,value", [
    ("module_ast_node_count", 8193), ("module_ast_depth", 65),
    ("module_ast_node_count", 0), ("module_ast_depth", 0), ("tensor_count", 4),
    ("operation_count", 2), ("return_count", 1), ("import_count", 1),
    ("top_level_function_count", 2), ("source_name", "different"),
    ("kernel_name", "different"), ("module_digest", "sha256:" + "0" * 64),
    ("source_intent_digest", "sha256:" + "0" * 64), ("module_bytes", 1),
    ("module_line_count", 1), ("extracted_kernel_digest", "sha256:" + "A" * 64),
    ("parser_report_digest", "arbitrary"), ("operation_families", ["matmul"]),
    ("allowed_import_aliases", ["triton", "tl"]), ("blocked_claims", []),
    ("default_parser_status", "accepted"), ("raw_source_policy", SOURCE.decode()),
    ("extra", True),
])
def test_report_binding_and_policy_rejects(key, value):
    wire = response()
    wire["ingress_report"][key] = value
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("reason", ["source_rejected", "protocol_rejected"])
def test_exact_worker_rejection_has_closed_reason(reason):
    req = request()
    wire = {"protocol": api.WORKER_PROTOCOL, "request_digest": json.loads(req)["request_digest"],
            "status": "rejected", "reason_code": reason}
    rejected(lambda: api.decode_source_response(req, encoded(wire)), reason)
    wire["source"] = SOURCE.decode()
    rejected(lambda: api.decode_source_response(req, encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("reason", [True, None, [], {}, "graph_rejected", "signature_rejected",
                                    "source path /secret failed"])
def test_rejection_reason_cannot_leak_or_forge_parent_results(reason):
    wire = {"protocol": api.WORKER_PROTOCOL,
            "request_digest": json.loads(request())["request_digest"],
            "status": "rejected", "reason_code": reason}
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "protocol_rejected")


@pytest.mark.parametrize("mutate", [
    lambda g: g.update(name="other"),
    lambda g: g["operations"][0].update(name="renamed"),
    lambda g: g["operations"][0].update(hints={"prefer_sparsity": True}),
    lambda g: g["operations"][0].pop("hints"),
    lambda g: g["tensors"][0].pop("dtype"),
    lambda g: g["returns"][0].pop("required"),
    lambda g: g["operations"][1]["attributes"].update(elementwise_kind="identity"),
    lambda g: g["operations"][1].update(family="softmax", attributes={"axis": 1}),
    lambda g: g["operations"][2]["attributes"].update(axis=0),
    lambda g: g["operations"][2]["attributes"].update(axis=True),
    lambda g: g["returns"][0].update(tensor_name="p"),
    lambda g: g["returns"].pop(),
    lambda g: g["returns"][0].update(public_name="different"),
    lambda g: g["returns"][0].update(required=False),
    lambda g: g["returns"][0].update(required=1),
    lambda g: g["operations"].reverse(),
    lambda g: g["operations"].append(copy.deepcopy(g["operations"][0])),
    lambda g: g["tensors"][0].update(shape=[64, 64]),
])
def test_graph_contract_rejects_before_publication(mutate):
    changed = graph()
    mutate(changed)
    wire = response()
    wire["source_intent_payload"] = changed
    rejected(lambda: api.decode_source_response(request(), encoded(wire)), "graph_rejected")


@pytest.mark.parametrize("name,shape", [("a", [3, 3]), ("y", [1, 2]), ("z", [1]),
                                       ("extra", [1]), ("p", [2, 2])])
def test_graph_is_bound_to_original_signature_inputs_and_public_shapes(name, shape):
    declared = signature()
    declared["tensor_shapes"][name] = shape
    req = request(declared=declared)
    rejected(lambda: api.decode_source_response(req, encoded(response(req))), "graph_rejected")


def test_signature_roles_do_not_alias():
    declared = signature()
    del declared["tensor_shapes"]["y"]
    changed = graph()
    changed["returns"][0]["public_name"] = "a"
    req = request(declared=declared)
    rejected(lambda: api.decode_source_response(req, encoded(response(req, changed))),
             "graph_rejected")


@pytest.mark.parametrize("change", ["protocol", "digest", "source", "signature", "extra",
                                    "whitespace", "duplicate", "type"])
def test_decoder_revalidates_the_original_request(change):
    req = request()
    wire = response(req)
    modified = json.loads(req)
    if change == "protocol":
        modified["protocol"] = "tuc.isolated_source_ingestion_worker.v0"
    elif change == "digest":
        modified["request_digest"] = "sha256:" + "0" * 64
    elif change == "source":
        modified["payload"]["module_source"] += "# changed\n"
    elif change == "signature":
        modified["payload"]["tensor_shapes"]["a"] = [1, 1]
    elif change == "extra":
        modified["payload"]["extra"] = True
    req = encoded(modified)
    if change == "whitespace":
        req += b"\n"
    elif change == "duplicate":
        req = req[:-1] + b',"protocol":"' + api.WORKER_PROTOCOL.encode() + b'"}'
    elif change == "type":
        req = bytearray(req)
    rejected(lambda: api.decode_source_response(req, encoded(wire)), "protocol_rejected")


def test_different_valid_request_cannot_reuse_response():
    req = request(SOURCE + b"# different request\n")
    rejected(lambda: api.decode_source_response(req, encoded(response())), "protocol_rejected")


def test_exact_byte_boundary_does_not_invoke_subclass_hooks():
    class HostileBytes(bytes):
        def decode(self, *args, **kwargs):
            raise AssertionError("untrusted method called")

        def __len__(self):
            raise AssertionError("untrusted length called")

    rejected(lambda: request(HostileBytes(SOURCE)), "source_rejected")
    rejected(lambda: api.prepare_source_request(SOURCE, HostileBytes(encoded(signature()))),
             "signature_rejected")
    rejected(lambda: api.decode_source_response(HostileBytes(request()), encoded(response())),
             "protocol_rejected")
    rejected(lambda: api.decode_source_response(request(), HostileBytes(encoded(response()))),
             "protocol_rejected")


@pytest.mark.parametrize("reason", [None, True, "raw error", "", "source_rejected\n"])
def test_error_reason_is_closed(reason):
    with pytest.raises(ValueError, match="invalid bounded CPU source diagnostic"):
        api.BoundedCPUSourceError(reason)


def test_error_reason_property_is_read_only():
    error = api.BoundedCPUSourceError("graph_rejected")
    with pytest.raises(AttributeError):
        error.reason = "source_rejected"
