from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, cast

import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv  # type: ignore[import-not-found]
from pydantic import (  # type: ignore[import-not-found]
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from vioscope.core.safe_path import safe_path

DEFAULT_CONFIG_PATH = Path.home() / ".vioscope" / "config.yaml"
PROVIDER_ENV_VARS: Dict[str, str | None] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "google": "GOOGLE_API_KEY",
    "ollama": None,
}
DEFAULT_CONFIG_TEMPLATE = """model:
  provider: anthropic
  model_id: claude-3-haiku
agents: {}
"""


class ConfigError(Exception):
    """Raised when configuration is invalid or incomplete."""


class ModelConfig(BaseModel):
    provider: str
    model_id: str
    api_key: str | None = Field(default=None)

    model_config = ConfigDict(extra="allow")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in PROVIDER_ENV_VARS:
            raise ValueError(
                f"Unsupported provider '{value}'. Allowed: {', '.join(PROVIDER_ENV_VARS)}"
            )
        return value


class AgentConfig(BaseModel):
    model: ModelConfig | None = None

    model_config = ConfigDict(extra="allow")


class VioScopeConfig(BaseModel):
    model: ModelConfig
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    knowledge_base: Dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

    def get_model_for_agent(self, agent_name: str) -> ModelConfig:
        agent = self.agents.get(agent_name)
        if agent and agent.model:
            return agent.model
        return self.model


def load_config(path: Path | str | None = None) -> VioScopeConfig:
    load_dotenv()

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH

    if not config_path.exists():
        if path is None:
            create_default_config(config_path)
        else:
            raise ConfigError(f"Config file not found at {config_path}")

    raw_data = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(raw_data, dict):
        raise ConfigError("Configuration root must be a mapping.")

    data: Dict[str, Any] = raw_data

    try:
        config = cast(VioScopeConfig, VioScopeConfig.model_validate(data))
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc

    validate_api_keys(config)

    return config


def validate_api_keys(config: VioScopeConfig) -> None:
    providers = {config.model.provider}
    for agent in config.agents.values():
        if agent.model:
            providers.add(agent.model.provider)

    for provider in providers:
        env_key = PROVIDER_ENV_VARS.get(provider)
        if env_key is None:
            continue

        value = os.getenv(env_key)
        if value is None:
            raise ConfigError(f"Missing API key for provider '{provider}'. Set {env_key}.")


def create_default_config(path: Path) -> None:
    """Create a default config file at *path* with secure permissions (chmod 600)."""
    base_dir = path.parent
    try:
        safe_path(base_dir, path.name)
    except ValueError as exc:
        raise ConfigError(f"Invalid default config path: {path}") from exc

    base_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TEMPLATE)
    _ensure_permissions(path)


def _ensure_permissions(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError as exc:
        raise ConfigError(f"Failed to set permissions on {path}: {exc}") from exc


__all__ = [
    "AgentConfig",
    "ConfigError",
    "ModelConfig",
    "VioScopeConfig",
    "create_default_config",
    "load_config",
    "validate_api_keys",
]
