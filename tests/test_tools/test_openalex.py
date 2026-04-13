from __future__ import annotations

import json
from typing import Any

import pytest

from vioscope.tools.openalex import search_openalex


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


def test_search_openalex_returns_normalized_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "results": [
                    {
                        "title": "OpenAlex Paper",
                        "publication_year": 2022,
                        "authorships": [{"author": {"display_name": "Alice"}}],
                        "abstract_inverted_index": {"retinal": [0], "study": [1]},
                        "doi": "10.1000/openalex",
                        "open_access": {"oa_url": "https://example.org/oa"},
                    }
                ]
            }
        )

    monkeypatch.setattr("vioscope.tools.openalex.urlopen", fake_urlopen)

    result = json.loads(search_openalex("retinal", limit=5))

    assert result == [
        {
            "title": "OpenAlex Paper",
            "authors": ["Alice"],
            "year": 2022,
            "abstract": "retinal study",
            "abstract_inverted_index": "retinal study",
            "doi": "10.1000/openalex",
            "open_access_url": "https://example.org/oa",
        }
    ]
    assert captured["timeout"] == 180
    assert "mailto=vioscope@vios.lab" in captured["request"].full_url


def test_search_openalex_returns_formatted_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("api down")

    monkeypatch.setattr("vioscope.tools.openalex.urlopen", boom)

    assert search_openalex("retinal") == "[openalex_error] RuntimeError: api down"
