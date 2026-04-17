from __future__ import annotations

from typing import TYPE_CHECKING, Type

from vioscope.repl.commands.base import BaseCommand
from vioscope.repl.commands.help import HelpCommand
from vioscope.repl.commands.kb import KBCommand
from vioscope.repl.commands.pipeline import PipelineCommand
from vioscope.repl.commands.scout import ScoutCommand
from vioscope.repl.commands.scribe import ScribeCommand
from vioscope.repl.commands.session import SessionCommand
from vioscope.repl.commands.skeptic import SkepticCommand
from vioscope.repl.commands.spark import SparkCommand
from vioscope.repl.commands.steward import StewardCommand
from vioscope.repl.commands.synth import SynthCommand
from vioscope.repl.context import SessionContext

if TYPE_CHECKING:
    from vioscope.repl.agents import AgentBundle

COMMAND_REGISTRY: dict[str, Type[BaseCommand]] = {
    "scout": ScoutCommand,
    "synth": SynthCommand,
    "spark": SparkCommand,
    "skeptic": SkepticCommand,
    "scribe": ScribeCommand,
    "steward": StewardCommand,
    "pipeline": PipelineCommand,
    "kb": KBCommand,
    "session": SessionCommand,
    "help": HelpCommand,
}

PLANNED_COMMANDS = [f"/{name}" for name in COMMAND_REGISTRY] + ["/quit", "/exit", "/q"]


def dispatch(raw_input: str, ctx: SessionContext, agents: AgentBundle | None = None) -> str:
    """Route a REPL input line to the appropriate handler.

    Slash commands → COMMAND_REGISTRY.
    Natural language → nl_router.
    """
    if raw_input.startswith("/"):
        parts = raw_input[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1] if len(parts) > 1 else ""

        if cmd_name in ("quit", "exit", "q"):
            return ""

        cmd_cls = COMMAND_REGISTRY.get(cmd_name)
        if cmd_cls is None:
            available = ", ".join(PLANNED_COMMANDS)
            return f"Unknown command: /{cmd_name}. Available: {available}"

        return cmd_cls(ctx, agents).run(cmd_args)

    from vioscope.repl.nl_router import nl_router

    return nl_router(raw_input, ctx, agents)
