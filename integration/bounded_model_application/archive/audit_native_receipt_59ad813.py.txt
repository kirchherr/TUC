"""Standard-library-only audit of fixed observed protocol/numerical records.

This verifier imports neither TUC nor the execution consumer. It does not
execute native code. A self-consistent record alone is not independent
organizational reproduction or authenticated execution provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

MAX_BYTES = 128 * 1024


def encoded(value: object, *, newline: bool = True) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("ascii") + (b"\n" if newline else b"")


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def read_record(data: bytes):
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("record size")
    text = data.decode("ascii")
    depth, quoted, escape = 0, False, False
    for char in text:
        if quoted:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 12:
                raise ValueError("record nesting")
        elif char in "]}":
            depth -= 1

    def integer(value):
        if len(value) > 8:
            raise ValueError("integer size")
        return int(value)

    def forbidden(value):
        raise ValueError("unexpected number")

    return json.loads(
        text,
        object_pairs_hook=pairs,
        parse_int=integer,
        parse_float=forbidden,
        parse_constant=forbidden,
    )


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def bits(values):
    return b"".join(struct.pack("<f", value) for value in values).hex()


def fixed_graph():
    names = ("x", "w", "p", "y", "r")
    return {
        "schema_version": "source_intent.v0",
        "name": "portable_native_observation",
        "tensors": [
            {"name": name, "shape": [2] if name == "r" else [2, 2], "dtype": "float32"}
            for name in names
        ],
        "operations": [
            {
                "name": "projection",
                "family": "matmul",
                "inputs": ["x", "w"],
                "outputs": ["p"],
                "attributes": {},
                "hints": {},
            },
            {
                "name": "activation",
                "family": "elementwise",
                "inputs": ["p"],
                "outputs": ["y"],
                "attributes": {"elementwise_kind": "relu"},
                "hints": {},
            },
            {
                "name": "rows",
                "family": "reduction",
                "inputs": ["p"],
                "outputs": ["r"],
                "attributes": {"axis": 1},
                "hints": {},
            },
        ],
        "returns": [
            {"public_name": public, "tensor_name": tensor, "required": True}
            for public, tensor in (("rows", "r"), ("scores", "y"))
        ],
    }


def reference(x, weight):
    w = (weight, -1.0, 1.0, 3.0)
    raw = []
    for row in range(2):
        for col in range(2):
            total = 0.0
            for k in range(2):
                total = f32(total + f32(x[row * 2 + k] * w[k * 2 + col]))
            raw.append(total)
    scores = [v if v >= 0.0 else 0.0 for v in raw]
    rows = [f32(f32(0.0 + raw[i * 2]) + raw[i * 2 + 1]) for i in range(2)]
    return raw, rows, scores


def audit(data: bytes):
    try:
        record = read_record(data)
        expected_keys = {
            "schema_version",
            "status",
            "native_execution_observed",
            "successful_runs",
            "cases",
            "rejections",
            "workspaces_clean",
        }
        if type(record) is not dict or set(record) != expected_keys:
            raise ValueError("record fields")
        if (
            record["schema_version"] != "tuc.bounded_model_application_native.v0"
            or record["status"] != "PASS"
            or record["native_execution_observed"] is not True
            or type(record["successful_runs"]) is not int
            or record["successful_runs"] != 3
            or record["workspaces_clean"] is not True
            or len(record["cases"]) != 3
        ):
            raise ValueError("record contract")
        models, bundles, programs, requests, protocol_requests = [], [], [], [], []
        receipt_keys = {
            "contract",
            "bundle_digest",
            "request_digest",
            "model_digest",
            "model_compilation_digest",
            "backend_bindings_digest",
            "program_digest",
            "protocol_request_digest",
            "response_sha256",
            "outputs",
            "protocol_validated",
            "native_execution_observed",
            "result_digest",
        }
        request_keys = {
            "contract",
            "bundle_digest",
            "model_digest",
            "model_compilation_digest",
            "backend_bindings_digest",
            "inputs",
            "request_digest",
        }
        for case, name, weight, x in zip(
            record["cases"],
            ("base", "variable", "parameter"),
            (2.0, 2.0, 4.0),
            ((1.0, -0.0, 3.0, 4.0), (-2.0, 1.0, 0.0, -0.0), (1.0, -0.0, 3.0, 4.0)),
            strict=True,
        ):
            if set(case) != {"name", "request", "receipt"} or case["name"] != name:
                raise ValueError("case")
            request, receipt = case["request"], case["receipt"]
            if set(request) != request_keys or set(receipt) != receipt_keys:
                raise ValueError("envelope fields")
            if request["contract"] != "tuc.bounded_model_artifact_request.v0":
                raise ValueError("request contract")
            model_identity = {
                "schema_version": "tuc.bounded_cpu_model.v0",
                "graph": fixed_graph(),
                "parameter_bits": {"w": bits((weight, -1.0, 1.0, 3.0))},
            }
            model_digest = hashlib.sha256(encoded(model_identity, newline=False)).hexdigest()
            if request["model_digest"] != model_digest:
                raise ValueError("model identity")
            expected_inputs = [
                {
                    "tensor_name": n,
                    "tensor_index": i,
                    "shape": [2, 2],
                    "dtype": "float32",
                    "value_bits": v,
                }
                for n, i, v in (("x", 0, bits(x)), ("w", 1, bits((weight, -1.0, 1.0, 3.0))))
            ]
            if encoded(request["inputs"]) != encoded(expected_inputs):
                raise ValueError("input bits")
            if request["request_digest"] != digest(
                {k: v for k, v in request.items() if k != "request_digest"}
            ):
                raise ValueError("request digest")
            for key in (
                "bundle_digest",
                "request_digest",
                "model_digest",
                "model_compilation_digest",
                "backend_bindings_digest",
            ):
                if receipt[key] != request[key]:
                    raise ValueError("context")
            raw, rows, scores = reference(x, weight)
            expected_outputs = [
                {
                    "public_name": public,
                    "tensor_name": tensor,
                    "tensor_index": i,
                    "shape": shape,
                    "dtype": "float32",
                    "value_bits": bits(values),
                }
                for public, tensor, i, shape, values in (
                    ("rows", "r", 4, [2], rows),
                    ("scores", "y", 3, [2, 2], scores),
                )
            ]
            if encoded(receipt["outputs"]) != encoded(expected_outputs):
                raise ValueError("numerical outputs")
            if (
                receipt["contract"] != "tuc.bounded_model_application_result.v0"
                or receipt["protocol_validated"] is not True
                or receipt["native_execution_observed"] is not False
            ):
                raise ValueError("receipt claims")
            program = bytes.fromhex(receipt["program_digest"])
            if len(program) != 32:
                raise ValueError("program")
            payload = bytes.fromhex(bits(x) + bits((weight, -1.0, 1.0, 3.0)))
            protocol_digest = hashlib.sha256(program + payload).digest()
            if receipt["protocol_request_digest"] != protocol_digest.hex():
                raise ValueError("binary request")
            response = (
                b"TUCOUT01"
                + program
                + protocol_digest
                + struct.pack("<I", 0)
                + bytes.fromhex(bits(rows + scores))
            )
            if receipt["response_sha256"] != hashlib.sha256(response).hexdigest():
                raise ValueError("response identity")
            if receipt["result_digest"] != digest(
                {k: v for k, v in receipt.items() if k != "result_digest"}
            ):
                raise ValueError("result digest")
            models.append(model_digest)
            bundles.append(receipt["bundle_digest"])
            programs.append(receipt["program_digest"])
            requests.append(request["request_digest"])
            protocol_requests.append(protocol_digest.hex())
        if (
            len(set(models)) != 2
            or len(set(bundles)) != 2
            or len(set(programs)) != 1
            or len(set(requests)) != 3
            or len(set(protocol_requests)) != 3
        ):
            raise ValueError("context stability")
        expected_rejections = [
            {"name": name, "reason": "model_application_rejected"}
            for name in ("malformed_request", "wrong_extent", "fixed_override")
        ]
        expected_rejections.append({"name": "numeric_overflow", "reason": "numeric_rejection"})
        if encoded(record["rejections"]) != encoded(expected_rejections):
            raise ValueError("rejections")
        return {
            "schema_version": "tuc.bounded_model_application_native_audit.v0",
            "status": "PASS",
            "record_sha256": hashlib.sha256(data).hexdigest(),
            "scalar_checks": 18,
            "model_checks": 3,
            "request_checks": 3,
            "response_checks": 3,
            "rejection_checks": 4,
            "tuc_imported": False,
            "native_execution_performed": False,
        }
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
        UnicodeError,
        struct.error,
    ):
        raise ValueError("native_record_rejected") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    with args.record.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    print(encoded(audit(data)).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
