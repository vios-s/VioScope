from __future__ import annotations

from vioscope.repl.context import SessionContext
from vioscope.repl.nl_router import _classify_intent, nl_router


def _ctx() -> SessionContext:
    return SessionContext(session_id="nl-test")


def test_classify_scout_intent() -> None:
    assert _classify_intent("find papers about retinal segmentation") == "scout"
    assert _classify_intent("search for literature on SAM2") == "scout"


def test_classify_synth_intent() -> None:
    assert _classify_intent("synthesize my findings") == "synth"
    assert _classify_intent("give me a synthesis overview") == "synth"


def test_classify_session_intent() -> None:
    assert _classify_intent("what is my current session status?") == "session"
    assert _classify_intent("show my progress so far") == "session"


def test_classify_pipeline_intent() -> None:
    assert _classify_intent("run the full pipeline now") == "pipeline"


def test_classify_quit_intent() -> None:
    assert _classify_intent("quit") == "quit"
    assert _classify_intent("goodbye") == "quit"


def test_classify_unknown_returns_none() -> None:
    assert _classify_intent("hello there") is None


def test_nl_router_scout_no_agents() -> None:
    result = nl_router("find papers about retinal segmentation", _ctx(), agents=None)
    assert result
    # Routes to ScoutCommand which returns agents-not-initialized without agents
    assert "E11-S3" not in result


def test_nl_router_session_returns_context() -> None:
    result = nl_router("what is my session status?", _ctx(), agents=None)
    assert "Session" in result or "Papers" in result


def test_nl_router_ambiguous_asks_clarification() -> None:
    result = nl_router("hello", _ctx(), agents=None)
    assert result
    assert "/help" in result or "not sure" in result.lower()


def test_nl_router_quit_returns_empty() -> None:
    result = nl_router("quit please", _ctx(), agents=None)
    assert result == ""
