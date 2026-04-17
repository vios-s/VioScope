from __future__ import annotations

from vioscope.repl.commands.base import BaseCommand

_HELP_TEXT = """\
## VioScope Interactive REPL

**Agent commands:**
| Command | Description |
|---------|-------------|
| `/scout <query>` | Search papers across all configured databases |
| `/synth` | Synthesize screened papers into a structured report |
| `/spark` | Generate hypothesis candidates (Epic 5) |
| `/skeptic` | Adversarial critique of hypotheses or drafts (Epic 6) |
| `/scribe` | Draft or revise paper sections (Epic 8) |
| `/steward` | Archive outputs and sync to GitBook (Epic 9) |

**Session commands:**
| Command | Description |
|---------|-------------|
| `/kb <query>` | Search the local knowledge base |
| `/session` | Inspect current session context |
| `/pipeline` | Promote session to full 15-stage pipeline |
| `/help` | Show this help |
| `/quit` | Exit VioScope |

**Context injection** (when no session context exists):
- `/spark --input ./synthesis.json`
- `/skeptic --from-kb <record-id>`

You can also type **natural language** — VioScope will route to the right command automatically.
"""


class HelpCommand(BaseCommand):
    def run(self, args: str) -> str:
        return _HELP_TEXT
