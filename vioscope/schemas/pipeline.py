from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field  # type: ignore[import-not-found]

from vioscope.schemas.research import CritiqueReport, HypothesisRecord, Paper, SynthesisReport
from vioscope.schemas.writing import DraftSection, JournalTemplate, PaperOutline


class PipelineConfig(BaseModel):
    max_papers: int = 50
    databases: List[str] = Field(
        default_factory=lambda: ["arxiv", "pubmed", "semantic_scholar", "openalex"]
    )
    max_pivot_rounds: int = 3
    session_cost_cap: float | None = None

    model_config = ConfigDict(extra="forbid")


class ScopeOutput(BaseModel):
    refined_question: str
    search_axes: List[str]
    strategy_notes: str

    model_config = ConfigDict(extra="forbid")


class PipelineSession(BaseModel):
    session_id: str
    research_question: str
    created_at: datetime
    config: PipelineConfig
    entry_mode: Literal["research", "search_only", "write", "review"] = "research"
    next_action: Literal["continue", "regenerate", "quit"] = "continue"
    regeneration_constraints: List[str] = Field(default_factory=list)
    stage_reached: int = 0
    pivot_count: int = 0

    scope: ScopeOutput | None = None
    search_results: List[Paper] | None = None
    screened_papers: List[Paper] | None = None
    synthesis: SynthesisReport | None = None
    hypothesis_candidates: List[HypothesisRecord] | None = None
    selected_hypothesis: HypothesisRecord | None = None
    critique_reports: List[CritiqueReport] | None = None
    paper_outline: PaperOutline | None = None
    draft_sections: List[DraftSection] | None = None
    final_approved: bool = False
    gitbook_synced: bool = False

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "PipelineConfig",
    "PipelineSession",
    "ScopeOutput",
    "JournalTemplate",
]
