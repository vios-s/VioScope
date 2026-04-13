from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict

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
from vioscope.core.circuit_breaker import CircuitBreaker
from vioscope.schemas.pipeline import PipelineSession
from vioscope.schemas.research import Paper, SynthesisReport


class SynthInput(BaseModel):
    research_question: str
    papers: list[Paper]

    model_config = ConfigDict(extra="forbid")


class SynthDefaults(BaseModel):
    name: str
    model: ModelConfig
    timeout_seconds: int
    instructions: list[str]

    model_config = ConfigDict(extra="forbid")


@lru_cache(maxsize=1)
def load_synth_defaults() -> SynthDefaults:
    return SynthDefaults.model_validate(load_agent_defaults("synth"))


def _resolve_model_config(cfg: AgentConfig | VioScopeConfig) -> ModelConfig:
    defaults = load_synth_defaults()
    if isinstance(cfg, VioScopeConfig):
        return cfg.get_model_for_agent("synth", default_model=defaults.model)
    if cfg.model:
        return defaults.model.model_copy(update=cfg.model.model_dump(exclude_none=True))
    return defaults.model


def _coerce_synthesis_report(response: Any) -> SynthesisReport:
    payload = getattr(response, "content", response)
    if isinstance(payload, SynthesisReport):
        return payload
    if isinstance(payload, BaseModel):
        return SynthesisReport.model_validate(payload.model_dump())
    return SynthesisReport.model_validate(_normalize_json_payload(payload))


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


class SynthAgent(AgnoAgent):
    def __init__(
        self,
        cfg: AgentConfig | VioScopeConfig,
        circuit_breaker: CircuitBreaker[Any] | None = None,
    ) -> None:
        defaults = load_synth_defaults()
        resolved_model = _resolve_model_config(cfg)
        model = build_agno_model(resolved_model, defaults.timeout_seconds)
        self._init_error: Exception | None = None
        try:
            super().__init__(
                name=defaults.name,
                model=model,
                instructions=defaults.instructions,
                output_schema=SynthesisReport,
            )
        except Exception as exc:  # pragma: no cover - depends on optional provider SDKs
            self._init_error = exc
            self.model = cast(Any, model)
            self.instructions = defaults.instructions
            self.output_schema = SynthesisReport
            self.name = defaults.name
        self.cfg = cfg
        self.resolved_model = resolved_model
        self.circuit_breaker = circuit_breaker or CircuitBreaker(backoff_seconds=0.0)
        self.timeout_seconds = defaults.timeout_seconds

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self._init_error is not None:
            raise RuntimeError(
                "Synth agent backend is unavailable in this environment"
            ) from self._init_error
        return super().run(*args, **kwargs)

    def synthesize(self, session: PipelineSession) -> PipelineSession:
        if not session.screened_papers:
            return session

        synth_input = SynthInput(
            research_question=session.research_question,
            papers=session.screened_papers,
        )
        response = self.circuit_breaker.call(lambda: self.run(input=synth_input))
        synthesis = _coerce_synthesis_report(response)
        return session.model_copy(update={"synthesis": synthesis})


def build_synth(cfg: AgentConfig | VioScopeConfig) -> SynthAgent:
    """Construct the Synth agent configured for structured synthesis output."""

    return SynthAgent(cfg=cfg)


__all__ = [
    "SynthAgent",
    "SynthDefaults",
    "SynthInput",
    "build_synth",
    "load_synth_defaults",
]
