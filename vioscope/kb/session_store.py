from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from vioscope.core.safe_path import safe_path
from vioscope.schemas.pipeline import PipelineSession

DEFAULT_SESSIONS_DIR = Path.home() / ".vioscope" / "sessions"


def save_checkpoint(session: PipelineSession, sessions_dir: Path | str | None = None) -> None:
    resolved_dir = _resolve_sessions_dir(sessions_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    target = safe_path(resolved_dir, f"{session.session_id}.json")
    temp = safe_path(resolved_dir, f"{session.session_id}.json.tmp")
    temp.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    temp.replace(target)


def load_checkpoint(
    session_id: str,
    sessions_dir: Path | str | None = None,
) -> PipelineSession:
    resolved_dir = _resolve_sessions_dir(sessions_dir)
    target = safe_path(resolved_dir, f"{session_id}.json")
    if not target.exists():
        raise FileNotFoundError(f"Checkpoint not found for session '{session_id}'.")

    try:
        return PipelineSession.model_validate_json(target.read_text(encoding="utf-8"))
    except ValidationError:
        raise


def list_checkpoints(sessions_dir: Path | str | None = None) -> list[str]:
    resolved_dir = _resolve_sessions_dir(sessions_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    return sorted(path.stem for path in resolved_dir.glob("*.json") if path.is_file())


def _resolve_sessions_dir(sessions_dir: Path | str | None) -> Path:
    candidate = Path(sessions_dir) if sessions_dir is not None else DEFAULT_SESSIONS_DIR
    base_dir = candidate.parent if candidate.is_absolute() else Path.cwd()
    return safe_path(base_dir, candidate)


__all__ = ["DEFAULT_SESSIONS_DIR", "list_checkpoints", "load_checkpoint", "save_checkpoint"]
