from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent  # type: ignore[import-not-found]
else:  # pragma: no cover - runtime fallback when agno is unavailable

    class AgnoAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

        def run(self, *_args: Any, **_kwargs: Any) -> Any:
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
from vioscope.schemas.research import (
    CritiqueReport,
    HypothesisRecord,
    SkepticMode,
    SynthesisReport,
)
from vioscope.schemas.writing import DraftSection


class SkepticDefaults(BaseModel):
    name: str
    model: ModelConfig
    timeout_seconds: int
    anti_rationalization_directive: str
    shared_instructions: list[str]
    mode_instructions: dict[SkepticMode, list[str]]

    model_config = ConfigDict(extra="forbid")


class SkepticInput(BaseModel):
    mode: SkepticMode
    research_question: str
    hypothesis: HypothesisRecord | None = None
    draft_sections: list[DraftSection] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
    selected_hypothesis: HypothesisRecord | None = None
    additional_constraints: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "SkepticInput":
        if self.mode is SkepticMode.HYPOTHESIS and self.hypothesis is None:
            raise ValueError("Hypothesis mode requires a hypothesis payload.")
        if self.mode is SkepticMode.MANUSCRIPT and not self.draft_sections:
            raise ValueError("Manuscript mode requires at least one draft section.")
        return self


@lru_cache(maxsize=1)
def load_skeptic_defaults() -> SkepticDefaults:
    return SkepticDefaults.model_validate(load_agent_defaults("skeptic"))


def _resolve_model_config(cfg: AgentConfig | VioScopeConfig) -> ModelConfig:
    defaults = load_skeptic_defaults()
    if isinstance(cfg, VioScopeConfig):
        return cfg.get_model_for_agent("skeptic", default_model=defaults.model)
    if cfg.model:
        return defaults.model.model_copy(update=cfg.model.model_dump(exclude_none=True))
    return defaults.model


def compose_skeptic_instructions(mode: SkepticMode) -> list[str]:
    defaults = load_skeptic_defaults()
    return [
        *defaults.shared_instructions,
        defaults.anti_rationalization_directive,
        *defaults.mode_instructions[mode],
        f"Return only a structured CritiqueReport with mode='{mode.value}'.",
        "Use verdict `pass`, `pivot`, or `fail` consistently with the evidence in the provided input.",
    ]


def _build_runtime_instructions() -> list[str]:
    defaults = load_skeptic_defaults()
    instructions = [
        *defaults.shared_instructions,
        defaults.anti_rationalization_directive,
        "Use the structured `mode` field in the runtime input to choose the appropriate review behavior.",
    ]
    for mode in SkepticMode:
        instructions.append(f"When mode='{mode.value}':")
        instructions.extend(defaults.mode_instructions[mode])
    instructions.extend(
        [
            "Return only the CritiqueReport structured output.",
            "Populate `mode` from the runtime input and set `target_id` when a concrete artifact is supplied.",
        ]
    )
    return instructions


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


def _coerce_critique_report(response: Any) -> CritiqueReport:
    payload = getattr(response, "content", response)
    if isinstance(payload, CritiqueReport):
        return payload
    if isinstance(payload, BaseModel):
        return CritiqueReport.model_validate(payload.model_dump())
    return CritiqueReport.model_validate(_normalize_json_payload(payload))


def _target_id_for_input(skeptic_input: SkepticInput) -> str | None:
    if skeptic_input.mode is SkepticMode.HYPOTHESIS and skeptic_input.hypothesis is not None:
        return skeptic_input.hypothesis.hypothesis_id
    if skeptic_input.mode is SkepticMode.MANUSCRIPT and skeptic_input.draft_sections:
        return skeptic_input.draft_sections[0].name
    return None


class SkepticAgent(AgnoAgent):
    def __init__(
        self,
        cfg: AgentConfig | VioScopeConfig,
        circuit_breaker: CircuitBreaker[Any] | None = None,
    ) -> None:
        defaults = load_skeptic_defaults()
        resolved_model = _resolve_model_config(cfg)
        model = build_agno_model(resolved_model, defaults.timeout_seconds)
        instructions = _build_runtime_instructions()
        self._init_error: Exception | None = None
        try:
            super().__init__(
                name=defaults.name,
                model=model,
                instructions=instructions,
                input_schema=SkepticInput,
                output_schema=CritiqueReport,
            )
        except Exception as exc:  # pragma: no cover - depends on optional provider SDKs
            self._init_error = exc
            self.model = cast(Any, model)
            self.instructions = instructions
            self.input_schema = SkepticInput
            self.output_schema = CritiqueReport
            self.name = defaults.name
        self.cfg = cfg
        self.resolved_model = resolved_model
        self.timeout_seconds = defaults.timeout_seconds
        self.circuit_breaker = circuit_breaker or CircuitBreaker(backoff_seconds=0.0)

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self._init_error is not None:
            raise RuntimeError(
                "Skeptic agent backend is unavailable in this environment"
            ) from self._init_error
        return super().run(*args, **kwargs)

    def critique(self, skeptic_input: SkepticInput) -> CritiqueReport:
        response = self.circuit_breaker.call(lambda: self.run(input=skeptic_input))
        critique = _coerce_critique_report(response)
        target_id = critique.target_id or _target_id_for_input(skeptic_input)
        if critique.mode is not skeptic_input.mode or critique.target_id != target_id:
            critique = critique.model_copy(
                update={
                    "mode": skeptic_input.mode,
                    "target_id": target_id,
                }
            )
        return critique

    def critique_hypothesis(
        self,
        session: PipelineSession,
        hypothesis: HypothesisRecord | None = None,
        *,
        additional_constraints: list[str] | None = None,
    ) -> CritiqueReport:
        target = hypothesis or session.selected_hypothesis
        if target is None and session.hypothesis_candidates:
            target = sorted(
                session.hypothesis_candidates,
                key=lambda candidate: candidate.rank or 10_000,
            )[0]
        if target is None:
            raise ValueError("No hypothesis is available for Skeptic review.")

        skeptic_input = SkepticInput(
            mode=SkepticMode.HYPOTHESIS,
            research_question=session.research_question,
            hypothesis=target,
            synthesis=session.synthesis,
            additional_constraints=additional_constraints or [],
        )
        return self.critique(skeptic_input)

    def critique_manuscript(
        self,
        session: PipelineSession,
        draft_sections: list[DraftSection] | None = None,
        *,
        additional_constraints: list[str] | None = None,
    ) -> CritiqueReport:
        sections = draft_sections or session.draft_sections or []
        if not sections:
            raise ValueError("No manuscript draft sections are available for Skeptic review.")

        skeptic_input = SkepticInput(
            mode=SkepticMode.MANUSCRIPT,
            research_question=session.research_question,
            draft_sections=sections,
            selected_hypothesis=session.selected_hypothesis,
            additional_constraints=additional_constraints or [],
        )
        return self.critique(skeptic_input)


def build_skeptic(cfg: AgentConfig | VioScopeConfig) -> SkepticAgent:
    """Construct the Skeptic agent configured for structured adversarial critique."""

    return SkepticAgent(cfg=cfg)


__all__ = [
    "SkepticAgent",
    "SkepticDefaults",
    "SkepticInput",
    "_coerce_critique_report",
    "build_skeptic",
    "compose_skeptic_instructions",
    "load_skeptic_defaults",
]
