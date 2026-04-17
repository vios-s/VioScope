from __future__ import annotations

import pytest

from vioscope.repl.context import SessionContext
from vioscope.schemas.pipeline import PipelineSession


def test_session_context_construction() -> None:
    ctx = SessionContext(session_id="test-123")
    assert ctx.session_id == "test-123"
    assert ctx.papers_found == []
    assert ctx.papers_screened == []
    assert ctx.synthesis is None
    assert ctx.hypothesis_candidates == []
    assert ctx.selected_hypothesis is None
    assert ctx.draft_sections == []


def test_session_context_extra_fields_forbidden() -> None:
    with pytest.raises(Exception):
        SessionContext(session_id="test", unknown_field="bad")  # type: ignore[call-arg]


def test_to_pipeline_session_returns_pipeline_session() -> None:
    ctx = SessionContext(session_id="test-456")
    ps = ctx.to_pipeline_session("What is SAM2?")
    assert isinstance(ps, PipelineSession)
    assert ps.session_id == "test-456"
    assert ps.research_question == "What is SAM2?"
    assert ps.entry_mode == "interactive"
    assert ps.search_results is None
    assert ps.screened_papers is None
    assert ps.synthesis is None
    assert ps.hypothesis_candidates is None
    assert ps.selected_hypothesis is None
