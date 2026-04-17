from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from vioscope.cli import app

runner = CliRunner()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _config_content(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    _write(
        config_path,
        "model:\n  provider: ollama\n  model_id: llama3.2\nknowledge_base:\n  local_path: "
        f"{tmp_path / 'kb'}\n",
    )
    return config_path


def test_main_without_command_starts_repl(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)
    with patch("vioscope.repl.run_interactive") as mock_repl:
        result = runner.invoke(app, ["--config", str(config_path)])

    assert result.exit_code == 0
    mock_repl.assert_called_once()


def test_main_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for cmd in ("research", "search", "review", "write", "kb", "config"):
        assert cmd in result.stdout


def test_research_command_uses_explicit_config(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)

    result = runner.invoke(app, ["research", "retinal vessel study", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Research command is not yet implemented." in result.stdout
    assert "Model: ollama:llama3.2" in result.stdout


def test_kb_list_command_displays_records(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)
    kb_root = tmp_path / "kb"
    _write(
        kb_root / "literature" / "2026-04-13T00-00-00Z_session-1_literature.md",
        "---\n"
        "type: literature\n"
        "session_id: session-1\n"
        "created_at: 2026-04-13T00:00:00Z\n"
        "research_question: retinal vessel study\n"
        "---\n"
        "Literature summary",
    )

    result = runner.invoke(app, ["kb", "list", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Knowledge Base Records" in result.stdout
    assert "session-1" in result.stdout


def test_kb_show_command_displays_content(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)
    kb_root = tmp_path / "kb"
    _write(
        kb_root / "sessions" / "2026-04-13T00-00-00Z_session-1_sessions.md",
        "---\n"
        "type: sessions\n"
        "session_id: session-1\n"
        "created_at: 2026-04-13T00:00:00Z\n"
        "---\n"
        "Session summary",
    )

    result = runner.invoke(
        app,
        [
            "kb",
            "show",
            "sessions",
            "2026-04-13T00-00-00Z_session-1_sessions",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "Session summary" in result.stdout


def test_kb_search_command_displays_results(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)
    kb_root = tmp_path / "kb"
    _write(
        kb_root / "hypotheses" / "2026-04-13T00-00-00Z_session-2_hypotheses.md",
        "---\n"
        "type: hypotheses\n"
        "session_id: session-2\n"
        "created_at: 2026-04-13T00:00:00Z\n"
        "research_question: retinal vessel study\n"
        "---\n"
        "Hypothesis about retinal vessels",
    )

    result = runner.invoke(
        app,
        ["kb", "search", "retinal", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "KB Search: retinal" in result.stdout
    assert "session-2" in result.stdout


def test_config_validate_reports_success(tmp_path: Path) -> None:
    config_path = _config_content(tmp_path)

    result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Configuration ok. Provider=ollama, Model=llama3.2" in result.stdout


def test_config_init_creates_missing_explicit_file(tmp_path: Path) -> None:
    config_path = tmp_path / "generated.yaml"

    result = runner.invoke(app, ["config", "init", "--config", str(config_path)])

    assert result.exit_code == 0
    assert config_path.exists()
    assert "Configuration initialized or loaded" in result.stdout
