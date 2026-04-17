from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class SkepticCommand(BaseCommand):
    def run(self, args: str) -> str:
        return (
            "**Skeptic agent** (adversarial review) is not yet implemented — coming in Epic 6.\n\n"
            "Skeptic will critique hypotheses and manuscript drafts once Epic 6 is complete."
        )
