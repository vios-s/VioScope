from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

try:  # pragma: no cover - optional dependency
    from agno.agent import Agent  # type: ignore[import-not-found]
    from agno.tools.arxiv import ArxivTools  # type: ignore[import-not-found]
    from agno.tools.pubmed import PubmedTools  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback when agno is unavailable

    class _FallbackAgent:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def search(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
            raise NotImplementedError("Agent.search unavailable")

    class _FallbackArxivTools:  # type: ignore[override]
        def search(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
            raise RuntimeError("ArxivTools unavailable")

    class _FallbackPubmedTools:  # type: ignore[override]
        def search(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
            raise RuntimeError("PubmedTools unavailable")

    Agent = _FallbackAgent  # type: ignore[assignment]
    ArxivTools = _FallbackArxivTools  # type: ignore[assignment]
    PubmedTools = _FallbackPubmedTools  # type: ignore[assignment]

from vioscope.config import AgentConfig
from vioscope.schemas.pipeline import PipelineSession
from vioscope.schemas.research import Paper
from vioscope.tools import search_openalex, search_semantic_scholar, verify_citation

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def _safe_json_loads(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return None
    return payload


def _normalize_record(record: Dict[str, Any], database: str) -> Paper:
    paper_id = str(
        record.get("paper_id")
        or record.get("id")
        or record.get("uid")
        or record.get("doi")
        or record.get("title")
        or ""
    )
    title = record.get("title") or ""
    abstract = record.get("abstract") or record.get("summary") or ""
    authors = record.get("authors") or record.get("author") or []
    if not isinstance(authors, list):
        authors = []
    year = record.get("year")
    if isinstance(year, str) and year.isdigit():
        year = int(year)

    url = record.get("url") or record.get("open_access_url") or record.get("landing_page_url")
    venue = record.get("venue") or record.get("journal")
    return Paper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        url=url,
        source=record.get("source") or database,
        database=database,
        authors=[a for a in authors if isinstance(a, str)],
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


def _call_tool(func: Callable[..., Any], query: str, limit: int) -> List[Dict[str, Any]]:
    try:
        result = func(query=query, limit=limit)  # type: ignore[arg-type]
    except TypeError:
        result = func(query, limit)  # type: ignore[misc]
    except Exception:
        return []

    data = _safe_json_loads(result)
    return data if isinstance(data, list) else []


def _call_tool_list(func: Callable[..., Any], query: str, limit: int) -> List[Dict[str, Any]]:
    # agno arxiv/pubmed may not accept limit; allow simple call
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


class ScoutAgent(Agent):
    def __init__(
        self,
        cfg: AgentConfig,
        arxiv_tools: ArxivTools,
        pubmed_tools: PubmedTools,
    ) -> None:
        super().__init__(model=cfg.model.model_id if cfg.model else DEFAULT_MODEL)
        self.cfg = cfg
        self.arxiv_tools = arxiv_tools
        self.pubmed_tools = pubmed_tools

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

        if database == "semantic_scholar":
            raw_records = _call_tool(search_semantic_scholar, query, limit)
        elif database == "openalex":
            raw_records = _call_tool(search_openalex, query, limit)
        elif database == "arxiv":
            raw_records = _call_tool_list(self.arxiv_tools.search, query, limit)
        elif database == "pubmed":
            raw_records = _call_tool_list(self.pubmed_tools.search, query, limit)
        else:
            raw_records = []

        if not raw_records:
            return session

        papers = [_normalize_record(rec, database) for rec in raw_records if isinstance(rec, dict)]
        verified = [_apply_verification(p) for p in papers]
        updated_results = (session.search_results or []) + verified
        return session.model_copy(update={"search_results": updated_results})


def build_scout(cfg: AgentConfig) -> Agent:
    """Construct the Scout agent configured with database tools and citation verification."""

    arxiv_tools = ArxivTools()
    pubmed_tools = PubmedTools()
    return ScoutAgent(cfg=cfg, arxiv_tools=arxiv_tools, pubmed_tools=pubmed_tools)


__all__ = ["build_scout", "ScoutAgent"]
