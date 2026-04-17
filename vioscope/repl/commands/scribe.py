from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class ScribeCommand(BaseCommand):
    def run(self, args: str) -> str:
        return (
            "**Scribe agent** (paper drafting) is not yet implemented — coming in Epic 8.\n\n"
            "Scribe will draft outlines and sections once a hypothesis is approved."
        )
