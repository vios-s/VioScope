from __future__ import annotations

from typing import Any

from vioscope.config import ModelConfig


def build_agno_model(model_config: ModelConfig, timeout_seconds: int) -> Any:
    if model_config.provider == "anthropic":
        try:
            from agno.models.anthropic import Claude  # type: ignore[import-not-found]
        except Exception:
            return f"{model_config.provider}:{model_config.model_id}"
        return Claude(
            id=model_config.model_id,
            api_key=model_config.api_key,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            timeout=float(timeout_seconds),
        )

    if model_config.provider == "openrouter":
        try:
            from agno.models.openrouter import OpenRouter  # type: ignore[import-not-found]
        except Exception:
            return f"{model_config.provider}:{model_config.model_id}"
        kwargs: dict[str, Any] = {
            "id": model_config.model_id,
            "api_key": model_config.api_key,
            "temperature": model_config.temperature,
            "timeout": float(timeout_seconds),
        }
        if model_config.max_tokens is not None:
            kwargs["max_tokens"] = model_config.max_tokens
        return OpenRouter(**kwargs)

    if model_config.provider == "openai":
        try:
            from agno.models.openai import OpenAIChat  # type: ignore[import-not-found]
        except Exception:
            return f"{model_config.provider}:{model_config.model_id}"
        return OpenAIChat(
            id=model_config.model_id,
            api_key=model_config.api_key,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            timeout=float(timeout_seconds),
        )

    if model_config.provider == "google":
        try:
            from agno.models.google import Gemini  # type: ignore[import-not-found]
        except Exception:
            return f"{model_config.provider}:{model_config.model_id}"
        return Gemini(
            id=model_config.model_id,
            api_key=model_config.api_key,
            temperature=model_config.temperature,
            max_output_tokens=model_config.max_tokens,
            timeout=float(timeout_seconds),
        )

    if model_config.provider == "ollama":
        try:
            from agno.models.ollama import Ollama  # type: ignore[import-not-found]
        except Exception:
            return f"{model_config.provider}:{model_config.model_id}"
        options: dict[str, Any] = {}
        if model_config.temperature is not None:
            options["temperature"] = model_config.temperature
        if model_config.max_tokens is not None:
            options["num_predict"] = model_config.max_tokens
        return Ollama(
            id=model_config.model_id,
            options=options or None,
            timeout=float(timeout_seconds),
        )

    return f"{model_config.provider}:{model_config.model_id}"


__all__ = ["build_agno_model"]
