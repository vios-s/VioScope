from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class PipelineCommand(BaseCommand):
    def run(self, args: str) -> str:
        positional, _flag_input, _flag_from_kb = self._parse_flags(args)
        ctx = self.ctx

        if not (
            ctx.papers_found or ctx.papers_screened or ctx.synthesis or ctx.selected_hypothesis
        ):
            return (
                "No session context to promote.\n"
                "Run `/scout <query>` first to gather papers, then `/pipeline`."
            )

        first_session_paper = (
            ctx.papers_found[0]
            if len(ctx.papers_found) > 0
            else (ctx.papers_screened[0] if len(ctx.papers_screened) > 0 else None)
        )
        question = positional.strip() or (
            ctx.selected_hypothesis.title
            if ctx.selected_hypothesis
            else (
                first_session_paper.title
                if first_session_paper
                else "interactive research session"
            )
        )

        try:
            pipeline_session = ctx.to_pipeline_session(question)
        except NotImplementedError:
            return (
                "Pipeline execution (agno Workflow) is coming in Epic 7.\n\n"
                "Your session context has been promoted to a `PipelineSession`:\n"
                f"- Research question: **{question}**\n"
                f"- Papers found: {len(ctx.papers_found)}\n"
                f"- Papers screened: {len(ctx.papers_screened)}\n"
                f"- Synthesis: {'complete' if ctx.synthesis else 'not yet run'}\n"
                f"- Hypotheses: {len(ctx.hypothesis_candidates)}"
            )

        return (
            f"Pipeline session `{pipeline_session.session_id[:8]}…` created.\n"
            f"Research question: **{pipeline_session.research_question}**\n"
            "Full pipeline execution coming in Epic 7."
        )
