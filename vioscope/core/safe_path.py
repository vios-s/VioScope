from __future__ import annotations

from pathlib import Path


def safe_path(base_dir: Path, user_path: str | Path) -> Path:
    """Resolve a user-supplied path within base_dir, rejecting traversal outside it."""

    base_resolved = base_dir.resolve()
    target = Path(user_path)
    resolved = target.resolve() if target.is_absolute() else (base_resolved / target).resolve()

    if not (resolved == base_resolved or resolved.is_relative_to(base_resolved)):
        raise ValueError(f"path '{user_path}' escapes base directory {base_resolved}")

    return resolved


__all__ = ["safe_path"]
