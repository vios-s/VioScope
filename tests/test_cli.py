from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from vioscope.cli import app

runner = CliRunner()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_main_without_command_shows_ready_message() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "VioScope CLI is ready." in result.stdout


def test_research_command_uses_explicit_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write(config_path, "model:\n  provider: ollama\n  model_id: llama3.2\n")

    result = runner.invoke(app, ["research", "retinal vessel study", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Research command is not yet implemented." in result.stdout
    assert "Model: ollama:llama3.2" in result.stdout


def test_kb_command_shows_placeholder(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write(config_path, "model:\n  provider: ollama\n  model_id: llama3.2\n")

    result = runner.invoke(app, ["kb", "--action", "list", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "KB command is not yet implemented." in result.stdout
    assert "Action: list" in result.stdout


def test_config_validate_reports_success(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write(config_path, "model:\n  provider: ollama\n  model_id: llama3.2\n")

    result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Configuration ok. Provider=ollama, Model=llama3.2" in result.stdout


def test_config_init_creates_missing_explicit_file(tmp_path: Path) -> None:
    config_path = tmp_path / "generated.yaml"

    result = runner.invoke(app, ["config", "init", "--config", str(config_path)])

    assert result.exit_code == 0
    assert config_path.exists()
    assert "Configuration initialized or loaded" in result.stdout
