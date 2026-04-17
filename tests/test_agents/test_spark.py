from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Generator

import pytest
from pydantic import ValidationError

from vioscope.agents.spark import (
    PIVOTExhaustedError,
    SparkAgent,
    SparkDefaults,
    SparkInput,
    _coerce_candidate_list,
    build_spark,
    load_spark_defaults,
)
from vioscope.config import AgentConfig, ConfigError, ModelConfig, ModelOverride, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas import (
    HypothesisCandidateList,
    HypothesisRecord,
    PipelineConfig,
    PipelineSession,
    ScopeOutput,
    SparkRole,
    SynthesisReport,
)


@pytest.fixture(autouse=True)
def clear_spark_default_caches() -> Generator[None, None, None]:
    load_spark_defaults.cache_clear()
    load_agent_defaults.cache_clear()
    yield
    load_spark_defaults.cache_clear()
    load_agent_defaults.cache_clear()


def make_candidate_payload() -> dict[str, object]:
    return {
        "candidates": [
            {
                "hypothesis_id": "h1",
                "title": "Adaptive vessel encoder for low-label ophthalmic segmentation",
                "statement": "A morphology-aware pretraining objective will improve transfer.",
                "rationale": "Multiple papers report label scarcity and topology failures.",
                "evidence": ["Gap: limited external validation", "Dataset: DRIVE"],
                "rank": 1,
                "source_paper_ids": ["p1", "p2"],
                "role_rationales": [
                    {
                        "role": "innovator",
                        "rationale": "The novelty comes from encoding retinal geometry directly.",
                    },
                    {
                        "role": "pragmatist",
                        "rationale": "The approach stays testable on public datasets.",
                    },
                    {
                        "role": "contrarian",
                        "rationale": "Need to guard against gains from augmentation alone.",
                    },
                ],
            }
        ]
    }


def assert_model_identity(agent: SparkAgent, provider: str, model_id: str) -> None:
    if isinstance(agent.model, str):
        assert agent.model == f"{provider}:{model_id}"
        return
    assert getattr(agent.model, "id", None) == model_id


def make_session(
    *,
    next_action: str = "continue",
    pivot_count: int = 0,
    regeneration_constraints: list[str] | None = None,
    strategy_notes: str = "Prefer reproducible experiments on public datasets.",
) -> PipelineSession:
    return PipelineSession(
        session_id="spark-1",
        research_question="How can we improve retinal vessel segmentation with limited labels?",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(max_pivot_rounds=2),
        next_action=next_action,  # type: ignore[arg-type]
        pivot_count=pivot_count,
        regeneration_constraints=regeneration_constraints or [],
        synthesis=SynthesisReport.model_validate(
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
                "performance_landscape": "Topology-aware methods help continuity but need better transfer.",
                "research_gaps": ["Few methods generalize across small labeled datasets."],
                "source_paper_ids": ["p1", "p2"],
            }
        ),
        scope=ScopeOutput(
            refined_question="How can we improve retinal vessel segmentation with limited labels?",
            search_axes=["retinal vessel segmentation", "limited labels"],
            strategy_notes=strategy_notes,
        ),
    )


def test_hypothesis_candidate_list_accepts_well_formed_data() -> None:
    candidates = HypothesisCandidateList.model_validate(make_candidate_payload())

    assert len(candidates.candidates) == 1
    assert candidates.candidates[0] == HypothesisRecord(
        hypothesis_id="h1",
        title="Adaptive vessel encoder for low-label ophthalmic segmentation",
        statement="A morphology-aware pretraining objective will improve transfer.",
        rationale="Multiple papers report label scarcity and topology failures.",
        evidence=["Gap: limited external validation", "Dataset: DRIVE"],
        rank=1,
        source_paper_ids=["p1", "p2"],
        role_rationales=[
            {
                "role": SparkRole.INNOVATOR,
                "rationale": "The novelty comes from encoding retinal geometry directly.",
            },
            {
                "role": SparkRole.PRAGMATIST,
                "rationale": "The approach stays testable on public datasets.",
            },
            {
                "role": SparkRole.CONTRARIAN,
                "rationale": "Need to guard against gains from augmentation alone.",
            },
        ],
    )


def test_hypothesis_candidate_list_requires_rank_and_provenance() -> None:
    payload = make_candidate_payload()
    candidate = payload["candidates"][0]
    assert isinstance(candidate, dict)
    candidate.pop("rank")

    with pytest.raises(ValidationError):
        HypothesisCandidateList.model_validate(payload)


