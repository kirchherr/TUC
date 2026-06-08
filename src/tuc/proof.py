"""Deterministic proof-report metadata for TUC validation artifacts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.runtime import Assignment, PartitionPlan

PROOF_REPORT_SCHEMA_VERSION = "proof-report.v0"
MAX_PROOF_METADATA_STRING_BYTES = 128
MAX_PROOF_BACKENDS = 16

_PROOF_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_BACKEND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


@dataclass(frozen=True)
class ProofReportMetadata:
    """Stable metadata printed in proof reports before compiler artifacts."""

    proof_id: str
    proof_version: str
    graph_family: str
    backend_set: tuple[str, ...]
    report_schema: str = PROOF_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_proof_identifier(self.report_schema, "report_schema")
        _validate_proof_identifier(self.proof_id, "proof_id")
        _validate_proof_identifier(self.proof_version, "proof_version")
        _validate_proof_identifier(self.graph_family, "graph_family")
        normalized_backends = _normalize_backend_set(self.backend_set)
        object.__setattr__(self, "backend_set", normalized_backends)

    def render_lines(self) -> tuple[str, ...]:
        """Return deterministic text lines for proof report rendering."""

        return (
            f"report_schema: {self.report_schema}",
            f"proof_id: {self.proof_id}",
            f"proof_version: {self.proof_version}",
            f"graph_family: {self.graph_family}",
            f"backend_set: {', '.join(self.backend_set)}",
        )


def proof_metadata_from_partition_plan(
    *,
    proof_id: str,
    proof_version: str,
    graph_family: str,
    partition_plan: PartitionPlan,
) -> ProofReportMetadata:
    """Build proof metadata from an already validated partition plan."""

    return ProofReportMetadata(
        proof_id=proof_id,
        proof_version=proof_version,
        graph_family=graph_family,
        backend_set=_backend_set_from_assignments(partition_plan.assignments),
    )


def _backend_set_from_assignments(
    assignments: Iterable[Assignment],
) -> tuple[str, ...]:
    return tuple(sorted({assignment.backend_name for assignment in assignments}))


def _normalize_backend_set(backends: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(backends, tuple):
        raise TypeError("backend_set must be a tuple")
    if not backends:
        raise ValueError("backend_set must not be empty")
    if len(backends) > MAX_PROOF_BACKENDS:
        raise ValueError("backend_set exceeds proof metadata backend limit")
    if len(set(backends)) != len(backends):
        raise ValueError("backend_set must not contain duplicate names")

    normalized: list[str] = []
    for backend in backends:
        if not isinstance(backend, str) or not _BACKEND_NAME_RE.fullmatch(backend):
            raise ValueError("backend_set entries must be safe backend identifiers")
        _validate_string_budget(backend, "backend_set entry")
        normalized.append(backend)
    return tuple(sorted(normalized))


def _validate_proof_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe proof identifier")
    _validate_string_budget(value, label)


def _validate_string_budget(value: str, label: str) -> None:
    if len(value.encode("utf-8")) > MAX_PROOF_METADATA_STRING_BYTES:
        raise ValueError(f"{label} exceeds proof metadata string limit")


__all__ = [
    "MAX_PROOF_BACKENDS",
    "MAX_PROOF_METADATA_STRING_BYTES",
    "PROOF_REPORT_SCHEMA_VERSION",
    "ProofReportMetadata",
    "proof_metadata_from_partition_plan",
]
