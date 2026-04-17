from __future__ import annotations

import json
import shlex
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vioscope.repl.context import SessionContext

if TYPE_CHECKING:
    from vioscope.repl.agents import AgentBundle


class UsageError(Exception):
    pass


class BaseCommand(ABC):
    def __init__(self, ctx: SessionContext, agents: AgentBundle | None) -> None:
        self.ctx = ctx
        self.agents = agents

    @abstractmethod
    def run(self, args: str) -> str:
        raise NotImplementedError

    def resolve_input(
        self,
        flag_input: str | None = None,
        flag_from_kb: str | None = None,
    ) -> dict[str, Any]:
        """Context resolution: session → --input file → --from-kb → raise."""
        if self.ctx.synthesis is not None:
            return {"synthesis": self.ctx.synthesis, "source": "session"}
        if self.ctx.papers_found:
            return {"papers": self.ctx.papers_found, "source": "session"}
        if flag_input:
            path = Path(flag_input)
            if not path.exists():
                raise UsageError(f"File not found: {flag_input}")
            raw = json.loads(path.read_text())
            return {"data": raw, "source": "file", "path": flag_input}
        if flag_from_kb:
            return {"kb_id": flag_from_kb, "source": "kb"}
        raise UsageError(
            "No context available. Run /scout <query> first, or provide --input <file> or --from-kb <id>."
        )

    def _parse_flags(self, args: str) -> tuple[str, str | None, str | None]:
        """Return (positional_args, --input value, --from-kb value)."""
        try:
            tokens = shlex.split(args)
        except ValueError:
            tokens = args.split()

        positional: list[str] = []
        flag_input: str | None = None
        flag_from_kb: str | None = None
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("--input", "-i") and i + 1 < len(tokens):
                flag_input = tokens[i + 1]
                i += 2
            elif tok.startswith("--input="):
                flag_input = tok[len("--input=") :]
                i += 1
            elif tok in ("--from-kb",) and i + 1 < len(tokens):
                flag_from_kb = tokens[i + 1]
                i += 2
            elif tok.startswith("--from-kb="):
                flag_from_kb = tok[len("--from-kb=") :]
                i += 1
            else:
                positional.append(tok)
                i += 1
        return " ".join(positional), flag_input, flag_from_kb
