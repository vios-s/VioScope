from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand


class KBCommand(BaseCommand):
    def run(self, args: str) -> str:
        positional, _flag_input, _flag_from_kb = self._parse_flags(args)
        query = positional.strip().strip("\"'")
        if not query:
            return "Usage: /kb <query>  Search the local knowledge base."

        try:
            from vioscope.kb import LocalKB

            kb = LocalKB()
            results = kb.search(query=query, limit=5)
        except Exception as exc:
            return f"KB search failed: {exc}"

        if not results:
            return f"No KB entries found for: **{query}**"

        lines = [f"## KB Results for: **{query}**", ""]
        for record in results:
            snippet = record.content_snippet.replace("\n", " ")[:200]
            lines.append(f"**[{record.record_type}]** `{record.record_id}` — {snippet}")

        return "\n".join(lines)
