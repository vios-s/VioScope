from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:  # pragma: no cover - optional dependency
    from agno import tool  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when agno is unavailable

    def tool(func: Callable[..., Any] | None = None, **_kwargs: Any):  # type: ignore
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator(func) if func else decorator


API_URL = "https://api.openalex.org/works"
TIMEOUT = 180
USER_AGENT = "vioscope/0.1.0 (mailto=vioscope@vios.lab)"
MAILTO = "vioscope@vios.lab"


def _build_request(query: str, limit: int) -> Request:
    bounded_limit = max(1, limit)
    params = {
        "search": query,
        "per-page": bounded_limit,
        "mailto": MAILTO,
    }
    full_url = f"{API_URL}?{urlencode(params)}"
    full_url = full_url.replace("%40", "@")
    request = Request(full_url)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("User-agent", USER_AGENT)
    request.headers["User-Agent"] = USER_AGENT
    return request


def _reconstruct_abstract(abstract_idx: Any) -> str:
    if not isinstance(abstract_idx, dict):
        return ""

    positions: List[Tuple[int, str]] = []
    for word, idxs in abstract_idx.items():
        if not isinstance(idxs, list):
            continue
        for pos in idxs:
            if isinstance(pos, int):
                positions.append((pos, word))

    if not positions:
        return ""

    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    authors: List[str] = []
    for entry in record.get("authorships", []) or []:
        if not isinstance(entry, dict):
            continue
        author = entry.get("author")
        if isinstance(author, dict):
            name = author.get("display_name") or author.get("orcid")
            if name:
                authors.append(name)

    abstract = _reconstruct_abstract(record.get("abstract_inverted_index"))
    open_access_url = (
        (record.get("open_access") or {}).get("oa_url")
        or (record.get("best_oa_location") or {}).get("url")
        or (record.get("primary_location") or {}).get("landing_page_url")
    )

    return {
        "title": record.get("title", ""),
        "authors": authors,
        "year": record.get("publication_year") or record.get("year"),
        "abstract": abstract,
        "doi": record.get("doi", ""),
        "open_access_url": open_access_url,
    }


@tool
def search_openalex(query: str, limit: int = 20) -> str:
    """Search OpenAlex for open-access scholarly works matching the query."""

    try:
        request = _build_request(query, limit)
        with urlopen(request, timeout=TIMEOUT) as response:  # type: ignore[arg-type]
            status = getattr(response, "status", None)
            if status is not None and status != 200:
                return f"[openalex_error] HTTPError: http {status}"
            raw = response.read()

        data = json.loads(raw)
        results = data.get("results", []) if isinstance(data, dict) else []
        normalized = [_normalize_record(item) for item in results if isinstance(item, dict)]
        return json.dumps(normalized)
    except Exception as exc:  # pragma: no cover - exercised via tests
        return f"[openalex_error] {exc.__class__.__name__}: {exc}"


__all__ = ["search_openalex"]
