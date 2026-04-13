from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from vioscope.agents.scout import ScoutAgent, ScoutDefaults, build_scout, load_scout_defaults
from vioscope.config import AgentConfig, ConfigError, ModelConfig, ModelOverride, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas import PipelineConfig, PipelineSession, ScopeOutput


@pytest.fixture(autouse=True)
def clear_scout_default_caches() -> None:
    load_scout_defaults.cache_clear()
    load_agent_defaults.cache_clear()


def make_session(*, databases: list[str] | None = None) -> PipelineSession:
    return PipelineSession(
        session_id="scout-1",
        research_question="How do recent methods perform?",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(
            databases=databases or ["semantic_scholar", "openalex", "arxiv", "pubmed"]
        ),
        scope=ScopeOutput(
            refined_question="How do recent methods perform?",
            search_axes=["retinal", "segmentation"],
            strategy_notes="focus on limited-label settings",
        ),
    )


class DummySearchTool:
    def __init__(self, payload: list[dict[str, Any]]) -> None:
        self.payload = payload

    def search(self, *args: Any, **_kwargs: Any) -> str:
        return json.dumps(self.payload)


def assert_model_identity(agent: ScoutAgent, provider: str, model_id: str) -> None:
    if isinstance(agent.model, str):
        assert agent.model == f"{provider}:{model_id}"
        return
    assert getattr(agent.model, "id", None) == model_id


def test_load_scout_defaults_reads_yaml() -> None:
    defaults = load_scout_defaults()

    assert defaults == ScoutDefaults(
        name="Scout",
        model=ModelConfig(
            provider="anthropic",
            model_id="claude-haiku-4-5-20251001",
            temperature=0.1,
            max_tokens=2048,
        ),
        timeout_seconds=180,
        instructions=[
            "You are Scout, a research search agent for VioScope.",
            "Search one scholarly database at a time and normalize every returned paper into the shared schema.",
            "Run citation verification for each paper and preserve the verified flag in the final result set.",
            "Only use the structured runtime input provided for this search.",
        ],
    )


def test_load_agent_defaults_raises_for_missing_asset() -> None:
    with pytest.raises(ConfigError, match="Missing packaged agent config"):
        load_agent_defaults("missing-scout")


def test_build_scout_uses_yaml_defaults_without_override() -> None:
    agent = build_scout(AgentConfig())

    assert isinstance(agent, ScoutAgent)
    assert agent.resolved_model == ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        temperature=0.1,
        max_tokens=2048,
    )
    assert_model_identity(agent, "anthropic", "claude-haiku-4-5-20251001")
    assert agent.timeout_seconds == 180


def test_build_scout_applies_global_model_and_partial_agent_override() -> None:
    agent = build_scout(
        VioScopeConfig(
            model=ModelConfig(
                provider="openrouter",
                model_id="openai/gpt-5.4-nano",
                temperature=0.15,
                max_tokens=1024,
            ),
            agents={"scout": AgentConfig(model=ModelOverride(temperature=0.05))},
        )
    )

    assert agent.resolved_model == ModelConfig(
        provider="openrouter",
        model_id="openai/gpt-5.4-nano",
        temperature=0.05,
        max_tokens=1024,
    )
    assert_model_identity(agent, "openrouter", "openai/gpt-5.4-nano")


@pytest.mark.parametrize(
    ("database", "payload", "arxiv_payload", "pubmed_payload"),
    [
        (
            "semantic_scholar",
            [
                {
                    "paper_id": "s2-1",
                    "title": "Semantic Scholar Paper",
                    "abstract": "Semantic Scholar abstract",
                    "authors": ["Alice"],
                    "year": 2024,
                    "url": "https://example.org/s2",
                }
            ],
            [],
            [],
        ),
        (
            "openalex",
            [
                {
                    "id": "oa-1",
                    "title": "OpenAlex Paper",
                    "abstract": "OpenAlex abstract",
                    "authors": ["Bob"],
                    "year": 2023,
                    "open_access_url": "https://example.org/oa",
                }
            ],
            [],
            [],
        ),
        (
            "arxiv",
            [],
            [
                {
                    "id": "arxiv-1",
                    "title": "Arxiv Paper",
                    "summary": "Arxiv summary",
                    "authors": ["Cara"],
                    "year": 2022,
                    "url": "https://example.org/arxiv",
                }
            ],
            [],
        ),
        (
            "pubmed",
            [],
            [],
            [
                {
                    "uid": "pubmed-1",
                    "title": "PubMed Paper",
                    "abstract": "PubMed abstract",
                    "authors": ["Dan"],
                    "year": 2021,
                    "url": "https://example.org/pubmed",
                }
            ],
        ),
    ],
)
def test_search_normalizes_and_verifies_results(
    monkeypatch: pytest.MonkeyPatch,
    database: str,
    payload: list[dict[str, Any]],
    arxiv_payload: list[dict[str, Any]],
    pubmed_payload: list[dict[str, Any]],
) -> None:
    session = make_session()
    arxiv_tools = DummySearchTool(arxiv_payload)
    pubmed_tools = DummySearchTool(pubmed_payload)

    monkeypatch.setattr(
        "vioscope.agents.scout.search_semantic_scholar",
        lambda query, limit=20: (
            json.dumps(payload) if database == "semantic_scholar" else json.dumps([])
        ),
    )
    monkeypatch.setattr(
        "vioscope.agents.scout.search_openalex",
        lambda query, limit=20: json.dumps(payload) if database == "openalex" else json.dumps([]),
    )
    monkeypatch.setattr(
        "vioscope.agents.scout.verify_citation",
        lambda title, authors, year: json.dumps(
            {"verified": True, "doi": "", "url": "", "similarity_score": 1.0}
        ),
    )

    agent = ScoutAgent(AgentConfig(), arxiv_tools=arxiv_tools, pubmed_tools=pubmed_tools)
    updated = agent.search(session, database)

    assert updated.search_results is not None
    assert len(updated.search_results) == 1
    assert updated.search_results[0].database == database
    assert updated.search_results[0].verified is True


def test_search_skips_excluded_database(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session(databases=["openalex"])
    called = {"search": False}

    def fake_search(*_args: Any, **_kwargs: Any) -> str:
        called["search"] = True
        return json.dumps([])

    monkeypatch.setattr("vioscope.agents.scout.search_semantic_scholar", fake_search)

    agent = build_scout(AgentConfig())
    updated = agent.search(session, "semantic_scholar")

    assert updated is session
    assert called["search"] is False


def test_search_uses_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session(databases=["semantic_scholar"])

    class RecordingBreaker(CircuitBreaker[list[dict[str, Any]]]):
        def __init__(self) -> None:
            super().__init__(backoff_seconds=0.0)
            self.called = False

        def call(self, fn: Any) -> list[dict[str, Any]]:  # type: ignore[override]
            self.called = True
            return fn()

    breaker = RecordingBreaker()
    monkeypatch.setattr(
        "vioscope.agents.scout.search_semantic_scholar",
        lambda *_args, **_kwargs: json.dumps(
            [{"paper_id": "p1", "title": "Paper", "abstract": "Abstract", "authors": ["Alice"]}]
        ),
    )
    monkeypatch.setattr(
        "vioscope.agents.scout.verify_citation",
        lambda *_args, **_kwargs: json.dumps({"verified": False}),
    )

    agent = ScoutAgent(AgentConfig(), circuit_breaker=breaker)
    updated = agent.search(session, "semantic_scholar")

    assert breaker.called is True
    assert updated.search_results is not None
