from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from vioscope.kb.session_store import list_checkpoints, load_checkpoint, save_checkpoint
from vioscope.schemas import PipelineConfig, PipelineSession


def make_session(session_id: str = "session-1") -> PipelineSession:
    return PipelineSession(
        session_id=session_id,
        research_question="retinal vessel study",
        created_at=datetime.now(timezone.utc),
        config=PipelineConfig(),
        stage_reached=5,
    )


def test_save_checkpoint_writes_atomically_and_loads_round_trip(tmp_path: Path) -> None:
    session = make_session()

    save_checkpoint(session, tmp_path)

    checkpoint_path = tmp_path / "session-1.json"
    assert checkpoint_path.exists()
    assert not (tmp_path / "session-1.json.tmp").exists()
    loaded = load_checkpoint("session-1", tmp_path)
    assert loaded == session


def test_save_checkpoint_replaces_stale_tmp_file(tmp_path: Path) -> None:
    session = make_session()
    stale_tmp = tmp_path / "session-1.json.tmp"
    stale_tmp.parent.mkdir(parents=True, exist_ok=True)
    stale_tmp.write_text("stale")

    save_checkpoint(session, tmp_path)

    assert not stale_tmp.exists()
    assert (tmp_path / "session-1.json").exists()


def test_load_checkpoint_raises_for_missing_session(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
        load_checkpoint("missing", tmp_path)


def test_load_checkpoint_raises_validation_error_for_corrupt_json(tmp_path: Path) -> None:
    broken = tmp_path / "session-1.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("{not json")

    with pytest.raises(ValidationError):
        load_checkpoint("session-1", tmp_path)


def test_list_checkpoints_returns_session_ids(tmp_path: Path) -> None:
    save_checkpoint(make_session("session-a"), tmp_path)
    save_checkpoint(make_session("session-b"), tmp_path)

    assert list_checkpoints(tmp_path) == ["session-a", "session-b"]
