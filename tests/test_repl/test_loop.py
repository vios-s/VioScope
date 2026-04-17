from __future__ import annotations

from unittest.mock import MagicMock, patch

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
