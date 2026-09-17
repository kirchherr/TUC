"""Pure comparison of the bounded native fan-in worker records (RFC 0318)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from examples import bounded_native_fanin_workers as workers
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
)
from examples.bounded_native_fanin_workers import _bounded_metadata, load_observation


def compare_records(cpu, matrix):
    for value, worker in ((cpu, "c11"), (matrix, "matrix")):
        _bounded_metadata(value)
        if type(value) is not dict or _canonical_json(value) != _canonical_json(
            workers.build_record(value.get("observations"), worker, value.get("operator_image_id"))
        ):
            raise BoundedCompilerEmissionError("fan-in record rejected")
    if len({workers.candidate.snapshot(p)["hac_ir"] for p in workers.PROFILES}) != 1:
        raise BoundedCompilerEmissionError("fan-in-dependent HAC-IR rejected")
    observations = matrix["observations"]
    return {
        "schema_version": "tuc.bounded_fanin_comparison.v0",
        "status": "PASS",
        "source_intent_digest": workers.candidate.INTENT_DIGEST,
        "matrix_scalar_checks": sum(
            o["numeric_observation"]["scalar_checks"] for o in observations
        ),
        "matrix_rounding_witnesses": sum(
            o["numeric_observation"]["outputs_differing_from_reference64"] for o in observations
        ),
        "one_matrix_image": True,
        "placements": [{"profile": o["profile"], **o["residency"]} for o in observations],
        "c11_record_digest": _digest_payload(cpu),
        "matrix_record_digest": _digest_payload(matrix),
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
        "blocked_claims": [
            "arbitrary_inputs",
            "dynamic_shapes",
            "general_native_runtime",
            "concurrent_producers",
            "performance",
            "independent_reproduction",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs=2, metavar=("C11", "MATRIX"))
    args = parser.parse_args()
    try:
        report = compare_records(*(load_observation(p) for p in args.records))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print("bounded fan-in comparison rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