def test_hypothesis_candidate_list_rejects_extra_fields() -> None:
    payload = make_candidate_payload()
    candidate = payload["candidates"][0]
    assert isinstance(candidate, dict)
    candidate["unexpected"] = "boom"

    with pytest.raises(ValidationError):
        HypothesisCandidateList.model_validate(payload)


def test_coerce_candidate_list_accepts_nested_json_strings() -> None:
    payload = json.dumps(
        {
            "candidates": [
                json.dumps(
                    {
                        "hypothesis_id": "h1",
                        "title": "Hypothesis title",
                        "statement": "Hypothesis statement",
                        "rationale": "Why the idea is plausible.",
                        "evidence": ["Gap A"],
                        "rank": 1,
                        "source_paper_ids": ["p1"],
                        "role_rationales": [
                            json.dumps(
                                {
                                    "role": "innovator",
                                    "rationale": "Novel combination of priors and topology.",
                                }
                            ),
                            json.dumps(
                                {
                                    "role": "pragmatist",
                                    "rationale": "Can be tested with existing benchmarks.",
                                }
                            ),
                            json.dumps(
                                {
                                    "role": "contrarian",
                                    "rationale": "May overfit to small datasets if unchecked.",
                                }
                            ),
                        ],
                    }
                )
            ]
        }
    )

    candidates = _coerce_candidate_list(payload)

    assert candidates.candidates[0].rank == 1
    assert candidates.candidates[0].role_rationales[0].role is SparkRole.INNOVATOR


def test_load_spark_defaults_reads_yaml() -> None:
    defaults = load_spark_defaults()

    assert defaults == SparkDefaults(
        name="Spark",
        model=ModelConfig(
            provider="anthropic",
            model_id="claude-opus-4-6",
            temperature=0.5,
            max_tokens=4096,
        ),
        timeout_seconds=300,
        roles={
            SparkRole.INNOVATOR: {
                "name": "Innovator",
                "instructions": [
                    "You are Innovator, Spark's novelty-seeking role for VioScope.",
                    "Propose bold but scientifically grounded hypotheses from the synthesis and constraints provided at runtime.",
                    "Maximize originality while still tying every idea to explicit evidence from the supplied synthesis.",
                ],
            },
            SparkRole.PRAGMATIST: {
                "name": "Pragmatist",
                "instructions": [
                    "You are Pragmatist, Spark's feasibility role for VioScope.",
                    "Stress-test each hypothesis for experimental realism, measurable outcomes, and available datasets or tooling.",
                    "Prefer hypotheses that can be validated without hidden dependencies beyond the supplied runtime context.",
                ],
            },
            SparkRole.CONTRARIAN: {
                "name": "Contrarian",
                "instructions": [
                    "You are Contrarian, Spark's blind-spot role for VioScope.",
                    "Actively look for confounders, over-claimed novelty, and ways a hypothesis could fail or mislead.",
                    "Surface the strongest objections while still referencing only the structured runtime context.",
                ],
            },
        },
    )


def test_load_agent_defaults_raises_for_missing_asset() -> None:
    with pytest.raises(ConfigError, match="Missing packaged agent config"):
        load_agent_defaults("missing-spark")


def test_build_spark_returns_agent_with_three_distinct_roles() -> None:
    agent = build_spark(AgentConfig())

    assert isinstance(agent, SparkAgent)
    assert agent.mode == "broadcast"
    assert agent.output_schema is HypothesisCandidateList
    assert agent.role_names == {
        SparkRole.INNOVATOR: "Innovator",
        SparkRole.PRAGMATIST: "Pragmatist",
        SparkRole.CONTRARIAN: "Contrarian",
    }
    assert len(agent.role_agents) == 3
    assert len(agent.members) == 3
    assert agent.role_agents[SparkRole.INNOVATOR].name == "Innovator"
    assert agent.role_agents[SparkRole.PRAGMATIST].name == "Pragmatist"
    assert agent.role_agents[SparkRole.CONTRARIAN].name == "Contrarian"
    assert "novelty-seeking role" in "\n".join(agent.role_instructions[SparkRole.INNOVATOR])
    assert "feasibility role" in "\n".join(agent.role_instructions[SparkRole.PRAGMATIST])
    assert "blind-spot role" in "\n".join(agent.role_instructions[SparkRole.CONTRARIAN])
    assert_model_identity(agent, "anthropic", "claude-opus-4-6")
    assert agent.timeout_seconds == 300


