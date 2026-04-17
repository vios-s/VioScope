from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class StewardCommand(BaseCommand):
    def run(self, args: str) -> str:
        return (
            "**Steward agent** (KB archiving and GitBook sync) is not yet implemented — coming in Epic 9.\n\n"
            "Steward will store approved outputs locally and sync to GitBook."
        )
