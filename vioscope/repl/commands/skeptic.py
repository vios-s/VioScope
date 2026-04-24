from __future__ import annotations

import json
import shlex
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from vioscope.repl.commands.base import BaseCommand
from vioscope.schemas.pipeline import PipelineConfig, PipelineSession
from vioscope.schemas.research import CritiqueReport, HypothesisRecord, SkepticMode
from vioscope.schemas.writing import DraftSection, JournalTemplate


class SkepticCommand(BaseCommand):
    def _parse_skeptic_flags(
        self,
        args: str,
    ) -> tuple[str, str | None, str | None, str | None]:
        try:
            tokens = shlex.split(args)
        except ValueError:
            tokens = args.split()

        positional: list[str] = []
        flag_input: str | None = None
        flag_from_kb: str | None = None
        flag_mode: str | None = None
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
            elif tok == "--mode" and i + 1 < len(tokens):
                flag_mode = tokens[i + 1]
                i += 2
            elif tok.startswith("--mode="):
                flag_mode = tok[len("--mode=") :]
                i += 1
            else:
                positional.append(tok)
                i += 1

        return " ".join(positional), flag_input, flag_from_kb, flag_mode

    def _infer_mode(self, flag_mode: str | None) -> SkepticMode | None:
        if flag_mode:
            try:
                return SkepticMode(flag_mode.lower())
            except ValueError:
                return None
        if self.ctx.draft_sections:
            return SkepticMode.MANUSCRIPT
        if self.ctx.selected_hypothesis or self.ctx.hypothesis_candidates:
            return SkepticMode.HYPOTHESIS
        return None

    def _session_hypothesis(self) -> HypothesisRecord | None:
        if self.ctx.selected_hypothesis is not None:
            return self.ctx.selected_hypothesis
        if not self.ctx.hypothesis_candidates:
            return None
        return sorted(
            self.ctx.hypothesis_candidates,
            key=lambda candidate: candidate.rank or 10_000,
        )[0]

    def _session_draft_sections(self) -> list[DraftSection]:
        sections: list[DraftSection] = []
        for idx, content in enumerate(self.ctx.draft_sections, start=1):
            sections.append(
                DraftSection(
                    name=f"Section {idx}",
                    content=content,
                    template=JournalTemplate.NATURE,
                    section_order=idx,
                )
            )
        return sections

    def _load_input_payload(
        self,
        mode: SkepticMode,
        flag_input: str | None,
        flag_from_kb: str | None,
    ) -> tuple[HypothesisRecord | None, list[DraftSection]]:
        if flag_from_kb:
            raise ValueError(
                "KB-backed `/skeptic` input is not implemented yet. Use session context or --input."
            )

        if mode is SkepticMode.HYPOTHESIS:
            hypothesis = self._session_hypothesis()
            if hypothesis is not None and flag_input is None:
                return hypothesis, []
        else:
            sections = self._session_draft_sections()
            if sections and flag_input is None:
                return None, sections

        if not flag_input:
            return None, []

        raw = json.loads(Path(flag_input).read_text(encoding="utf-8"))
        if mode is SkepticMode.HYPOTHESIS:
            if isinstance(raw, dict) and "selected_hypothesis" in raw:
                raw = raw["selected_hypothesis"]
            elif isinstance(raw, dict) and "hypothesis_candidates" in raw:
                candidates = raw["hypothesis_candidates"]
                if isinstance(candidates, list) and candidates:
                    raw = candidates[0]
            return HypothesisRecord.model_validate(raw), []

        if isinstance(raw, dict) and "draft_sections" in raw:
            raw = raw["draft_sections"]
        if not isinstance(raw, list):
            raise ValueError("Draft sections payload must be a JSON list.")
        sections = []
        for idx, item in enumerate(raw, start=1):
            if isinstance(item, str):
                sections.append(
                    DraftSection(
                        name=f"Section {idx}",
                        content=item,
                        template=JournalTemplate.NATURE,
                        section_order=idx,
                    )
                )
            else:
                sections.append(DraftSection.model_validate(item))
        return None, sections

    def run(self, args: str) -> str:
        positional, flag_input, flag_from_kb, flag_mode = self._parse_skeptic_flags(args)
        mode = self._infer_mode(flag_mode)
        if flag_mode and mode is None:
            return "Unsupported Skeptic mode. Use `--mode hypothesis` or `--mode manuscript`."
        if mode is None:
            return (
                "No Skeptic target found. Provide `--mode hypothesis` with hypothesis context, "
                "`--mode manuscript` with draft sections, or use `--input <file>`."
            )
        if self.agents is None:
            return "Agents not initialized — restart the session."

        try:
            hypothesis, draft_sections = self._load_input_payload(mode, flag_input, flag_from_kb)
        except FileNotFoundError:
            return f"File not found: {flag_input}"
        except json.JSONDecodeError:
            return "Skeptic input file must contain valid JSON."
        except ValidationError:
            if mode is SkepticMode.HYPOTHESIS:
                return "Input must contain a valid HypothesisRecord JSON object."
            return "Input must contain draft sections as a JSON list or a `draft_sections` field."
        except ValueError as exc:
            return str(exc)

        session = PipelineSession(
            session_id=self.ctx.session_id,
            research_question="(interactive session)",
            created_at=datetime.now(timezone.utc),
            config=PipelineConfig(),
            synthesis=self.ctx.synthesis,
            hypothesis_candidates=self.ctx.hypothesis_candidates or None,
            selected_hypothesis=hypothesis or self.ctx.selected_hypothesis,
            draft_sections=draft_sections or None,
        )

        try:
            if mode is SkepticMode.HYPOTHESIS:
                critique = self.agents.skeptic.critique_hypothesis(
                    session,
                    hypothesis=hypothesis,
                    additional_constraints=[positional] if positional else None,
                )
            else:
                critique = self.agents.skeptic.critique_manuscript(
                    session,
                    draft_sections=draft_sections or None,
                    additional_constraints=[positional] if positional else None,
                )
        except RuntimeError as exc:
            return f"Skeptic agent unavailable: {exc}"
        except ValueError as exc:
            return str(exc)

        self.ctx.critique_reports.append(critique)

        return self._render_result(critique)

    def _render_result(self, critique: CritiqueReport) -> str:
        lines = ["## Skeptic Complete", ""]
        lines.append(f"**Mode:** {critique.mode.value}")
        lines.append(f"**Verdict:** {critique.verdict.value}")
        if critique.target_id:
            lines.append(f"**Target:** {critique.target_id}")
        lines.append("")
        lines.append(critique.rationale)
        if critique.issues:
            lines.append("")
            lines.append("**Issues:**")
            for issue in critique.issues:
                lines.append(f"- {issue}")
        if critique.recommendations:
            lines.append("")
            lines.append("**Recommendations:**")
            for recommendation in critique.recommendations:
                lines.append(f"- {recommendation}")
        lines.append("")
        lines.append("Critique saved to session.")
        return "\n".join(lines)
