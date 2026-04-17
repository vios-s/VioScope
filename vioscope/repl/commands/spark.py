from __future__ import annotations

import json
import shlex
from datetime import datetime, timezone
from typing import Literal

from pydantic import ValidationError

from vioscope.agents.spark import PIVOTExhaustedError
from vioscope.repl.commands.base import BaseCommand, UsageError
from vioscope.schemas.pipeline import PipelineConfig, PipelineSession
from vioscope.schemas.research import SynthesisReport


class SparkCommand(BaseCommand):
    def _parse_spark_flags(
        self,
        args: str,
    ) -> tuple[str, str | None, str | None, list[str], list[str]]:
        try:
            tokens = shlex.split(args)
        except ValueError:
            tokens = args.split()

        positional: list[str] = []
        flag_input: str | None = None
        flag_from_kb: str | None = None
        constraints: list[str] = []
        additional_constraints: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("--input", "-i") and i + 1 < len(tokens):
                flag_input = tokens[i + 1]
                i += 2
            elif tok.startswith("--input="):
                flag_input = tok[len("--input=") :]
                i += 1
            elif tok == "--from-kb" and i + 1 < len(tokens):
                flag_from_kb = tokens[i + 1]
                i += 2
            elif tok.startswith("--from-kb="):
                flag_from_kb = tok[len("--from-kb=") :]
                i += 1
            elif tok in ("--constraints", "-c") and i + 1 < len(tokens):
                constraints.append(tokens[i + 1])
                i += 2
            elif tok.startswith("--constraints="):
                constraints.append(tok[len("--constraints=") :])
                i += 1
            elif tok == "--additional-constraint" and i + 1 < len(tokens):
                additional_constraints.append(tokens[i + 1])
                i += 2
            elif tok.startswith("--additional-constraint="):
                additional_constraints.append(tok[len("--additional-constraint=") :])
                i += 1
            else:
                positional.append(tok)
                i += 1

        return " ".join(positional), flag_input, flag_from_kb, constraints, additional_constraints

    def run(self, args: str) -> str:
        (
            positional,
            flag_input,
            flag_from_kb,
            constraints,
            additional_constraints,
        ) = self._parse_spark_flags(args)

        if positional:
            constraints.append(positional)

        if self.ctx.synthesis is None and not flag_input and not flag_from_kb:
            return (
                "No synthesis in session. Run /synth first, or provide "
                "--input <synthesis.json> or --from-kb <id>."
            )

        if self.agents is None:
            return "Agents not initialized — restart the session."

        synthesis = self.ctx.synthesis
        if synthesis is None:
            try:
                resolved = self.resolve_input(flag_input, flag_from_kb)
            except UsageError as exc:
                return str(exc)

            raw = resolved.get("synthesis") or resolved.get("data")
            try:
                synthesis = SynthesisReport.model_validate(raw)
            except ValidationError:
                return "Input must contain a valid SynthesisReport JSON object."

        next_action: Literal["continue", "regenerate"] = (
            "regenerate" if additional_constraints else "continue"
        )
        session = PipelineSession(
            session_id=self.ctx.session_id,
            research_question="(interactive session)",
            created_at=datetime.now(timezone.utc),
            config=PipelineConfig(),
            synthesis=synthesis,
            regeneration_constraints=[*constraints, *additional_constraints],
            next_action=next_action,
            pivot_count=0,
        )

        try:
            session = self.agents.spark.generate(session)
        except PIVOTExhaustedError as exc:
            return f"Spark rerun limit reached: {exc}"
        except RuntimeError as exc:
            return f"Spark agent unavailable: {exc}"

        if not session.hypothesis_candidates:
            return "Spark produced no hypothesis candidates. Check agent configuration."

        self.ctx.synthesis = synthesis
        self.ctx.hypothesis_candidates = session.hypothesis_candidates
        self.ctx.selected_hypothesis = None

        lines = ["## Spark Complete", ""]
        lines.append(f"**Candidates generated:** {len(session.hypothesis_candidates)}")
        lines.append(f"**Pivot rounds used:** {session.pivot_count}")
        if session.regeneration_constraints:
            lines.append(
                f"**Constraints applied:** {json.dumps(session.regeneration_constraints)}"
            )
        lines.append("")
        for candidate in session.hypothesis_candidates[:3]:
            lines.append(f"- #{candidate.rank or '?'} {candidate.title}")
        if len(session.hypothesis_candidates) > 3:
            lines.append(f"- ... and {len(session.hypothesis_candidates) - 3} more candidate(s)")
        lines.append("")
        lines.append("Hypothesis candidates saved to session.")
        return "\n".join(lines)
