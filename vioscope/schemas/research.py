from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field  # type: ignore[import-not-found]


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: str
    url: str | None = None
    source: str | None = None
    database: str | None = None
    authors: List[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    verified: bool = False

    model_config = ConfigDict(extra="forbid")


class SynthesisReport(BaseModel):
    taxonomy: List[str]
    dataset_summary: List[str]
    performance_landscape: str
    gaps: List[str]
    provenance: str

    model_config = ConfigDict(extra="forbid")


class HypothesisRecord(BaseModel):
    hypothesis_id: str
    title: str
    statement: str
    rationale: str
    evidence: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CritiqueVerdict(str, Enum):
    PASS = "pass"
    PIVOT = "pivot"
    FAIL = "fail"


class CritiqueReport(BaseModel):
    mode: str
    verdict: CritiqueVerdict
    rationale: str
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    target_id: str | None = None

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "CritiqueReport",
    "CritiqueVerdict",
    "HypothesisRecord",
    "Paper",
    "SynthesisReport",
]
