from __future__ import annotations

import re
from typing import TYPE_CHECKING

from vioscope.repl.context import SessionContext

if TYPE_CHECKING:
    from vioscope.repl.agents import AgentBundle

_INTENT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(search|find|look\s+for|papers?|literature|articles?|studies)\b", re.I),
        "scout",
    ),
    (
        re.compile(
            r"\b(synthesize?[ds]?|synthesis|summari[sz]e?[ds]?|summary|overview|landscape)\b", re.I
        ),
        "synth",
    ),
    (
        re.compile(r"\b(hypothesis|hypothes[ei]s|idea|spark|generat|novel|conjecture)\b", re.I),
        "spark",
    ),
    (
        re.compile(r"\b(critiqu|review|skeptic|adversari|weakness|flaw|challenge)\b", re.I),
        "skeptic",
    ),
    (re.compile(r"\b(write|draft|scribe|section|paper|manuscript|outline)\b", re.I), "scribe"),
    (re.compile(r"\b(save|store|steward|archive|gitbook|sync|upload)\b", re.I), "steward"),
    (re.compile(r"\b(kb|knowledge\s+base|retrieve|recall|what\s+do\s+i\s+know)\b", re.I), "kb"),
    (re.compile(r"\b(session|status|progress|what\s+have|so\s+far|context)\b", re.I), "session"),
    (re.compile(r"\b(pipeline|full\s+run|workflow|automat)\b", re.I), "pipeline"),
    (re.compile(r"\b(help|commands?|what\s+can|how\s+do)\b", re.I), "help"),
]

_QUIT_PATTERNS = re.compile(r"\b(quit|exit|bye|goodbye|stop|end\s+session)\b", re.I)


def _classify_intent(text: str) -> str | None:
    if _QUIT_PATTERNS.search(text):
        return "quit"
    scores: dict[str, int] = {}
    for pattern, intent in _INTENT_PATTERNS:
        if pattern.search(text):
            scores[intent] = scores.get(intent, 0) + 1
    if not scores:
        return None
    return max(scores, key=lambda k: scores[k])


def nl_router(raw_input: str, ctx: SessionContext, agents: AgentBundle | None) -> str:
    """Classify natural language intent and delegate to the appropriate command.

    Returns a string result (same contract as BaseCommand.run).
    """
    from vioscope.repl.dispatcher import COMMAND_REGISTRY

    intent = _classify_intent(raw_input)

    if intent is None:
        return (
            "I'm not sure what you'd like to do. Try describing your intent more specifically, "
            "or type `/help` to see available commands."
        )

    if intent == "quit":
        return ""

    cmd_cls = COMMAND_REGISTRY.get(intent)
    if cmd_cls is None:
        return f"Understood intent: **{intent}**, but no command is registered yet."

    # For scout, pass the original text as the query
    if intent == "scout":
        return cmd_cls(ctx, agents).run(raw_input)

    # For kb, pass the original text as the query
    if intent == "kb":
        return cmd_cls(ctx, agents).run(raw_input)

    # For other commands, run with no positional args (they read from ctx)
    return cmd_cls(ctx, agents).run("")
