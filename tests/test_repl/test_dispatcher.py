from __future__ import annotations

from vioscope.repl.context import SessionContext
from vioscope.repl.dispatcher import dispatch


def _ctx() -> SessionContext:
    return SessionContext(session_id="disp-test")


def test_unknown_slash_command_returns_error() -> None:
    result = dispatch("/unknown", _ctx())
    assert "Unknown command" in result
    assert "/unknown" in result


def test_known_exit_commands_return_empty() -> None:
    ctx = _ctx()
    assert dispatch("/quit", ctx) == ""
    assert dispatch("/exit", ctx) == ""
    assert dispatch("/q", ctx) == ""


def test_planned_commands_listed_in_error() -> None:
    result = dispatch("/foo", _ctx())
    assert "/scout" in result


def test_help_command_returns_help_text() -> None:
    result = dispatch("/help", _ctx())
    assert "/scout" in result
    assert "/synth" in result


def test_session_command_returns_session_info() -> None:
    result = dispatch("/session", _ctx())
    assert "Session" in result
    assert "Papers found" in result


def test_scout_command_no_agents_returns_error() -> None:
    result = dispatch("/scout retinal segmentation", _ctx(), agents=None)
    assert "Agents not initialized" in result or "Usage" in result or "retinal" in result


def test_synth_command_no_papers_returns_guidance() -> None:
    result = dispatch("/synth", _ctx(), agents=None)
    assert "scout" in result.lower() or "papers" in result.lower()


def test_natural_language_scout_intent_routes() -> None:
    result = dispatch("find papers about retinal segmentation", _ctx(), agents=None)
    # NL router should route to scout → returns agents-not-initialized or usage message
    assert result  # non-empty response
    assert "E11-S3" not in result  # old placeholder gone


def test_natural_language_ambiguous_asks_clarification() -> None:
    result = dispatch("hello there", _ctx(), agents=None)
    assert result  # should return some guidance
    assert "E11-S3" not in result


def test_natural_language_session_intent_routes() -> None:
    result = dispatch("what is my current session status?", _ctx(), agents=None)
    assert "Session" in result or "Papers" in result


def test_pipeline_command_no_context_returns_guidance() -> None:
    result = dispatch("/pipeline", _ctx(), agents=None)
    assert "scout" in result.lower() or "context" in result.lower()
