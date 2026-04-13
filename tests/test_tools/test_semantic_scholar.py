from __future__ import annotations

import json
from typing import Any

import pytest

from vioscope.tools.semantic_scholar import get_paper_details, search_semantic_scholar


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_search_semantic_scholar_returns_normalized_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "data": [
                    {
                        "paperId": "p1",
                        "title": "Paper 1",
                        "abstract": "Abstract 1",
                        "authors": [{"name": "Alice"}],
                        "year": 2024,
                        "venue": "Nature",
                        "url": "https://example.org/p1",
                        "externalIds": {"DOI": "10.1000/p1"},
                    }
                ]
            }
        )

    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "secret")
    monkeypatch.setattr("vioscope.tools.semantic_scholar.urlopen", fake_urlopen)

    result = json.loads(search_semantic_scholar("retinal", limit=99))

    assert result == [
        {
            "paper_id": "p1",
            "title": "Paper 1",
            "abstract": "Abstract 1",
            "authors": ["Alice"],
            "year": 2024,
            "venue": "Nature",
            "url": "https://example.org/p1",
            "externalIds": {"DOI": "10.1000/p1"},
            "source": "semantic_scholar",
        }
    ]
    assert captured["timeout"] == 180
    assert "limit=50" in captured["request"].full_url
    assert ("X-api-key", "secret") in captured["request"].header_items()


def test_search_semantic_scholar_returns_formatted_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise TimeoutError("too slow")

    monkeypatch.setattr("vioscope.tools.semantic_scholar.urlopen", boom)

    assert search_semantic_scholar("retinal") == "[semantic_scholar_error] TimeoutError: too slow"


def test_get_paper_details_returns_single_normalized_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "paperId": "CorpusID:1",
                "title": "Detailed Paper",
                "abstract": "Detailed abstract",
                "authors": [{"name": "Bob"}],
                "year": 2023,
                "venue": "ICLR",
                "externalIds": {"DOI": "10.1000/detail"},
                "openAccessPdf": {"url": "https://example.org/detail.pdf"},
            }
        )

    monkeypatch.setattr("vioscope.tools.semantic_scholar.urlopen", fake_urlopen)

    result = json.loads(get_paper_details("10.1000/detail"))

    assert result == {
        "paper_id": "CorpusID:1",
        "title": "Detailed Paper",
        "abstract": "Detailed abstract",
        "authors": ["Bob"],
        "year": 2023,
        "venue": "ICLR",
        "url": "https://example.org/detail.pdf",
        "externalIds": {"DOI": "10.1000/detail"},
        "source": "semantic_scholar",
    }
    assert captured["timeout"] == 180
    assert "fields=" in captured["request"].full_url
