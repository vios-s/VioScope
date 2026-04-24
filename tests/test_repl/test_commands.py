from __future__ import annotations

import json
import tempfile
from pathlib import Path

from vioscope.repl.commands.base import BaseCommand, UsageError
from vioscope.repl.commands.help import HelpCommand
from vioscope.repl.commands.pipeline import PipelineCommand
from vioscope.repl.commands.session import SessionCommand
from vioscope.repl.commands.skeptic import SkepticCommand
from vioscope.repl.commands.spark import SparkCommand
from vioscope.repl.commands.synth import SynthCommand
from vioscope.repl.context import SessionContext
from vioscope.schemas.pipeline import PipelineSession
from vioscope.schemas.research import (
    CritiqueReport,
    CritiqueVerdict,
    HypothesisRecord,
    Paper,
    SkepticMode,
    SynthesisReport,
)


def _ctx(**kwargs: object) -> SessionContext:
    return SessionContext(session_id="cmd-test", **kwargs)  # type: ignore[arg-type]


def _paper() -> Paper:
    return Paper(paper_id="p1", title="Test Paper", abstract="abstract", authors=["Author A"])


def _synthesis() -> SynthesisReport:
    return SynthesisReport.model_validate(
        {
            "method_taxonomy": [
                {"name": "Topology-aware", "papers": ["p1"], "description": "Keeps continuity."}
            ],
            "dataset_summary": [
                {
                    "name": "DRIVE",
                    "modality": "retinal image",
                    "size": "40 images",
                    "papers_using": ["p1"],
                }
            ],
            "performance_landscape": "Topology methods help continuity.",
            "research_gaps": ["Limited label efficiency evidence."],
            "source_paper_ids": ["p1"],
        }
    )


def _hypothesis(rank: int = 1) -> HypothesisRecord:
    return HypothesisRecord(
        hypothesis_id=f"h{rank}",
        title=f"Hypothesis {rank}",
        statement="Test statement",
        rationale="Test rationale",
        evidence=["Gap A"],
        rank=rank,
        source_paper_ids=["p1"],
        role_rationales=[
            {"role": "innovator", "rationale": "Novel."},
            {"role": "pragmatist", "rationale": "Feasible."},
            {"role": "contrarian", "rationale": "Needs controls."},
        ],
    )


def _critique(mode: SkepticMode = SkepticMode.HYPOTHESIS) -> CritiqueReport:
    return CritiqueReport(
        mode=mode,
        verdict=CritiqueVerdict.PIVOT,
        rationale="Needs stronger evidence.",
        issues=["Confounding remains unresolved."],
        recommendations=["Add a stronger baseline."],
        target_id="target-1",
    )


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


def test_session_command_with_critique_reports() -> None:
    ctx = _ctx(critique_reports=[_critique()])
    result = SessionCommand(ctx, None).run("")
    assert "Critique reports:** 1" in result
    assert "hypothesis/pivot" in result


# --- SynthCommand ---


def test_synth_command_no_papers_returns_guidance() -> None:
    result = SynthCommand(_ctx(), None).run("")
    assert "scout" in result.lower()


def test_synth_command_no_agents_returns_error() -> None:
    ctx = _ctx(papers_found=[_paper()])
    result = SynthCommand(ctx, None).run("")
    assert "Agents not initialized" in result


# --- SparkCommand ---


def test_spark_command_requires_synthesis_or_input() -> None:
    result = SparkCommand(_ctx(), None).run("")
    assert "synth" in result.lower()


def test_spark_command_no_agents_returns_error() -> None:
    ctx = _ctx(synthesis=_synthesis())
    result = SparkCommand(ctx, None).run("")
    assert "Agents not initialized" in result


