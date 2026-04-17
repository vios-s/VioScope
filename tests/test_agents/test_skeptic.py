from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generator, cast

import pytest
from pydantic import ValidationError

from vioscope.agents.skeptic import (
    SkepticAgent,
    SkepticDefaults,
    SkepticInput,
    build_skeptic,
    compose_skeptic_instructions,
    load_skeptic_defaults,
)
from vioscope.config import AgentConfig, ConfigError, ModelConfig, ModelOverride, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas import (
    CritiqueReport,
    CritiqueVerdict,
    DraftSection,
    HypothesisRecord,
    PipelineConfig,
    PipelineSession,
    SkepticMode,
    SynthesisReport,
)

if TYPE_CHECKING:
    from agno.run.agent import RunOutput
else:
    try:
        from agno.run.agent import RunOutput
    except Exception:  # pragma: no cover - fallback for environments without agno

        class RunOutput:
            def __init__(self, content: Any = None) -> None:
                self.content = content


@pytest.fixture(autouse=True)
def clear_skeptic_default_caches() -> Generator[None, None, None]:
    load_skeptic_defaults.cache_clear()
    load_agent_defaults.cache_clear()
    yield
    load_skeptic_defaults.cache_clear()
    load_agent_defaults.cache_clear()


def _hypothesis() -> HypothesisRecord:
    return HypothesisRecord.model_validate(
        {
            "hypothesis_id": "h1",
            "title": "Topology-aware retinal pretraining",
            "statement": "Geometry-aware pretraining improves low-label transfer.",
            "rationale": "The synthesis shows label scarcity and vessel discontinuity gaps.",
            "evidence": ["Gap: limited external validation", "Dataset: DRIVE"],
            "rank": 1,
            "source_paper_ids": ["p1", "p2"],
            "role_rationales": [
                {"role": "innovator", "rationale": "Novel topology prior."},
                {"role": "pragmatist", "rationale": "Testable on public data."},
                {"role": "contrarian", "rationale": "Could just be augmentation gains."},
            ],
        }
    )


def _draft_sections() -> list[DraftSection]:
    return [
        DraftSection(
            name="Introduction",
            content="We study retinal vessel segmentation with limited labels.",
            template="nature",
            citations=["p1"],
            section_order=1,
        )
    ]


def _synthesis() -> SynthesisReport:
    return SynthesisReport.model_validate(
        {
            "method_taxonomy": [
                {
                    "name": "Topology-aware segmentation",
                    "papers": ["p1"],
                    "description": "Methods that preserve vessel continuity.",
                }
            ],
            "dataset_summary": [
                {
                    "name": "DRIVE",
                    "modality": "retinal image",
                    "size": "40 images",
                    "papers_using": ["p1"],
                }
            ],
            "performance_landscape": "Topology priors help continuity but hurt calibration if overfit.",
            "research_gaps": ["Few methods generalize under limited labels."],
            "source_paper_ids": ["p1", "p2"],
        }
    )


def _session() -> PipelineSession:
    return PipelineSession(
        session_id="skeptic-1",
        research_question="How can low-label retinal segmentation be improved?",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(),
        synthesis=_synthesis(),
        hypothesis_candidates=[_hypothesis()],
        selected_hypothesis=_hypothesis(),
        draft_sections=_draft_sections(),
    )


def assert_model_identity(agent: SkepticAgent, provider: str, model_id: str) -> None:
    if isinstance(agent.model, str):
        assert agent.model == f"{provider}:{model_id}"
        return
    assert getattr(agent.model, "id", None) == model_id


def test_load_skeptic_defaults_reads_yaml() -> None:
    defaults = load_skeptic_defaults()

    assert defaults == SkepticDefaults(
        name="Skeptic",
        model=ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-6",
            temperature=0.2,
            max_tokens=4096,
        ),
        timeout_seconds=300,
        anti_rationalization_directive=(
            "Do not rationalize weak work into a pass; surface the strongest scientific objections "
            "even when the idea is promising."
        ),
        shared_instructions=[
            "You are Skeptic, VioScope's adversarial review agent.",
            "Use only the structured runtime input for this critique. Do not invent missing evidence, results, or citations.",
            "Prefer concrete scientific criticism over generic writing advice, and make every recommendation actionable.",
        ],
        mode_instructions={
            SkepticMode.HYPOTHESIS: [
                "In hypothesis mode, test novelty claims, causal plausibility, confounders, measurability, and experiment design risk.",
                "Recommend `pivot` when the core direction could succeed with substantial reframing or stronger controls.",
            ],
            SkepticMode.MANUSCRIPT: [
                "In manuscript mode, critique claim discipline, experimental support, citation grounding, and venue-appropriate scientific communication.",
                "Recommend `fail` when the current draft should not proceed without major evidentiary or structural repair.",
            ],
        },
    )


