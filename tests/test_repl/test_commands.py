from __future__ import annotations

import json
import tempfile
from pathlib import Path

from vioscope.repl.commands.base import BaseCommand, UsageError
from vioscope.repl.commands.help import HelpCommand
from vioscope.repl.commands.pipeline import PipelineCommand
from vioscope.repl.commands.session import SessionCommand
from vioscope.repl.commands.synth import SynthCommand
from vioscope.repl.context import SessionContext
from vioscope.schemas.research import Paper


def _ctx(**kwargs: object) -> SessionContext:
    return SessionContext(session_id="cmd-test", **kwargs)  # type: ignore[arg-type]


def _paper() -> Paper:
    return Paper(paper_id="p1", title="Test Paper", abstract="abstract", authors=["Author A"])


# --- HelpCommand ---


def test_help_command_contains_all_agents() -> None:
    result = HelpCommand(_ctx(), None).run("")
    for cmd in ["/scout", "/synth", "/spark", "/skeptic", "/scribe", "/steward"]:
        assert cmd in result


# --- SessionCommand ---


def test_session_command_empty_ctx() -> None:
    result = SessionCommand(_ctx(), None).run("")
    assert "cmd-test" in result
    assert "Papers found:** 0" in result
    assert "not yet run" in result


def test_session_command_with_papers() -> None:
    ctx = _ctx(papers_found=[_paper()])
    result = SessionCommand(ctx, None).run("")
    assert "Papers found:** 1" in result


# --- SynthCommand ---


def test_synth_command_no_papers_returns_guidance() -> None:
    result = SynthCommand(_ctx(), None).run("")
    assert "scout" in result.lower()


def test_synth_command_no_agents_returns_error() -> None:
    ctx = _ctx(papers_found=[_paper()])
    result = SynthCommand(ctx, None).run("")
    assert "Agents not initialized" in result


# --- PipelineCommand ---


def test_pipeline_command_no_context_returns_guidance() -> None:
    result = PipelineCommand(_ctx(), None).run("")
    assert "scout" in result.lower()


def test_pipeline_command_with_papers_promotes() -> None:
    ctx = _ctx(papers_found=[_paper()])
    result = PipelineCommand(ctx, None).run("test question")
    # to_pipeline_session is now implemented, returns success message
    assert "pipeline" in result.lower() or "Pipeline" in result


# --- BaseCommand resolve_input ---


def test_resolve_input_from_session_papers() -> None:
    ctx = _ctx(papers_found=[_paper()])

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    cmd = _Cmd(ctx, None)
    resolved = cmd.resolve_input()
    assert resolved["source"] == "session"
    assert resolved["papers"] == [_paper()]


def test_resolve_input_from_file() -> None:
    ctx = _ctx()

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value"}, f)
        fpath = f.name

    cmd = _Cmd(ctx, None)
    resolved = cmd.resolve_input(flag_input=fpath)
    assert resolved["source"] == "file"
    assert resolved["data"] == {"key": "value"}
    Path(fpath).unlink()


def test_resolve_input_from_kb() -> None:
    ctx = _ctx()

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    cmd = _Cmd(ctx, None)
    resolved = cmd.resolve_input(flag_from_kb="abc123")
    assert resolved["source"] == "kb"
    assert resolved["kb_id"] == "abc123"


def test_resolve_input_raises_usage_error_when_no_context() -> None:
    ctx = _ctx()

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    import pytest

    cmd = _Cmd(ctx, None)
    with pytest.raises(UsageError):
        cmd.resolve_input()


# --- Flag parsing ---


def test_parse_flags_input_flag() -> None:
    ctx = _ctx()

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    cmd = _Cmd(ctx, None)
    positional, flag_input, flag_from_kb = cmd._parse_flags("--input myfile.json query text")
    assert flag_input == "myfile.json"
    assert flag_from_kb is None
    assert "query" in positional


def test_parse_flags_from_kb_flag() -> None:
    ctx = _ctx()

    class _Cmd(BaseCommand):
        def run(self, args: str) -> str:
            return ""

    cmd = _Cmd(ctx, None)
    positional, flag_input, flag_from_kb = cmd._parse_flags("--from-kb abc123")
    assert flag_from_kb == "abc123"
    assert flag_input is None
    assert positional.strip() == ""
