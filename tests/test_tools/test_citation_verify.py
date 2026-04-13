from __future__ import annotations

import json
from typing import Any

import pytest

from vioscope.tools.citation_verify import (
    _check_url_live,
    _crossref_lookup,
    _semantic_scholar_lookup,
    verify_citation,
)


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


def test_verify_citation_returns_success_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup",
        lambda *_args: {
            "title": "Retinal Vessel Study",
            "abstract": "retinal vessel study",
            "url": "https://example.org/paper",
        },
    )
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._crossref_lookup",
        lambda *_args: {
            "doi": "10.1000/rvs",
            "url": "https://doi.org/10.1000/rvs",
            "abstract": "<jats:p>retinal vessel study</jats:p>",
            "title": "Retinal Vessel Study",
        },
    )
    monkeypatch.setattr("vioscope.tools.citation_verify._check_url_live", lambda *_args: True)

    result = json.loads(verify_citation("Retinal Vessel Study", ["Alice"], 2024))

    assert result["verified"] is True
    assert result["doi"] == "10.1000/rvs"
    assert result["url"] == "https://doi.org/10.1000/rvs"
    assert result["similarity_score"] >= 0.7


def test_semantic_scholar_lookup_prefers_year_and_author_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(*_args: Any, **_kwargs: Any) -> FakeResponse:
        return FakeResponse(
            {
                "data": [
                    {
                        "title": "Retinal Vessel Study",
                        "year": 2023,
                        "authors": [{"name": "Alice"}],
                        "abstract": "older result",
                        "url": "https://example.org/older",
                    },
                    {
                        "title": "Retinal Vessel Study",
                        "year": 2024,
                        "authors": [{"name": "Alice"}, {"name": "Bob"}],
                        "abstract": "best result",
                        "url": "https://example.org/best",
                    },
                ]
            }
        )

    monkeypatch.setattr("vioscope.tools.citation_verify.urlopen", fake_urlopen)

    result = _semantic_scholar_lookup("Retinal Vessel Study", ["Alice"], 2024)

    assert result == {
        "title": "Retinal Vessel Study",
        "authors": ["Alice", "Bob"],
        "year": 2024,
        "abstract": "best result",
        "url": "https://example.org/best",
    }


def test_crossref_lookup_returns_first_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_args: Any, **_kwargs: Any) -> FakeResponse:
        return FakeResponse(
            {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/paper",
                            "URL": "https://doi.org/10.1000/paper",
                            "abstract": "<jats:p>abstract</jats:p>",
                            "title": ["Retinal Vessel Study"],
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("vioscope.tools.citation_verify.urlopen", fake_urlopen)

    result = _crossref_lookup("Retinal Vessel Study")

    assert result == {
        "doi": "10.1000/paper",
        "url": "https://doi.org/10.1000/paper",
        "abstract": "<jats:p>abstract</jats:p>",
        "title": "Retinal Vessel Study",
    }


def test_check_url_live_returns_true_for_2xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify.urlopen",
        lambda *_args, **_kwargs: FakeResponse({}, status=204),
    )

    assert _check_url_live("https://example.org/live") is True


def test_check_url_live_returns_false_for_empty_url() -> None:
    assert _check_url_live("") is False


def test_verify_citation_fails_at_layer_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup", lambda *_args: None
    )

    result = json.loads(verify_citation("Missing Paper", ["Alice"], 2024))

    assert result == {
        "verified": False,
        "failed_layer": 1,
        "reason": "No Semantic Scholar match",
    }


def test_verify_citation_fails_at_layer_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup",
        lambda *_args: {"title": "Paper", "abstract": "paper", "url": "https://example.org/paper"},
    )
    monkeypatch.setattr("vioscope.tools.citation_verify._crossref_lookup", lambda *_args: None)

    result = json.loads(verify_citation("Paper", ["Alice"], 2024))

    assert result == {
        "verified": False,
        "failed_layer": 2,
        "reason": "No CrossRef DOI",
    }


def test_verify_citation_fails_at_layer_three(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup",
        lambda *_args: {"title": "Paper", "abstract": "paper", "url": "https://example.org/paper"},
    )
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._crossref_lookup",
        lambda *_args: {"doi": "10.1000/paper", "url": "https://doi.org/10.1000/paper"},
    )
    monkeypatch.setattr("vioscope.tools.citation_verify._check_url_live", lambda *_args: False)

    result = json.loads(verify_citation("Paper", ["Alice"], 2024))

    assert result == {
        "verified": False,
        "failed_layer": 3,
        "reason": "URL not reachable",
    }


def test_verify_citation_fails_at_layer_four(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup",
        lambda *_args: {
            "title": "Different Title",
            "abstract": "completely unrelated abstract",
            "url": "https://example.org/paper",
        },
    )
    monkeypatch.setattr(
        "vioscope.tools.citation_verify._crossref_lookup",
        lambda *_args: {
            "doi": "10.1000/paper",
            "url": "https://doi.org/10.1000/paper",
            "abstract": "<jats:p>another mismatch</jats:p>",
            "title": "Different Title",
        },
    )
    monkeypatch.setattr("vioscope.tools.citation_verify._check_url_live", lambda *_args: True)

    result = json.loads(verify_citation("Paper", ["Alice"], 2024))

    assert result["verified"] is False
    assert result["failed_layer"] == 4
    assert result["reason"].startswith("Low similarity:")


def test_verify_citation_formats_layer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise TimeoutError("layer 2 timeout")

    monkeypatch.setattr(
        "vioscope.tools.citation_verify._semantic_scholar_lookup",
        lambda *_args: {"title": "Paper", "abstract": "paper", "url": "https://example.org/paper"},
    )
    monkeypatch.setattr("vioscope.tools.citation_verify._crossref_lookup", boom)

    assert (
        verify_citation("Paper", ["Alice"], 2024)
        == "[citation_verify_error] 2: TimeoutError: layer 2 timeout"
    )