def test_load_agent_defaults_raises_for_missing_asset() -> None:
    with pytest.raises(ConfigError, match="Missing packaged agent config"):
        load_agent_defaults("missing-skeptic")


def test_compose_skeptic_instructions_include_shared_directive() -> None:
    defaults = load_skeptic_defaults()
    hypothesis_instructions = compose_skeptic_instructions(SkepticMode.HYPOTHESIS)
    manuscript_instructions = compose_skeptic_instructions(SkepticMode.MANUSCRIPT)

    assert defaults.anti_rationalization_directive in hypothesis_instructions
    assert defaults.anti_rationalization_directive in manuscript_instructions


def test_skeptic_input_requires_matching_payload() -> None:
    with pytest.raises(ValidationError):
        SkepticInput(mode=SkepticMode.HYPOTHESIS, research_question="Q")

    with pytest.raises(ValidationError):
        SkepticInput(mode=SkepticMode.MANUSCRIPT, research_question="Q")


def test_build_skeptic_applies_global_model_and_agent_override() -> None:
    agent = build_skeptic(
        VioScopeConfig(
            model=ModelConfig(
                provider="openrouter",
                model_id="openai/gpt-5.4-mini",
                temperature=0.15,
                max_tokens=2048,
            ),
            agents={"skeptic": AgentConfig(model=ModelOverride(temperature=0.05))},
        )
    )

    assert agent.resolved_model == ModelConfig(
        provider="openrouter",
        model_id="openai/gpt-5.4-mini",
        temperature=0.05,
        max_tokens=2048,
    )
    assert_model_identity(agent, "openrouter", "openai/gpt-5.4-mini")
    combined_instructions = "\n".join(cast(list[str], agent.instructions))
    assert _hypothesis().title not in combined_instructions
    assert _draft_sections()[0].content not in combined_instructions


def test_critique_hypothesis_uses_structured_input(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    captured: dict[str, Any] = {}

    def fake_run(self: SkepticAgent, *, input: SkepticInput) -> RunOutput:
        captured["input"] = input
        return RunOutput(
            content=CritiqueReport(
                mode=SkepticMode.HYPOTHESIS,
                verdict=CritiqueVerdict.PIVOT,
                rationale="Interesting direction, but the causal claim needs stronger controls.",
                issues=["Potential confounding from augmentation."],
                recommendations=["Add ablations against geometry-only baselines."],
            )
        )

    monkeypatch.setattr(SkepticAgent, "run", fake_run)

    agent = build_skeptic(AgentConfig())
    critique = agent.critique_hypothesis(session)

    assert isinstance(captured["input"], SkepticInput)
    assert captured["input"].mode is SkepticMode.HYPOTHESIS
    assert captured["input"].hypothesis == session.selected_hypothesis
    assert critique.mode is SkepticMode.HYPOTHESIS
    assert critique.target_id == "h1"


def test_critique_manuscript_uses_structured_input(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    captured: dict[str, Any] = {}

    def fake_run(self: SkepticAgent, *, input: SkepticInput) -> RunOutput:
        captured["input"] = input
        return RunOutput(
            content={
                "mode": "manuscript",
                "verdict": "fail",
                "rationale": "The draft overclaims generalization without enough evidence.",
                "issues": ["No external validation section is described."],
                "recommendations": ["Add institution-shift experiments and narrow the claims."],
            }
        )

    monkeypatch.setattr(SkepticAgent, "run", fake_run)

    agent = build_skeptic(AgentConfig())
    critique = agent.critique_manuscript(session)

    assert isinstance(captured["input"], SkepticInput)
    assert captured["input"].mode is SkepticMode.MANUSCRIPT
    assert captured["input"].draft_sections == session.draft_sections
    assert critique.mode is SkepticMode.MANUSCRIPT
    assert critique.target_id == "Introduction"


def test_critique_uses_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()

    class RecordingBreaker(CircuitBreaker[Any]):
        def __init__(self) -> None:
            super().__init__(backoff_seconds=0.0)
            self.called = False

        def call(self, fn: Any) -> Any:  # type: ignore[override]
            self.called = True
            return fn()

    breaker = RecordingBreaker()

    def fake_run(self: SkepticAgent, *, input: SkepticInput) -> RunOutput:
        return RunOutput(
            content={
                "mode": input.mode.value,
                "verdict": "pass",
                "rationale": "The critique target is acceptable with current evidence.",
                "issues": [],
                "recommendations": [],
                "target_id": "explicit-target",
            }
        )

    monkeypatch.setattr(SkepticAgent, "run", fake_run)

    agent = SkepticAgent(AgentConfig(), circuit_breaker=breaker)
    critique = agent.critique_hypothesis(session)

    assert breaker.called is True
    assert critique.target_id == "explicit-target"
