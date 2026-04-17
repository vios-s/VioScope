from __future__ import annotations

from datetime import datetime, timezone

from vioscope.repl.commands.base import BaseCommand
from vioscope.schemas.pipeline import PipelineConfig, PipelineSession


class ScoutCommand(BaseCommand):
    def run(self, args: str) -> str:
        positional, flag_input, flag_from_kb = self._parse_flags(args)
        query = positional.strip().strip("\"'")
        if not query:
            return "Usage: /scout <query>  Search for papers matching a query."

        if self.agents is None:
            return "Agents not initialized — restart the session."

        session = PipelineSession(
            session_id=self.ctx.session_id,
            research_question=query,
            created_at=datetime.now(timezone.utc),
            config=PipelineConfig(),
        )

        for database in session.config.databases:
            session = self.agents.scout.search(session, database)

        papers = session.search_results or []
        self.ctx.papers_found = list(papers)

        if not papers:
            return f"No papers found for: **{query}**"

        lines = [f"Found **{len(papers)}** papers for: **{query}**", ""]
        for idx, paper in enumerate(papers[:10], 1):
            authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown"
            year = f" ({paper.year})" if paper.year else ""
            verified = " ✓" if paper.verified else ""
            lines.append(f"{idx}. **{paper.title}**{year} — {authors}{verified}")
        if len(papers) > 10:
            lines.append(f"\n... and {len(papers) - 10} more. Context saved to session.")
        else:
            lines.append("\nContext saved to session. Run /synth to synthesize.")

        return "\n".join(lines)
