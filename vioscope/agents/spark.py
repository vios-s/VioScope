from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent  # type: ignore[import-not-found]
    from agno.team.mode import TeamMode  # type: ignore[import-not-found]
    from agno.team.team import Team as AgnoTeam  # type: ignore[import-not-found]
else:  # pragma: no cover - runtime fallback when agno is unavailable

    class AgnoAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

        def run(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("Agent unavailable")

    class AgnoTeam:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

        def run(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("Team unavailable")

    try:
        from agno.agent import Agent as _RuntimeAgnoAgent  # type: ignore[import-not-found]
        from agno.team.mode import TeamMode  # type: ignore[import-not-found]
        from agno.team.team import Team as _RuntimeAgnoTeam  # type: ignore[import-not-found]
    except Exception:

        class TeamMode:
            broadcast = "broadcast"

        pass
    else:
        AgnoAgent = _RuntimeAgnoAgent
        AgnoTeam = _RuntimeAgnoTeam

from vioscope.agents._models import build_agno_model
from vioscope.config import AgentConfig, ModelConfig, VioScopeConfig
from vioscope.configs import load_agent_defaults
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas.pipeline import PipelineSession
from vioscope.schemas.research import HypothesisCandidateList, SparkRole, SynthesisReport


class PIVOTExhaustedError(RuntimeError):
    """Raised when Spark is asked to rerun after the configured pivot budget is spent."""

    def __init__(self, max_rounds: int) -> None:
        self.max_rounds = max_rounds
        super().__init__(f"Spark regeneration exhausted: max_pivot_rounds={max_rounds}")


class _FallbackAgent:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise RuntimeError("Spark sub-agent backend is unavailable")


class SparkInput(BaseModel):
    research_question: str
    synthesis: SynthesisReport
    additional_constraints: list[str] = Field(default_factory=list)

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


class SparkAgent(AgnoTeam):
    def __init__(
        self,
        cfg: AgentConfig | VioScopeConfig,
        circuit_breaker: CircuitBreaker[Any] | None = None,
    ) -> None:
        defaults = load_spark_defaults()
        resolved_model = _resolve_model_config(cfg)
        model = build_agno_model(resolved_model, defaults.timeout_seconds)

        self.cfg = cfg
        self.name = defaults.name
        self.model = cast(Any, model)
        self.resolved_model = resolved_model
        self.timeout_seconds = defaults.timeout_seconds
        self.output_schema = HypothesisCandidateList
        self.input_schema = SparkInput
        self.role_instructions = {
            role: role_defaults.instructions for role, role_defaults in defaults.roles.items()
        }
        self.role_names = {
            role: role_defaults.name for role, role_defaults in defaults.roles.items()
        }
        self.role_agents: dict[SparkRole, Any] = {}
        self.members: list[Any] = []
        self.mode = TeamMode.broadcast
        self._init_error: Exception | None = None
        self._role_init_errors: dict[SparkRole, Exception] = {}

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
                self._role_init_errors[role] = exc
                role_agent = _FallbackAgent(
                    name=role_defaults.name,
                    model=model,
                    instructions=role_defaults.instructions,
                    output_schema=HypothesisCandidateList,
                )

            self.role_agents[role] = role_agent
            self.members.append(role_agent)

        if self._role_init_errors:
            self._init_error = next(iter(self._role_init_errors.values()))
        else:
            try:
                super().__init__(
                    name=defaults.name,
                    mode=TeamMode.broadcast,
                    members=self.members,
                    input_schema=SparkInput,
                    output_schema=HypothesisCandidateList,
                )
                self.model = cast(Any, model)
            except Exception as exc:  # pragma: no cover - depends on optional provider SDKs
                self._init_error = exc
                self.name = defaults.name
                self.mode = TeamMode.broadcast
                self.output_schema = HypothesisCandidateList
                self.input_schema = SparkInput

        self.circuit_breaker = circuit_breaker or CircuitBreaker(backoff_seconds=0.0)

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self._init_error is not None:
            raise RuntimeError(
                "Spark team backend is unavailable in this environment"
            ) from self._init_error
        return super().run(*args, **kwargs)

    def run_role(self, role: SparkRole, spark_input: SparkInput) -> HypothesisCandidateList:
        init_error = self._role_init_errors.get(role)
        if init_error is not None:
            raise RuntimeError(
                f"Spark role backend is unavailable for '{role.value}' in this environment"
            ) from init_error

        response = self.role_agents[role].run(input=spark_input)
        return _coerce_candidate_list(response)

    def generate(self, session: PipelineSession) -> PipelineSession:
        if session.synthesis is None:
            return session

        is_regeneration = session.next_action == "regenerate"
        if is_regeneration and session.pivot_count >= session.config.max_pivot_rounds:
            raise PIVOTExhaustedError(session.config.max_pivot_rounds)

        additional_constraints: list[str] = []
        if session.scope and session.scope.strategy_notes:
            additional_constraints.append(session.scope.strategy_notes)
        additional_constraints.extend(session.regeneration_constraints)

        spark_input = SparkInput(
            research_question=session.research_question,
            synthesis=session.synthesis,
            additional_constraints=additional_constraints,
        )

        response = self.circuit_breaker.call(lambda: self.run(input=spark_input))
        candidate_list = _coerce_candidate_list(response)
        candidates = sorted(candidate_list.candidates, key=lambda candidate: candidate.rank or 0)

        updated_pivot_count = session.pivot_count + 1 if is_regeneration else session.pivot_count
        return session.model_copy(
            update={
                "hypothesis_candidates": candidates,
                "pivot_count": updated_pivot_count,
                "next_action": "continue",
            }
        )


def build_spark(cfg: AgentConfig | VioScopeConfig) -> SparkAgent:
    """Construct the Spark Team configured for broadcast hypothesis generation."""

    return SparkAgent(cfg=cfg)


__all__ = [
    "PIVOTExhaustedError",
    "SparkAgent",
    "SparkDefaults",
    "SparkInput",
    "SparkRoleDefaults",
    "_coerce_candidate_list",
    "build_spark",
    "load_spark_defaults",
]
