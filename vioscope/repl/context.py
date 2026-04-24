from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from vioscope.schemas.pipeline import PipelineConfig, PipelineSession
from vioscope.schemas.research import CritiqueReport, HypothesisRecord, Paper, SynthesisReport


class SessionContext(BaseModel):
    session_id: str
    papers_found: list[Paper] = Field(default_factory=list)
    papers_screened: list[Paper] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
    hypothesis_candidates: list[HypothesisRecord] = Field(default_factory=list)
    selected_hypothesis: HypothesisRecord | None = None
    critique_reports: list[CritiqueReport] = Field(default_factory=list)
    draft_sections: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def to_pipeline_session(self, question: str) -> PipelineSession:
        """Promote interactive context to a full PipelineSession."""
        screened = self.papers_screened or None
        search_results = self.papers_found or None
        hypotheses = self.hypothesis_candidates if self.hypothesis_candidates else None
        critiques = self.critique_reports or None
        return PipelineSession(
            session_id=self.session_id,
            research_question=question,
            created_at=datetime.now(timezone.utc),
            config=PipelineConfig(),
            entry_mode="interactive",
            search_results=search_results,
            screened_papers=screened,
            synthesis=self.synthesis,
            hypothesis_candidates=hypotheses,
            selected_hypothesis=self.selected_hypothesis,
            critique_reports=critiques,
        )
