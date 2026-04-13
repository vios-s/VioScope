from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generator, cast

import pytest
from pydantic import ValidationError

from vioscope.agents.synth import (
    SynthAgent,
    SynthDefaults,
    SynthInput,
    _normalize_json_payload,
    build_synth,
    load_synth_defaults,
)
from vioscope.config import AgentConfig, ConfigError, ModelConfig, ModelOverride, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas import (
    DatasetEntry,
    MethodGroup,
    Paper,
    PipelineConfig,
    PipelineSession,
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
def clear_synth_default_caches() -> Generator[None, None, None]:
    load_synth_defaults.cache_clear()
    load_agent_defaults.cache_clear()
    yield
    load_synth_defaults.cache_clear()
    load_agent_defaults.cache_clear()


def make_valid_synthesis() -> dict[str, object]:
    return {
        "method_taxonomy": [
            {
                "name": "Self-supervised learning",
                "papers": ["p1", "p2"],
                "description": "Groups representation learning methods without dense labels.",
            }
        ],
        "dataset_summary": [
            {
                "name": "MIMIC-CXR",
                "modality": "x-ray",
                "size": "377k images",
                "papers_using": ["p1"],
            }
        ],
        "performance_landscape": "Method A leads AUROC while Method B improves calibration.",
        "research_gaps": ["Limited external validation across institutions."],
        "source_paper_ids": ["p1", "p2"],
    }


def assert_model_identity(agent: SynthAgent, provider: str, model_id: str) -> None:
    if isinstance(agent.model, str):
        assert agent.model == f"{provider}:{model_id}"
        return
    assert getattr(agent.model, "id", None) == model_id


def test_synthesis_report_accepts_well_formed_data() -> None:
    report = SynthesisReport.model_validate(make_valid_synthesis())

    assert report.method_taxonomy == [
        MethodGroup(
            name="Self-supervised learning",
            papers=["p1", "p2"],
            description="Groups representation learning methods without dense labels.",
        )
    ]
    assert report.dataset_summary == [
        DatasetEntry(
            name="MIMIC-CXR",
            modality="x-ray",
            size="377k images",
            papers_using=["p1"],
        )
    ]
    assert report.source_paper_ids == ["p1", "p2"]


@pytest.mark.parametrize(
    "missing_field",
    [
        "method_taxonomy",
        "dataset_summary",
        "performance_landscape",
        "research_gaps",
        "source_paper_ids",
    ],
)
def test_synthesis_report_requires_all_fields(missing_field: str) -> None:
    payload = make_valid_synthesis()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        SynthesisReport.model_validate(payload)


def test_synthesis_report_rejects_extra_fields() -> None:
    payload = make_valid_synthesis()
    payload["extra"] = "boom"

    with pytest.raises(ValidationError):
        SynthesisReport.model_validate(payload)


def test_synthesis_report_coerces_nested_json_strings() -> None:
    payload = json.dumps(
        {
            "method_taxonomy": [
                '{"name":"Self-supervised learning","papers":["p1"],"description":"Learns without dense labels."}'
            ],
            "dataset_summary": [
                '{"name":"MIMIC-CXR","modality":"x-ray","size":"377k images","papers_using":["p1"]}'
            ],
            "performance_landscape": "AUROC is reported for the main baseline.",
            "research_gaps": ["External validation remains limited."],
            "source_paper_ids": ["p1"],
        }
    )
    report = SynthesisReport.model_validate(_normalize_json_payload(payload))

    assert report.method_taxonomy[0].name == "Self-supervised learning"
    assert report.dataset_summary[0].name == "MIMIC-CXR"


def make_session() -> PipelineSession:
    return PipelineSession(
        session_id="synth-1",
        research_question="How do recent methods perform?",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(),
        screened_papers=[
            Paper(
                paper_id="p1",
                title="Paper 1",
                abstract="Abstract 1",
                authors=["Alice"],
                year=2024,
            )
        ],
    )


def test_build_synth_returns_agent() -> None:
    agent = build_synth(AgentConfig(model=ModelConfig(provider="anthropic", model_id="m")))

    assert isinstance(agent, SynthAgent)
    assert agent.resolved_model == ModelConfig(
        provider="anthropic",
        model_id="m",
        temperature=0.2,
        max_tokens=4096,
    )
    assert_model_identity(agent, "anthropic", "m")
    assert agent.output_schema is SynthesisReport
    assert agent.instructions == [
        "You are Synth, a research synthesis agent for VioScope.",
        "Produce a structured synthesis report that preserves dataset names, metrics, and experimental conditions verbatim.",
        "Group related methods into method_taxonomy, summarize datasets in dataset_summary, describe the performance_landscape, and list explicit research_gaps.",
        "Only use the structured input provided for this run.",
    ]


def test_load_synth_defaults_reads_yaml() -> None:
    defaults = load_synth_defaults()

    assert defaults == SynthDefaults(
        name="Synth",
        model=ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-6",
            temperature=0.2,
            max_tokens=4096,
        ),
        timeout_seconds=300,
        instructions=[
            "You are Synth, a research synthesis agent for VioScope.",
            "Produce a structured synthesis report that preserves dataset names, metrics, and experimental conditions verbatim.",
            "Group related methods into method_taxonomy, summarize datasets in dataset_summary, describe the performance_landscape, and list explicit research_gaps.",
            "Only use the structured input provided for this run.",
        ],
    )


