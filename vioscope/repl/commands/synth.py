from __future__ import annotations

from datetime import datetime, timezone

from vioscope.repl.commands.base import BaseCommand, UsageError
from vioscope.schemas.pipeline import PipelineConfig, PipelineSession


class SynthCommand(BaseCommand):
    def run(self, args: str) -> str:
        positional, flag_input, flag_from_kb = self._parse_flags(args)

        papers = self.ctx.papers_screened or self.ctx.papers_found

        if not papers and not flag_input and not flag_from_kb:
            return "No papers in session. Run /scout <query> first, or use --input <file>."

        if self.agents is None:
            return "Agents not initialized — restart the session."

        if not papers:
            try:
                resolved = self.resolve_input(flag_input, flag_from_kb)
                papers = resolved.get("papers") or resolved.get("data", [])
            except UsageError as exc:
                return str(exc)

        if not papers:
            return "No papers to synthesize."

        session = PipelineSession(
            session_id=self.ctx.session_id,
            research_question="(interactive session)",
            created_at=datetime.now(timezone.utc),
            config=PipelineConfig(),
            screened_papers=papers,
        )

        try:
            session = self.agents.synth.synthesize(session)
        except RuntimeError as exc:
            return f"Synth agent unavailable: {exc}"

        if session.synthesis is None:
            return "Synthesis produced no output. Check agent configuration."

        self.ctx.synthesis = session.synthesis
        report = session.synthesis

        lines = ["## Synthesis Complete", ""]
        lines.append(f"**Papers synthesized:** {len(papers)}")
        lines.append(f"**Research gaps:** {len(report.research_gaps)}")
        for gap in report.research_gaps[:5]:
            lines.append(f"- {gap}")
        if len(report.research_gaps) > 5:
            lines.append(f"- ... and {len(report.research_gaps) - 5} more")
        lines.append(f"\n**Method groups:** {len(report.method_taxonomy)}")
        lines.append(f"**Datasets:** {len(report.dataset_summary)}")
        lines.append("\nSynthesis saved to session. Run /spark to generate hypotheses.")

        return "\n".join(lines)
