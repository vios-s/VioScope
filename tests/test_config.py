from __future__ import annotations

from pathlib import Path

import pytest

from vioscope.config import AgentConfig, ModelConfig, ModelOverride, VioScopeConfig, load_config


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_load_config_uses_project_local_config_when_home_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    nested_dir = project_root / "src"
    home_config = tmp_path / "home" / ".vioscope" / "config.yaml"
    project_config = project_root / ".vioscope" / "config.yaml"

    nested_dir.mkdir(parents=True, exist_ok=True)
    _write(project_root / "pyproject.toml", "[project]\nname = 'demo'\n")
    _write(
        project_config,
        "model:\n  provider: ollama\n  model_id: project-model\nagents:\n  synth:\n    model:\n      provider: ollama\n      model_id: project-synth\n",
    )

    monkeypatch.chdir(nested_dir)
    monkeypatch.setattr("vioscope.config.DEFAULT_CONFIG_PATH", home_config)

    cfg = load_config()

    assert cfg.model.provider == "ollama"
    assert cfg.model.model_id == "project-model"
    assert cfg.get_model_for_agent("synth").model_id == "project-synth"
    assert home_config.exists() is False


def test_load_config_home_overrides_project_when_both_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    nested_dir = project_root / "app"
    home_config = tmp_path / "home" / ".vioscope" / "config.yaml"
    project_config = project_root / ".vioscope" / "config.yaml"

    nested_dir.mkdir(parents=True, exist_ok=True)
    _write(project_root / "pyproject.toml", "[project]\nname = 'demo'\n")
    _write(
        project_config,
        "model:\n  provider: ollama\n  model_id: project-model\nagents:\n  synth:\n    model:\n      provider: ollama\n      model_id: project-synth\nknowledge_base:\n  backend: local\n",
    )
    _write(
        home_config,
        "model:\n  provider: ollama\n  model_id: home-model\nagents:\n  synth:\n    model:\n      provider: ollama\n      model_id: home-synth\n",
    )

    monkeypatch.chdir(nested_dir)
    monkeypatch.setattr("vioscope.config.DEFAULT_CONFIG_PATH", home_config)

    cfg = load_config()

    assert cfg.model.model_id == "home-model"
    assert cfg.get_model_for_agent("synth").model_id == "home-synth"
    assert cfg.knowledge_base == {"backend": "local"}


def test_load_config_explicit_path_bypasses_layered_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    home_config = tmp_path / "home" / ".vioscope" / "config.yaml"
    explicit_config = tmp_path / "custom.yaml"

    _write(project_root / "pyproject.toml", "[project]\nname = 'demo'\n")
    _write(
        project_root / ".vioscope" / "config.yaml",
        "model:\n  provider: ollama\n  model_id: project-model\n",
    )
    _write(home_config, "model:\n  provider: ollama\n  model_id: home-model\n")
    _write(explicit_config, "model:\n  provider: ollama\n  model_id: explicit-model\n")

    monkeypatch.chdir(project_root)
    monkeypatch.setattr("vioscope.config.DEFAULT_CONFIG_PATH", home_config)

    cfg = load_config(explicit_config)

    assert cfg.model.model_id == "explicit-model"


def test_get_model_for_agent_merges_packaged_default_global_and_partial_agent_override() -> None:
    cfg = VioScopeConfig(
        model=ModelConfig(
            provider="openrouter",
            model_id="openai/gpt-5.4-nano",
            temperature=0.15,
            max_tokens=3072,
        ),
        agents={
            "synth": AgentConfig(
                model=ModelOverride(
                    temperature=0.4,
                )
            )
        },
    )

    resolved = cfg.get_model_for_agent(
        "synth",
        default_model=ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-6",
            temperature=0.2,
            max_tokens=4096,
        ),
    )

    assert resolved == ModelConfig(
        provider="openrouter",
        model_id="openai/gpt-5.4-nano",
        temperature=0.4,
        max_tokens=3072,
    )
