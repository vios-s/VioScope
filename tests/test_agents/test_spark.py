from __future__ import annotations

import json
from typing import Generator

import pytest
from pydantic import ValidationError

from vioscope.agents.spark import (
    SparkAgent,
    SparkDefaults,
    _coerce_candidate_list,
    build_spark,
    load_spark_defaults,
)
from vioscope.config import AgentConfig, ConfigError, ModelConfig, ModelOverride, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.schemas import HypothesisCandidateList, HypothesisRecord, SparkRole


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
    assert agent.output_schema is HypothesisCandidateList
    assert agent.role_names == {
        SparkRole.INNOVATOR: "Innovator",
        SparkRole.PRAGMATIST: "Pragmatist",
        SparkRole.CONTRARIAN: "Contrarian",
    }
    assert len(agent.role_agents) == 3
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
