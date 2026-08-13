"""Standalone Objective Delta consumer using only TUC's public API."""

from pathlib import Path

from tuc.portable_compute import emit_portable_compute_proof

ROOT = Path(__file__).resolve().parent


if __name__ == "__main__":
    emit_portable_compute_proof(
        ROOT / "source_intent.v0.json",
        (
            ROOT / "external_vector.v0.json",
            ROOT / "external_systolic.v0.json",
        ),
    )
