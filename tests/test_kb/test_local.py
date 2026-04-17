from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from vioscope.kb.local import KBRecord, LocalKB


class FakeDocument:
    def __init__(self, content: str, meta_data: dict[str, Any], name: str = "") -> None:
        self.content = content
        self.meta_data = meta_data
        self.name = name


def test_write_record_and_read_record_round_trip(tmp_path: Path) -> None:
    kb = LocalKB(tmp_path / "kb")

    path = kb.write_record(
        "literature",
        "session-1",
        "Literature body",
        {"research_question": "retinal vessel study", "paper_count": 3},
    )

    assert path.exists()
    assert path.parent.name == "literature"
    assert kb.read_record("literature", path.stem) == "Literature body"


def test_write_record_supports_tex_extension_for_papers(tmp_path: Path) -> None:
    kb = LocalKB(tmp_path / "kb")

    path = kb.write_record(
        "papers",
        "session-2",
        "\\section{Results}",
        {"template": "miccai"},
        extension=".tex",
    )

    assert path.suffix == ".tex"
    assert path.parent.name == "papers"


def test_list_records_returns_frontmatter_metadata(tmp_path: Path) -> None:
    kb = LocalKB(tmp_path / "kb")
    kb.write_record(
        "sessions",
        "session-1",
        "Session body",
        {"research_question": "retinal vessel study", "source_record_ids": ["lit-1"]},
    )
    kb.write_record(
        "hypotheses",
        "session-2",
        "Hypothesis body",
        {"research_question": "segmentation"},
    )

    records = kb.list_records()

    assert len(records) == 2
    assert {record["record_type"] for record in records} == {"sessions", "hypotheses"}
    assert records[0]["content"]


def test_invalid_record_type_is_rejected(tmp_path: Path) -> None:
    kb = LocalKB(tmp_path / "kb")

    with pytest.raises(ValueError, match="Unsupported record type"):
        kb.write_record("notes", "session-1", "Body", {})


def test_search_returns_typed_kb_records_from_knowledge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kb = LocalKB(tmp_path / "kb")
    kb.write_record(
        "literature",
        "session-1",
        "Literature body",
        {"research_question": "retinal vessel study", "source_record_ids": ["paper-1"]},
    )

    class FakeKnowledge:
        def search(self, query: str, max_results: int) -> list[FakeDocument]:
            return [
                FakeDocument(
                    content="retinal vessel study snippet",
                    meta_data={
                        "record_id": "record-1",
                        "record_type": "literature",
                        "session_id": "session-1",
                        "source_path": str(tmp_path / "kb" / "literature" / "record-1.md"),
                        "source_record_ids": ["paper-1"],
                        "created_at": "2026-04-13T00:00:00Z",
                        "research_question": "retinal vessel study",
                    },
                )
            ]

    monkeypatch.setattr(
        LocalKB, "get_knowledge_base", lambda self, record_types=None: FakeKnowledge()
    )
    monkeypatch.setenv("VIOSCOPE_ENABLE_LANCEDB", "1")

    results = kb.search("retinal")

    assert results == [
        KBRecord(
            record_id="record-1",
            record_type="literature",
            session_id="session-1",
            content_snippet="retinal vessel study snippet",
            source_path=str(tmp_path / "kb" / "literature" / "record-1.md"),
            source_record_ids=["paper-1"],
            created_at="2026-04-13T00:00:00Z",
            research_question="retinal vessel study",
        )
    ]


def test_search_falls_back_to_keyword_search_when_lancedb_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kb = LocalKB(tmp_path / "kb")
    kb.write_record(
        "sessions",
        "session-1",
        "Session summary about retinal vessel segmentation",
        {"research_question": "retinal vessel study"},
    )

    def boom(self: LocalKB, record_types: tuple[str, ...] | None = None) -> Any:
        raise RuntimeError("LanceDB knowledge support is unavailable. Install lancedb.")

    monkeypatch.setattr(LocalKB, "get_knowledge_base", boom)

    results = kb.search("retinal", record_types=("sessions",))

    assert len(results) == 1
    assert results[0].record_type == "sessions"
