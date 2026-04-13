from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:  # pragma: no cover - optional dependency
    from agno import tool  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when agno is unavailable

    def tool(func: Callable[..., Any] | None = None, **_kwargs: Any):  # type: ignore
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator(func) if func else decorator


USER_AGENT = "vioscope/0.1.0"
SEARCH_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
DETAILS_API_URL = "https://api.semanticscholar.org/graph/v1/paper"
MAX_LIMIT = 50
TIMEOUT = 180
SEARCH_FIELDS = "paperId,title,abstract,authors.name,year,venue,url,externalIds,openAccessPdf"
DETAIL_FIELDS = "paperId,title,abstract,authors.name,year,venue,url,externalIds,openAccessPdf"


def _api_headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _build_search_request(query: str, limit: int) -> Request:
    bounded_limit = max(1, min(limit, MAX_LIMIT))
    params = {
        "query": query,
        "limit": bounded_limit,
        "fields": SEARCH_FIELDS,
    }
    full_url = f"{SEARCH_API_URL}?{urlencode(params)}"
    return Request(full_url, headers=_api_headers())


def _build_details_request(paper_id: str) -> Request:
    encoded_id = paper_id.replace("/", "%2F")
    full_url = f"{DETAILS_API_URL}/{encoded_id}?{urlencode({'fields': DETAIL_FIELDS})}"
    return Request(full_url, headers=_api_headers())


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    authors = [
        author.get("name", "")
        for author in record.get("authors", []) or []
        if isinstance(author, dict) and author.get("name")
    ]
    open_access_url = (record.get("openAccessPdf") or {}).get("url")

    return {
        "paper_id": record.get("paperId", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "authors": authors,
        "year": record.get("year"),
        "venue": record.get("venue"),
        "url": record.get("url") or open_access_url,
        "externalIds": record.get("externalIds") or {},
        "source": "semantic_scholar",
    }


def _error_payload(exc: Exception) -> str:
    return f"[semantic_scholar_error] {exc.__class__.__name__}: {exc}"


def _read_json(request: Request) -> Any:
    with urlopen(request, timeout=TIMEOUT) as response:  # type: ignore[arg-type]
        status = getattr(response, "status", None)
        if status is not None and status != 200:
            raise RuntimeError(f"http {status}")
        return json.loads(response.read())


@tool
def search_semantic_scholar(query: str, limit: int = 20) -> str:
    """Search Semantic Scholar for academic papers matching the query."""

    try:
        data = _read_json(_build_search_request(query, limit))
        items = data.get("data", []) if isinstance(data, dict) else []
        normalized = [_normalize_record(item) for item in items if isinstance(item, dict)]
        return json.dumps(normalized)
    except Exception as exc:  # pragma: no cover - exercised via tests
        return _error_payload(exc)


@tool
def get_paper_details(paper_id: str) -> str:
    """Fetch a single Semantic Scholar paper by paper id or DOI."""

    try:
        data = _read_json(_build_details_request(paper_id))
        if not isinstance(data, dict):
            raise RuntimeError("invalid response payload")
        return json.dumps(_normalize_record(data))
    except Exception as exc:  # pragma: no cover - exercised via tests
        return _error_payload(exc)


__all__ = ["get_paper_details", "search_semantic_scholar"]
