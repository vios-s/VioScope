from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent  # type: ignore[import-not-found]
else:  # pragma: no cover - runtime fallback when agno is unavailable

    class AgnoAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

        def run(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
            raise RuntimeError("Agent unavailable")

    try:
        from agno.agent import Agent as _RuntimeAgnoAgent  # type: ignore[import-not-found]
    except Exception:
        pass
    else:
        AgnoAgent = _RuntimeAgnoAgent

from vioscope.agents._models import build_agno_model
from vioscope.config import AgentConfig, ModelConfig, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.schemas.research import HypothesisCandidateList, SparkRole, SynthesisReport


class _FallbackAgent:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise RuntimeError("Spark sub-agent backend is unavailable")


class SparkInput(BaseModel):
    research_question: str
    synthesis: SynthesisReport
    constraints: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SparkRoleDefaults(BaseModel):
    name: str
    instructions: list[str]

    model_config = ConfigDict(extra="forbid")


class SparkDefaults(BaseModel):
    name: str
    model: ModelConfig
    timeout_seconds: int
    roles: dict[SparkRole, SparkRoleDefaults]

    model_config = ConfigDict(extra="forbid")


@lru_cache(maxsize=1)
def load_spark_defaults() -> SparkDefaults:
    return SparkDefaults.model_validate(load_agent_defaults("spark"))


def _resolve_model_config(cfg: AgentConfig | VioScopeConfig) -> ModelConfig:
    defaults = load_spark_defaults()
    if isinstance(cfg, VioScopeConfig):
        return cfg.get_model_for_agent("spark", default_model=defaults.model)
    if cfg.model:
        return defaults.model.model_copy(update=cfg.model.model_dump(exclude_none=True))
    return defaults.model


def _normalize_json_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return _normalize_json_payload(json.loads(payload))
        except json.JSONDecodeError:
            return payload
    if isinstance(payload, list):
        return [_normalize_json_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _normalize_json_payload(value) for key, value in payload.items()}
    return payload


def _coerce_candidate_list(response: Any) -> HypothesisCandidateList:
    payload = getattr(response, "content", response)
    if isinstance(payload, HypothesisCandidateList):
        return payload
    if isinstance(payload, BaseModel):
        return HypothesisCandidateList.model_validate(payload.model_dump())
    return HypothesisCandidateList.model_validate(_normalize_json_payload(payload))


class SparkAgent:
    def __init__(self, cfg: AgentConfig | VioScopeConfig) -> None:
        defaults = load_spark_defaults()
        resolved_model = _resolve_model_config(cfg)
        model = build_agno_model(resolved_model, defaults.timeout_seconds)

        self.cfg = cfg
        self.name = defaults.name
        self.model = cast(Any, model)
        self.resolved_model = resolved_model
        self.timeout_seconds = defaults.timeout_seconds
        self.output_schema = HypothesisCandidateList
        self.role_instructions = {
            role: role_defaults.instructions for role, role_defaults in defaults.roles.items()
        }
        self.role_names = {
            role: role_defaults.name for role, role_defaults in defaults.roles.items()
        }
        self.role_agents: dict[SparkRole, Any] = {}
        self._init_errors: dict[SparkRole, Exception] = {}

        for role, role_defaults in defaults.roles.items():
            role_agent: Any
            try:
                role_agent = AgnoAgent(
                    name=role_defaults.name,
                    model=model,
                    instructions=role_defaults.instructions,
                    output_schema=HypothesisCandidateList,
                )
            except Exception as exc:  # pragma: no cover - depends on optional provider SDKs
                self._init_errors[role] = exc
                role_agent = _FallbackAgent(
                    name=role_defaults.name,
                    model=model,
                    instructions=role_defaults.instructions,
                    output_schema=HypothesisCandidateList,
                )

            self.role_agents[role] = role_agent

    def run_role(self, role: SparkRole, spark_input: SparkInput) -> HypothesisCandidateList:
        init_error = self._init_errors.get(role)
        if init_error is not None:
            raise RuntimeError(
                f"Spark role backend is unavailable for '{role.value}' in this environment"
            ) from init_error

        response = self.role_agents[role].run(input=spark_input)
        return _coerce_candidate_list(response)


def build_spark(cfg: AgentConfig | VioScopeConfig) -> SparkAgent:
    """Construct the Spark agent shell with role-specific sub-agents and shared schema."""

    return SparkAgent(cfg=cfg)


__all__ = [
    "SparkAgent",
    "SparkDefaults",
    "SparkInput",
    "SparkRoleDefaults",
    "_coerce_candidate_list",
    "build_spark",
    "load_spark_defaults",
]
