from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class SessionCommand(BaseCommand):
    def run(self, args: str) -> str:
        ctx = self.ctx
        lines = [f"## Session `{ctx.session_id[:8]}…`", ""]

        lines.append(f"**Papers found:** {len(ctx.papers_found)}")
        lines.append(f"**Papers screened:** {len(ctx.papers_screened)}")

        if ctx.synthesis:
            gaps = len(ctx.synthesis.research_gaps)
            methods = len(ctx.synthesis.method_taxonomy)
            lines.append(f"**Synthesis:** complete — {gaps} gaps, {methods} method groups")
        else:
            lines.append("**Synthesis:** not yet run — use `/synth`")

        if ctx.hypothesis_candidates:
            lines.append(f"**Hypothesis candidates:** {len(ctx.hypothesis_candidates)}")
            for hyp in ctx.hypothesis_candidates[:3]:
                lines.append(f"  - {hyp.title}")
        else:
            lines.append("**Hypothesis candidates:** none — use `/spark`")

        if ctx.selected_hypothesis:
            lines.append(f"**Selected hypothesis:** {ctx.selected_hypothesis.title}")
        else:
            lines.append("**Selected hypothesis:** none")

        if ctx.draft_sections:
            lines.append(f"**Draft sections:** {len(ctx.draft_sections)}")
        else:
            lines.append("**Draft sections:** none — use `/scribe`")

        lines.append("")
        lines.append("Use `/pipeline` to hand off to the full 15-stage pipeline.")

        return "\n".join(lines)