def test_build_spark_applies_global_model_and_partial_agent_override() -> None:
    agent = build_spark(
        VioScopeConfig(
            model=ModelConfig(
                provider="openrouter",
                model_id="openai/gpt-5.4-nano",
                temperature=0.15,
                max_tokens=1024,
            ),
            agents={"spark": AgentConfig(model=ModelOverride(temperature=0.3))},
        )
    )

    assert agent.resolved_model == ModelConfig(
        provider="openrouter",
        model_id="openai/gpt-5.4-nano",
        temperature=0.3,
        max_tokens=1024,
    )
    assert_model_identity(agent, "openrouter", "openai/gpt-5.4-nano")


def test_generate_populates_ranked_hypothesis_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session(regeneration_constraints=["No proprietary datasets."])
    captured: dict[str, Any] = {}

    class DummyResponse:
        def __init__(self, content: Any) -> None:
            self.content = content

    def fake_run(self: SparkAgent, *, input: SparkInput) -> DummyResponse:
        captured["input"] = input
        return DummyResponse(
            {
                "candidates": [
                    {
                        "hypothesis_id": "h2",
                        "title": "Second-ranked idea",
                        "statement": "Second statement",
                        "rationale": "Second rationale",
                        "evidence": ["Gap B"],
                        "rank": 2,
                        "source_paper_ids": ["p2"],
                        "role_rationales": [
                            {"role": "innovator", "rationale": "Novel twist."},
                            {"role": "pragmatist", "rationale": "Feasible benchmark."},
                            {"role": "contrarian", "rationale": "Could overfit."},
                        ],
                    },
                    {
                        "hypothesis_id": "h1",
                        "title": "Top idea",
                        "statement": "First statement",
                        "rationale": "First rationale",
                        "evidence": ["Gap A"],
                        "rank": 1,
                        "source_paper_ids": ["p1"],
                        "role_rationales": [
                            {"role": "innovator", "rationale": "Strong novelty."},
                            {"role": "pragmatist", "rationale": "Realistic to test."},
                            {"role": "contrarian", "rationale": "Needs ablation guardrails."},
                        ],
                    },
                ]
            }
        )

    monkeypatch.setattr(SparkAgent, "run", fake_run)

    agent = build_spark(AgentConfig())
    updated = agent.generate(session)

    assert captured["input"].research_question == session.research_question
    assert captured["input"].synthesis == session.synthesis
    assert captured["input"].additional_constraints == [
        "Prefer reproducible experiments on public datasets.",
        "No proprietary datasets.",
    ]
    assert updated.hypothesis_candidates is not None
    assert [candidate.rank for candidate in updated.hypothesis_candidates] == [1, 2]
    assert updated.pivot_count == 0
    assert updated.next_action == "continue"


def test_generate_increments_pivot_count_only_for_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_session = make_session(next_action="continue", pivot_count=0)
    rerun_session = make_session(
        next_action="regenerate",
        pivot_count=0,
        regeneration_constraints=["No clinical-trial data."],
    )

    class DummyResponse:
        def __init__(self, content: Any) -> None:
            self.content = content

    def fake_run(self: SparkAgent, *, input: SparkInput) -> DummyResponse:
        return DummyResponse(make_candidate_payload())

    monkeypatch.setattr(SparkAgent, "run", fake_run)
    agent = build_spark(AgentConfig())

    initial_updated = agent.generate(initial_session)
    rerun_updated = agent.generate(rerun_session)

    assert initial_updated.pivot_count == 0
    assert rerun_updated.pivot_count == 1


def test_generate_raises_pivot_exhausted_error_at_limit() -> None:
    session = make_session(next_action="regenerate", pivot_count=2)
    agent = build_spark(AgentConfig())

    with pytest.raises(PIVOTExhaustedError, match="max_pivot_rounds=2"):
        agent.generate(session)


def test_generate_uses_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()

    class RecordingBreaker(CircuitBreaker[Any]):
        def __init__(self) -> None:
            super().__init__(backoff_seconds=0.0)
            self.called = False

        def call(self, fn: Any) -> Any:  # type: ignore[override]
            self.called = True
            return fn()

    class DummyResponse:
        def __init__(self, content: Any) -> None:
            self.content = content

    def fake_run(self: SparkAgent, *, input: SparkInput) -> DummyResponse:
        return DummyResponse(make_candidate_payload())

    breaker = RecordingBreaker()
    monkeypatch.setattr(SparkAgent, "run", fake_run)

    agent = SparkAgent(AgentConfig(), circuit_breaker=breaker)
    updated = agent.generate(session)

    assert breaker.called is True
    assert updated.hypothesis_candidates is not None
