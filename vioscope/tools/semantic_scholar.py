from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "vioscope/0.1.0"
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_LIMIT = 50
TIMEOUT = 10


def _build_request(query: str, limit: int) -> Request:
    bounded_limit = max(1, min(limit, MAX_LIMIT))
    params = {
        "query": query,
        "limit": bounded_limit,
        "fields": "paperId,title,abstract,authors.name,year,venue,url,openAccessPdf",
    }
    full_url = f"{API_URL}?{urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    return Request(full_url, headers=headers)


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    authors: List[str] = [a.get("name", "") for a in record.get("authors", []) if a.get("name")]
    url = record.get("url") or (record.get("openAccessPdf") or {}).get("url")

    return {
        "paper_id": record.get("paperId", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "authors": authors,
        "year": record.get("year"),
        "venue": record.get("venue"),
        "url": url,
        "source": "semantic_scholar",
    }


def search_semantic_scholar(query: str, limit: int = 20) -> str:
    """Search Semantic Scholar and return normalized results as JSON string.

    Returns "error: <detail>" on failure; does not raise.
    """

    try:
        request = _build_request(query, limit)
        with urlopen(request, timeout=TIMEOUT) as response:  # type: ignore[arg-type]
            status = getattr(response, "status", None)
            if status is not None and status != 200:
                return f"error: http {status}"
            raw = response.read()

        data = json.loads(raw)
        items = data.get("data", []) if isinstance(data, dict) else []
        normalized = [_normalize_record(item) for item in items]
        return json.dumps(normalized)
    except Exception as exc:  # pragma: no cover - exercised via tests
        return f"error: {exc}"


__all__ = ["search_semantic_scholar"]
