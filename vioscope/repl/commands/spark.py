from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class SparkCommand(BaseCommand):
    def run(self, args: str) -> str:
        return (
            "**Spark agent** (hypothesis generation) is not yet implemented — coming in Epic 5.\n\n"
            "To proceed: run `/synth` to synthesize papers first, then Spark will generate "
            "hypothesis candidates from the synthesis."
        )
