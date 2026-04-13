from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:  # pragma: no cover - optional dependency
    from agno import tool  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when agno is unavailable

    def tool(func: Callable[..., Any] | None = None, **_kwargs: Any):  # type: ignore
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator(func) if func else decorator


SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_API = "https://api.crossref.org/works"
USER_AGENT = "vioscope/0.1.0"
TIMEOUT_LOOKUP = 30
TIMEOUT_HEAD = 10


def _semantic_scholar_lookup(
    title: str, authors: List[str], year: int
) -> Optional[Dict[str, Any]]:
    params = {
        "query": title,
        "limit": 5,
        "year": year,
        "fields": "paperId,title,abstract,authors.name,year,url",
    }
    full_url = f"{SEMANTIC_SCHOLAR_API}?{urlencode(params)}"
    request = Request(full_url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=TIMEOUT_LOOKUP) as response:  # type: ignore[arg-type]
        if getattr(response, "status", None) not in (None, 200):
            return None
        data = json.loads(response.read())

    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        return None

    # Basic disambiguation: prefer same year and overlapping authors if provided
    def score(item: Dict[str, Any]) -> Tuple[int, int]:
        item_year = item.get("year")
        year_match = 1 if item_year == year else 0
        item_authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        overlap = (
            len(set(a.lower() for a in item_authors) & set(a.lower() for a in authors))
            if authors
            else 0
        )
        return (year_match, overlap)

    best = max(items, key=score)
    return {
        "title": best.get("title", ""),
        "authors": [a.get("name", "") for a in best.get("authors", []) if a.get("name")],
        "year": best.get("year"),
        "abstract": best.get("abstract", ""),
        "url": best.get("url"),
    }


def _crossref_lookup(title: str) -> Optional[Dict[str, Any]]:
    params = {"query.title": title, "rows": 3}
    full_url = f"{CROSSREF_API}?{urlencode(params)}"
    request = Request(full_url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=TIMEOUT_LOOKUP) as response:  # type: ignore[arg-type]
        if getattr(response, "status", None) not in (None, 200):
            return None
        data = json.loads(response.read())

    msg = data.get("message", {}) if isinstance(data, dict) else {}
    items = msg.get("items", []) if isinstance(msg, dict) else []
    if not items:
        return None

    best = items[0]
    doi = best.get("DOI") or best.get("doi")
    url = best.get("URL") or (best.get("link", [{}])[0].get("URL") if best.get("link") else None)
    abstract = best.get("abstract", "")
    return {"doi": doi, "url": url, "abstract": abstract}


def _check_url_live(url: str) -> bool:
    if not url:
        return False
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    with urlopen(request, timeout=TIMEOUT_HEAD) as response:  # type: ignore[arg-type]
        status = getattr(response, "status", None)
        if status is None:
            return True
        return bool(200 <= status < 400)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def _success_payload(doi: Optional[str], url: Optional[str], similarity: float) -> str:
    return json.dumps(
        {
            "verified": True,
            "doi": doi or "",
            "url": url or "",
            "similarity_score": similarity,
        }
    )


def _failure_payload(layer: int, reason: str) -> str:
    return json.dumps({"verified": False, "failed_layer": layer, "reason": reason})


@tool
def verify_citation(title: str, authors: List[str], year: int) -> str:
    """Run four-layer citation verification for a candidate citation."""

    # Layer 1: Semantic Scholar
    try:
        s2 = _semantic_scholar_lookup(title, authors, year)
    except Exception as exc:  # pragma: no cover - tested via error path
        return f"[citation_verify_error] 1: {exc.__class__.__name__}: {exc}"

    if not s2:
        return _failure_payload(1, "No Semantic Scholar match")

    # Layer 2: CrossRef
    try:
        cr = _crossref_lookup(title)
    except Exception as exc:  # pragma: no cover - tested via error path
        return f"[citation_verify_error] 2: {exc.__class__.__name__}: {exc}"

    if not cr or not cr.get("doi"):
        return _failure_payload(2, "No CrossRef DOI")

    doi = cr.get("doi")
    target_url = (
        cr.get("url") or (f"https://doi.org/{doi}" if doi else s2.get("url")) or s2.get("url")
    )
    target_url = target_url or ""

    # Layer 3: URL liveness
    try:
        live = _check_url_live(target_url)
    except Exception as exc:  # pragma: no cover - tested via error path
        return f"[citation_verify_error] 3: {exc.__class__.__name__}: {exc}"

    if not live:
        return _failure_payload(3, "URL not reachable")

    # Layer 4: abstract similarity
    abstract_source = s2.get("abstract") or cr.get("abstract", "")
    sim = _similarity(title.lower(), abstract_source.lower())
    if sim <= 0.7:
        return _failure_payload(4, f"Low similarity: {sim:.2f}")

    return _success_payload(doi, target_url, sim)


__all__ = ["verify_citation"]
