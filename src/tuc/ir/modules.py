"""Explicit IR module stages for the Phase 1 pipeline skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from tuc.ir.model import ComputeGraph


class IRStage(StrEnum):
    """Named compiler stages used by TUC's prototype pipeline."""

    TLIR = "tlir"
    HAC_IR = "hac-ir"
    HS_IR = "hs-ir"


@dataclass(frozen=True)
class IRModule:
    """A graph plus stage metadata."""

    stage: IRStage
    graph: ComputeGraph
    target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.target is not None and not self.target:
            raise ValueError("target must not be empty when provided")

    def with_metadata(self, **metadata: Any) -> IRModule:
        merged = dict(self.metadata)
        merged.update(metadata)
        return IRModule(
            stage=self.stage,
            graph=self.graph,
            target=self.target,
            metadata=merged,
        )
