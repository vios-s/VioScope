from __future__ import annotations

import uuid
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.markdown import Markdown
from rich.panel import Panel

from vioscope import __version__
from vioscope.config import VioScopeConfig
from vioscope.core.ui import console
from vioscope.repl.agents import build_agents
from vioscope.repl.context import SessionContext
from vioscope.repl.dispatcher import dispatch

SLASH_COMMANDS = [
    "/scout",
    "/synth",
    "/spark",
    "/skeptic",
    "/scribe",
    "/steward",
    "/pipeline",
    "/kb",
    "/session",
    "/help",
    "/quit",
    "/exit",
    "/q",
]


def run_interactive(config: VioScopeConfig) -> None:
    agents = build_agents(config)
    ctx = SessionContext(session_id=str(uuid.uuid4()))
    history_path = Path.home() / ".vioscope" / "history"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        completer=WordCompleter(SLASH_COMMANDS, sentence=True),
    )

    console.print(
        Panel(
            f"VioScope {__version__} — interactive research session\n"
            "Type /help for commands, or describe what you need.",
            title="VioScope",
        )
    )

    while True:
        try:
            raw = session.prompt("> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break
        if not raw:
            continue
        if raw in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        result = dispatch(raw, ctx, agents=agents)
        if result:
            console.print(Panel(Markdown(result)))
