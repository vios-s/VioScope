from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from prompt_toolkit.history import FileHistory
from rich.console import Console

from vioscope.repl.loop import run_interactive


def _make_config() -> MagicMock:
    return MagicMock()


def _run(prompts: list[str] | type[BaseException]) -> str:
    rec = Console(record=True)
    with (
        patch("vioscope.repl.loop.build_agents", return_value=MagicMock()),
        patch("vioscope.repl.loop.PromptSession") as mock_session_cls,
        patch("vioscope.repl.loop.console", rec),
    ):
        mock_session = MagicMock()
        if isinstance(prompts, list):
            mock_session.prompt.side_effect = prompts
        else:
            mock_session.prompt.side_effect = prompts
        mock_session_cls.return_value = mock_session
        run_interactive(_make_config())
    return rec.export_text()


def test_run_interactive_exits_on_quit() -> None:
    output = _run(["/quit"])
    assert "VioScope" in output
    assert "Goodbye" in output


def test_run_interactive_exits_on_eof() -> None:
    output = _run(EOFError)
    assert "Session ended" in output


def test_run_interactive_exits_on_keyboard_interrupt() -> None:
    output = _run(KeyboardInterrupt)
    assert "Session ended" in output


def test_run_interactive_skips_empty_input_then_quits() -> None:
    output = _run(["", "  ", "/exit"])
    assert "Goodbye" in output


def test_run_interactive_dispatches_unknown_command() -> None:
    output = _run(["/unknown", "/q"])
    assert "Unknown command" in output


def test_welcome_panel_printed() -> None:
    output = _run(EOFError)
    assert "interactive research session" in output


def test_run_interactive_does_not_create_history_by_default() -> None:
    rec = Console(record=True)
    with (
        patch("vioscope.repl.loop.build_agents", return_value=MagicMock()),
        patch("vioscope.repl.loop.PromptSession") as mock_session_cls,
        patch("vioscope.repl.loop.console", rec),
        patch.dict(os.environ, {}, clear=True),
    ):
        mock_session = MagicMock()
        mock_session.prompt.side_effect = EOFError
        mock_session_cls.return_value = mock_session
        run_interactive(_make_config())

    assert "history" not in mock_session_cls.call_args.kwargs


def test_run_interactive_uses_env_history_file(tmp_path: Path) -> None:
    rec = Console(record=True)
    history_file = tmp_path / "repl-history.txt"
    with (
        patch("vioscope.repl.loop.build_agents", return_value=MagicMock()),
        patch("vioscope.repl.loop.PromptSession") as mock_session_cls,
        patch("vioscope.repl.loop.console", rec),
        patch.dict(os.environ, {"VIOSCOPE_HISTORY_FILE": str(history_file)}),
    ):
        mock_session = MagicMock()
        mock_session.prompt.side_effect = EOFError
        mock_session_cls.return_value = mock_session
        run_interactive(_make_config())

    assert "history" in mock_session_cls.call_args.kwargs
    history_obj = mock_session_cls.call_args.kwargs["history"]
    assert isinstance(history_obj, FileHistory)
    assert history_obj.filename == str(history_file)
    assert history_file.parent.exists()


def test_run_interactive_warns_when_history_init_fails(tmp_path: Path) -> None:
    rec = Console(record=True)
    history_file = tmp_path / "repl-history.txt"
    with (
        patch("vioscope.repl.loop.build_agents", return_value=MagicMock()),
        patch("vioscope.repl.loop.PromptSession") as mock_session_cls,
        patch("vioscope.repl.loop.console", rec),
        patch("vioscope.repl.loop.Path.mkdir", side_effect=OSError("read-only fs")),
        patch.dict(os.environ, {"VIOSCOPE_HISTORY_FILE": str(history_file)}),
    ):
        mock_session = MagicMock()
        mock_session.prompt.side_effect = EOFError
        mock_session_cls.return_value = mock_session
        run_interactive(_make_config())

    assert "Warning:" in rec.export_text()
    assert "history" not in mock_session_cls.call_args.kwargs