def test_load_agent_defaults_raises_for_missing_asset() -> None:
    with pytest.raises(ConfigError, match="Missing packaged agent config"):
        load_agent_defaults("does-not-exist")


def test_synthesize_updates_session(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    captured: dict[str, Any] = {}

    def fake_run(self: SynthAgent, *, input: SynthInput) -> RunOutput:
        captured["input"] = input
        return RunOutput(content=SynthesisReport.model_validate(make_valid_synthesis()))

    monkeypatch.setattr(SynthAgent, "run", fake_run)

    agent = build_synth(AgentConfig())
    updated = agent.synthesize(session)

    assert isinstance(captured["input"], SynthInput)
    assert captured["input"].research_question == session.research_question
    assert captured["input"].papers == session.screened_papers
    assert updated.synthesis is not None
    assert updated.synthesis.source_paper_ids == ["p1", "p2"]


def test_synth_keeps_external_content_out_of_static_instructions() -> None:
    agent = build_synth(AgentConfig())

    combined_instructions = "\n".join(cast(list[str], agent.instructions))
    assert "Abstract 1" not in combined_instructions
    assert "Paper 1" not in combined_instructions


def test_synthesize_uses_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()

    class RecordingBreaker(CircuitBreaker[Any]):
        def __init__(self) -> None:
            super().__init__(backoff_seconds=0.0)
            self.called = False

        def call(self, fn: Any) -> Any:  # type: ignore[override]
            self.called = True
            return fn()

    breaker = RecordingBreaker()

    def fake_run(self: SynthAgent, *, input: SynthInput) -> RunOutput:
        return RunOutput(content=SynthesisReport.model_validate(make_valid_synthesis()))

    monkeypatch.setattr(SynthAgent, "run", fake_run)

    agent = SynthAgent(AgentConfig(), circuit_breaker=breaker)
    updated = agent.synthesize(session)

    assert breaker.called is True
    assert updated.synthesis is not None


def test_synthesize_returns_session_when_no_screened_papers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = PipelineSession(
        session_id="empty",
        research_question="RQ",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(),
    )

    def boom(self: SynthAgent, *, input: SynthInput) -> RunOutput:
        raise AssertionError("run should not be called")

    monkeypatch.setattr(SynthAgent, "run", boom)

    agent = build_synth(AgentConfig())
    updated = agent.synthesize(session)

    assert updated is session


def test_build_synth_uses_yaml_defaults_without_override() -> None:
    agent = build_synth(AgentConfig())

    assert isinstance(agent, SynthAgent)
    assert agent.resolved_model == ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        temperature=0.2,
        max_tokens=4096,
    )
    assert_model_identity(agent, "anthropic", "claude-sonnet-4-6")
    assert agent.timeout_seconds == 300


def test_build_synth_prefers_explicit_agent_model_override() -> None:
    agent = build_synth(
        AgentConfig(model=ModelConfig(provider="openrouter", model_id="anthropic/claude-3.7"))
    )

    assert isinstance(agent, SynthAgent)
    assert agent.resolved_model == ModelConfig(
        provider="openrouter",
        model_id="anthropic/claude-3.7",
        temperature=0.2,
        max_tokens=4096,
    )
    assert_model_identity(agent, "openrouter", "anthropic/claude-3.7")


def test_build_synth_applies_global_model_and_partial_agent_override() -> None:
    agent = build_synth(
        VioScopeConfig(
            model=ModelConfig(
                provider="openrouter",
                model_id="openai/gpt-5.4-nano",
                temperature=0.1,
                max_tokens=2048,
            ),
            agents={
                "synth": AgentConfig(
                    model=ModelOverride(
                        temperature=0.35,
                    )
                )
            },
        )
    )

    assert isinstance(agent, SynthAgent)
    assert agent.resolved_model == ModelConfig(
        provider="openrouter",
        model_id="openai/gpt-5.4-nano",
        temperature=0.35,
        max_tokens=2048,
    )
    assert_model_identity(agent, "openrouter", "openai/gpt-5.4-nano")
