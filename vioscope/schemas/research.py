from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import (  # type: ignore[import-not-found]
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


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


class MethodGroup(BaseModel):
    name: str
    papers: List[str]
    description: str

    model_config = ConfigDict(extra="forbid")


class DatasetEntry(BaseModel):
    name: str
    modality: str
    size: str
    papers_using: List[str]

    model_config = ConfigDict(extra="forbid")


class SynthesisReport(BaseModel):
    method_taxonomy: List[MethodGroup]
    dataset_summary: List[DatasetEntry]
    performance_landscape: str
    research_gaps: List[str]
    source_paper_ids: List[str]

    model_config = ConfigDict(extra="forbid")


class SparkRole(str, Enum):
    INNOVATOR = "innovator"
    PRAGMATIST = "pragmatist"
    CONTRARIAN = "contrarian"


class HypothesisRoleRationale(BaseModel):
    role: SparkRole
    rationale: str

    model_config = ConfigDict(extra="forbid")


class HypothesisRecord(BaseModel):
    hypothesis_id: str
    title: str
    statement: str
    rationale: str
    evidence: List[str] = Field(default_factory=list)
    rank: int | None = Field(default=None, ge=1)
    source_paper_ids: List[str] = Field(default_factory=list)
    role_rationales: List[HypothesisRoleRationale] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class HypothesisCandidateList(BaseModel):
    candidates: List[HypothesisRecord] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_candidate_details(self) -> "HypothesisCandidateList":
        required_roles = {
            SparkRole.INNOVATOR,
            SparkRole.PRAGMATIST,
            SparkRole.CONTRARIAN,
        }

        for candidate in self.candidates:
            if candidate.rank is None:
                raise ValueError("Each hypothesis candidate must include a rank.")
            if not candidate.source_paper_ids:
                raise ValueError(
                    "Each hypothesis candidate must include source_paper_ids provenance."
                )
            if not candidate.role_rationales:
                raise ValueError("Each hypothesis candidate must include role_rationales.")
            seen_roles = {item.role for item in candidate.role_rationales}
            if seen_roles != required_roles:
                missing_roles = sorted(role.value for role in required_roles - seen_roles)
                raise ValueError(
                    "Each hypothesis candidate must include rationales for all Spark roles. "
                    f"Missing: {', '.join(missing_roles)}"
                )

        return self


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
    "DatasetEntry",
    "HypothesisCandidateList",
    "HypothesisRecord",
    "HypothesisRoleRationale",
    "MethodGroup",
    "Paper",
    "SparkRole",
    "SynthesisReport",
]
