from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent  # type: ignore[import-not-found]
    from agno.tools.arxiv import ArxivTools  # type: ignore[import-not-found]
    from agno.tools.pubmed import PubmedTools  # type: ignore[import-not-found]
else:  # pragma: no cover - runtime fallback when agno is unavailable

    class AgnoAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ArxivTools:
        def search(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("ArxivTools unavailable")

    class PubmedTools:
        def search(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("PubmedTools unavailable")

    try:
        from agno.agent import Agent as _RuntimeAgnoAgent  # type: ignore[import-not-found]
        from agno.tools.arxiv import (
            ArxivTools as _RuntimeArxivTools,  # type: ignore[import-not-found]
        )
        from agno.tools.pubmed import (
            PubmedTools as _RuntimePubmedTools,  # type: ignore[import-not-found]
        )
    except Exception:
        pass
    else:
        AgnoAgent = _RuntimeAgnoAgent
        ArxivTools = _RuntimeArxivTools
        PubmedTools = _RuntimePubmedTools

from vioscope.agents._models import build_agno_model
from vioscope.config import AgentConfig, ModelConfig, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas.pipeline import PipelineSession
from vioscope.schemas.research import Paper
from vioscope.tools import search_openalex, search_semantic_scholar, verify_citation


class ScoutDefaults(BaseModel):
    name: str
    model: ModelConfig
    timeout_seconds: int
    instructions: list[str]

    model_config = ConfigDict(extra="forbid")


@lru_cache(maxsize=1)
def load_scout_defaults() -> ScoutDefaults:
    return ScoutDefaults.model_validate(load_agent_defaults("scout"))


def _resolve_model_config(cfg: AgentConfig | VioScopeConfig) -> ModelConfig:
    defaults = load_scout_defaults()
    if isinstance(cfg, VioScopeConfig):
        return cfg.get_model_for_agent("scout", default_model=defaults.model)
    if cfg.model:
        return defaults.model.model_copy(update=cfg.model.model_dump(exclude_none=True))
    return defaults.model


def _safe_json_loads(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return None
    return payload


def _normalize_record(record: dict[str, Any], database: str) -> Paper:
    paper_id = str(
        record.get("paper_id")
        or record.get("paperId")
        or record.get("id")
        or record.get("uid")
        or record.get("doi")
        or record.get("title")
        or ""
    )
    title = record.get("title") or ""
    abstract = (
        record.get("abstract")
        or record.get("summary")
        or record.get("abstract_inverted_index")
        or ""
    )
    authors = record.get("authors") or record.get("author") or []
    if not isinstance(authors, list):
        authors = []
    year = record.get("year")
    if isinstance(year, str) and year.isdigit():
        year = int(year)

    url = (
        record.get("url")
        or record.get("open_access_url")
        or record.get("openAccessPdf", {}).get("url")
        or record.get("landing_page_url")
    )
    venue = record.get("venue") or record.get("journal")
    return Paper(
        paper_id=paper_id,
        title=title,
        abstract=abstract if isinstance(abstract, str) else "",
        url=url if isinstance(url, str) else None,
        source=record.get("source") or database,
        database=database,
        authors=[author for author in authors if isinstance(author, str)],
        year=year if isinstance(year, int) else None,
        venue=venue if isinstance(venue, str) else None,
    )


def _apply_verification(paper: Paper) -> Paper:
    try:
        verification = verify_citation(paper.title, paper.authors, paper.year or 0)
        data = _safe_json_loads(verification) or {}
        verified = bool(data.get("verified"))
    except Exception:
        verified = False

    return paper.model_copy(update={"verified": verified})


def _call_tool(func: Callable[..., Any], query: str, limit: int) -> list[dict[str, Any]]:
    try:
        result = func(query=query, limit=limit)  # type: ignore[arg-type]
    except TypeError:
        result = func(query, limit)  # type: ignore[misc]
    except Exception:
        return []

    data = _safe_json_loads(result)
    return data if isinstance(data, list) else []


def _call_tool_list(func: Callable[..., Any], query: str, limit: int) -> list[dict[str, Any]]:
    try:
        result = func(query=query, max_results=limit)
    except TypeError:
        try:
            result = func(query=query)
        except Exception:
            result = func(query, limit)  # type: ignore[misc]
    except Exception:
        return []

    data = _safe_json_loads(result)
    return data if isinstance(data, list) else []


class ScoutAgent(AgnoAgent):
    def __init__(
        self,
        cfg: AgentConfig | VioScopeConfig,
        *,
        arxiv_tools: ArxivTools | None = None,
        pubmed_tools: PubmedTools | None = None,
        circuit_breaker: CircuitBreaker[list[dict[str, Any]]] | None = None,
    ) -> None:
        defaults = load_scout_defaults()
        resolved_model = _resolve_model_config(cfg)
        model = build_agno_model(resolved_model, defaults.timeout_seconds)
        resolved_arxiv_tools = arxiv_tools or ArxivTools()
        resolved_pubmed_tools = pubmed_tools or PubmedTools()
        tool_list = [
            search_semantic_scholar,
            search_openalex,
            verify_citation,
            resolved_arxiv_tools,
            resolved_pubmed_tools,
        ]
        self._init_error: Exception | None = None
        try:
            super().__init__(
                name=defaults.name,
                model=model,
                instructions=defaults.instructions,
                tools=tool_list,
            )
        except Exception as exc:  # pragma: no cover - depends on optional provider SDKs
            self._init_error = exc
            self.model = model
            self.instructions = defaults.instructions
            self.name = defaults.name
            self.tools = tool_list

        self.cfg = cfg
        self.resolved_model = resolved_model
        self.timeout_seconds = defaults.timeout_seconds
        self.arxiv_tools = resolved_arxiv_tools
        self.pubmed_tools = resolved_pubmed_tools
        self.circuit_breaker = circuit_breaker or CircuitBreaker(backoff_seconds=0.0)

    def _query_database(self, database: str, query: str, limit: int) -> list[dict[str, Any]]:
        if database == "semantic_scholar":
            return _call_tool(search_semantic_scholar, query, limit)
        if database == "openalex":
            return _call_tool(search_openalex, query, limit)
        if database == "arxiv":
            return _call_tool_list(self.arxiv_tools.search, query, limit)  # type: ignore[attr-defined]
        if database == "pubmed":
            return _call_tool_list(self.pubmed_tools.search, query, limit)  # type: ignore[attr-defined]
        return []

    def search(self, session: PipelineSession, database: str) -> PipelineSession:
        allowed = session.config.databases or []
        if database not in allowed:
            return session

        query = (
            " ".join(session.scope.search_axes)
            if session.scope and session.scope.search_axes
            else session.research_question
        )
        limit = max(1, session.config.max_papers)

        raw_records = self.circuit_breaker.call(
            lambda: self._query_database(database, query, limit)
        )
        if not raw_records:
            return session

        papers = [_normalize_record(rec, database) for rec in raw_records if isinstance(rec, dict)]
        verified = [_apply_verification(paper) for paper in papers]
        updated_results = (session.search_results or []) + verified
        return session.model_copy(update={"search_results": updated_results})


def build_scout(cfg: AgentConfig | VioScopeConfig) -> ScoutAgent:
    """Construct the Scout agent configured with database tools and citation verification."""

    return ScoutAgent(cfg=cfg)


__all__ = [
    "ScoutAgent",
    "ScoutDefaults",
    "build_scout",
    "load_scout_defaults",
]
