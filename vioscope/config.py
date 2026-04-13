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
PROJECT_CONFIG_DIR = ".vioscope"
PROJECT_CONFIG_FILENAME = "config.yaml"
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
    temperature: float | None = Field(default=None)
    max_tokens: int | None = Field(default=None, ge=1)

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
    model: ModelConfig | ModelOverride | None = None

    model_config = ConfigDict(extra="allow")


class ModelOverride(BaseModel):
    provider: str | None = None
    model_id: str | None = None
    api_key: str | None = Field(default=None)
    temperature: float | None = Field(default=None)
    max_tokens: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(extra="allow")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in PROVIDER_ENV_VARS:
            raise ValueError(
                f"Unsupported provider '{value}'. Allowed: {', '.join(PROVIDER_ENV_VARS)}"
            )
        return value


class VioScopeConfig(BaseModel):
    model: ModelConfig
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    knowledge_base: Dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

    def get_model_for_agent(
        self,
        agent_name: str,
        default_model: ModelConfig | None = None,
    ) -> ModelConfig:
        resolved = default_model or self.model
        resolved = _merge_model_config(resolved, self.model)
        agent = self.agents.get(agent_name)
        if agent and agent.model:
            resolved = _merge_model_config(resolved, agent.model)
        return resolved


def load_config(path: Path | str | None = None) -> VioScopeConfig:
    load_dotenv()
    config_paths = _resolve_config_paths(path)
    data: Dict[str, Any] = {}

    for config_path in config_paths:
        raw_data = yaml.safe_load(config_path.read_text()) or {}
        if not isinstance(raw_data, dict):
            raise ConfigError(f"Configuration root must be a mapping: {config_path}")
        data = _merge_mappings(data, raw_data)

    try:
        config = cast(VioScopeConfig, VioScopeConfig.model_validate(data))
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc

    _validate_precedence(config)
    validate_api_keys(config)

    return config


def validate_api_keys(config: VioScopeConfig) -> None:
    providers = {config.model.provider}
    for agent in config.agents.values():
        provider = _model_provider(agent.model)
        if provider:
            providers.add(provider)

    for provider in providers:
        env_key = PROVIDER_ENV_VARS.get(provider)
        if env_key is None:
            continue

        value = os.getenv(env_key)
        if not value:
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


def _validate_precedence(config: VioScopeConfig) -> None:
    if config.model is None:
        raise ConfigError("Global model configuration is required.")


def _resolve_config_paths(path: Path | str | None = None) -> list[Path]:
    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found at {config_path}")
        return [config_path]

    project_config = _find_project_config_path()
    home_config = DEFAULT_CONFIG_PATH
    config_paths: list[Path] = []

    if project_config is not None and project_config.exists():
        config_paths.append(project_config)

    if home_config.exists():
        config_paths.append(home_config)

    if config_paths:
        return config_paths

    create_default_config(home_config)
    return [home_config]


def _find_project_config_path(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()

    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate / PROJECT_CONFIG_DIR / PROJECT_CONFIG_FILENAME

    return None


def _merge_mappings(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_mappings(
                cast(dict[str, Any], merged[key]),
                cast(dict[str, Any], value),
            )
            continue
        merged[key] = value

    return merged


def _merge_model_config(
    base: ModelConfig,
    override: ModelConfig | ModelOverride,
) -> ModelConfig:
    merged = base.model_dump()
    merged.update(override.model_dump(exclude_none=True))
    return ModelConfig.model_validate(merged)


def _model_provider(model: ModelConfig | ModelOverride | None) -> str | None:
    if model is None:
        return None
    provider = getattr(model, "provider", None)
    return provider if isinstance(provider, str) else None


__all__ = [
    "AgentConfig",
    "ConfigError",
    "ModelConfig",
    "ModelOverride",
    "VioScopeConfig",
    "create_default_config",
    "load_config",
    "validate_api_keys",
]
