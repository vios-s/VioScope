from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml  # type: ignore[import-untyped]

from vioscope.config import ConfigError


@lru_cache(maxsize=None)
def load_agent_defaults(agent_name: str) -> dict[str, Any]:
    resource = files("vioscope.configs.agents").joinpath(f"{agent_name}.yaml")

    try:
        raw = resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing packaged agent config for '{agent_name}'.") from exc

    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Packaged agent config for '{agent_name}' must be a mapping.")
    return data


__all__ = ["load_agent_defaults"]