def test_spark_command_generates_hypotheses_and_updates_context() -> None:
    ctx = _ctx(synthesis=_synthesis())

    class SparkStub:
        def generate(self, session: PipelineSession) -> PipelineSession:
            return session.model_copy(
                update={"hypothesis_candidates": [_hypothesis(1), _hypothesis(2)]}
            )

    agents = type("Agents", (), {"spark": SparkStub()})()
    result = SparkCommand(ctx, agents).run("")

    assert "Spark Complete" in result
    assert "Candidates generated:** 2" in result
    assert len(ctx.hypothesis_candidates) == 2


def test_spark_command_marks_regeneration_with_additional_constraint() -> None:
    ctx = _ctx(synthesis=_synthesis(), hypothesis_candidates=[_hypothesis(1)])
    captured: dict[str, object] = {}

    class SparkStub:
        def generate(self, session: PipelineSession) -> PipelineSession:
            captured["next_action"] = session.next_action
            captured["regeneration_constraints"] = session.regeneration_constraints
            captured["pivot_count"] = session.pivot_count
            return session.model_copy(update={"hypothesis_candidates": [_hypothesis(1)]})

    agents = type("Agents", (), {"spark": SparkStub()})()
    result = SparkCommand(ctx, agents).run('--additional-constraint "No clinical-trial data"')

    assert "Spark Complete" in result
    assert captured["next_action"] == "regenerate"
    assert captured["regeneration_constraints"] == ["No clinical-trial data"]
    assert captured["pivot_count"] == 0


# --- SkepticCommand ---


def test_skeptic_command_requires_context() -> None:
    result = SkepticCommand(_ctx(), None).run("")
    assert "No Skeptic target found" in result


def test_skeptic_command_no_agents_returns_error() -> None:
    ctx = _ctx(selected_hypothesis=_hypothesis(1))
    result = SkepticCommand(ctx, None).run("")
    assert "Agents not initialized" in result


def test_skeptic_command_reviews_hypothesis_and_updates_context() -> None:
    ctx = _ctx(selected_hypothesis=_hypothesis(1))

    class SkepticStub:
        def critique_hypothesis(
            self,
            session: PipelineSession,
            hypothesis: HypothesisRecord | None = None,
            *,
            additional_constraints: list[str] | None = None,
        ) -> CritiqueReport:
            assert session.selected_hypothesis is not None
            assert hypothesis is not None
            assert additional_constraints == ["Need stronger causal controls"]
            return _critique(SkepticMode.HYPOTHESIS)

    agents = type("Agents", (), {"skeptic": SkepticStub()})()
    result = SkepticCommand(ctx, agents).run("Need stronger causal controls")

    assert "Skeptic Complete" in result
    assert "Verdict:** pivot" in result
    assert len(ctx.critique_reports) == 1


def test_skeptic_command_reviews_manuscript_from_session() -> None:
    ctx = _ctx(draft_sections=["Introduction text", "Methods text"])

    class SkepticStub:
        def critique_manuscript(
            self,
            session: PipelineSession,
            draft_sections: list[object] | None = None,
            *,
            additional_constraints: list[str] | None = None,
        ) -> CritiqueReport:
            assert draft_sections is not None
            assert len(draft_sections) == 2
            assert additional_constraints is None
            return _critique(SkepticMode.MANUSCRIPT)

    agents = type("Agents", (), {"skeptic": SkepticStub()})()
    result = SkepticCommand(ctx, agents).run("")

    assert "Mode:** manuscript" in result
    assert len(ctx.critique_reports) == 1


# --- PipelineCommand ---


def test_pipeline_command_no_context_returns_guidance() -> None:
    result = PipelineCommand(_ctx(), None).run("")
    assert "scout" in result.lower()


def test_pipeline_command_with_papers_promotes() -> None:
    ctx = _ctx(papers_found=[_paper()])
    result = PipelineCommand(ctx, None).run("test question")
    # to_pipeline_session is now implemented, returns success message
    assert "pipeline" in result.lower() or "Pipeline" in result


def test_pipeline_command_with_screened_papers_promotes() -> None:
    ctx = _ctx(papers_screened=[_paper()])
    result = PipelineCommand(ctx, None).run("")
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
