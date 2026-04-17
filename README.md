# VioScope

**An interactive AI research agent for the VIOS Lab (University of Edinburgh)**

VioScope is a conversational research assistant that researchers direct through natural language and slash commands — similar to how developers use Claude Code. You open a session, tell it what you need, and it routes your intent to the right agent. You stay in control; agents do the legwork.

> **Status:** Active development. Core infrastructure, Scout, Synth, and local KB are complete. The interactive REPL layer, Spark, Skeptic, Scribe, and Steward are next.

---

## How It Works

Start a session and talk to it:

```
$ vioscope
VioScope 0.1.0 — interactive research session
Type /help for commands, or describe what you need.

> /scout "foundation models for retinal vessel segmentation 2024-2025"
  Scout › searching arXiv, PubMed, Semantic Scholar, OpenAlex... found 52 papers.

> which papers use SAM or SAM2?
  → 8 papers match. [table shown]

> /synth --papers screened
  Synth › synthesising 40 papers... SynthesisReport ready.

> /spark --constraints "single-GPU reproducible"
  Spark › Innovator / Pragmatist / Contrarian debate... 3 candidates generated.

> /skeptic
  Skeptic (Mode A) › Candidate 2 fails feasibility. PIVOT triggered.

> /spark --additional-constraint "no clinical trial data"
  Spark › 2 revised candidates. Both pass review.

> /scribe --template neurips --hypothesis 1
  Scribe › drafting NeurIPS outline and introduction...

> /steward --action store
  Steward › archived to local KB. GitBook sync complete.
```

Six agents, one session, no pipeline stage management required.

---

## Six Agents

| Agent | Role |
|-------|------|
| **Scout** | Parallel literature search across arXiv, PubMed, Semantic Scholar, OpenAlex — with 4-layer citation verification |
| **Synth** | Distils screened papers into a structured synthesis (method taxonomy, dataset summary, research gaps) |
| **Spark** | Generates hypothesis candidates via an internal 3-role debate (Innovator / Pragmatist / Contrarian) |
| **Skeptic** | Adversarial peer-review critique in two modes: hypothesis critique (Mode A) and manuscript review (Mode B) |
| **Scribe** | Drafts paper sections in NeurIPS, CVPR, MICCAI (LaTeX) or Nature (Markdown) formats |
| **Steward** | Archives research outputs to a local KB and syncs to the VIOS Lab GitBook wiki |

Three **Human Gates** pause for researcher decisions: SCREEN (relevance filtering), SELECT (hypothesis approval), SEAL (quality gate). Everything else runs autonomously.

---

## Two Ways to Use It

### Interactive session (primary)

```bash
vioscope          # enter REPL — slash commands + natural language
```

Slash commands: `/scout`, `/synth`, `/spark`, `/skeptic`, `/scribe`, `/steward`, `/pipeline`, `/kb`, `/session`, `/help`

### One-shot CLI (scripting / automation)

```bash
vioscope research "your question"          # full 15-stage pipeline
vioscope search "query"                    # literature search only
vioscope review --from-kb <id>             # re-run critique on KB record
vioscope write --template neurips          # enter at writing stage
vioscope kb list                           # query local knowledge base
```

---

## Quick Start

### Requirements

- Python 3.11+
- `uv` (recommended) or `pip`
- At least one LLM API key: Anthropic, OpenRouter, or OpenAI

### Install

```bash
git clone https://github.com/vios-s/VioScope.git
cd VioScope

uv venv .venv --python 3.11
source .venv/bin/activate       # Windows: .venv\Scripts\activate

uv pip install -e ".[dev]"
pre-commit install
```

### Configure

```bash
cp config.example.yaml ~/.vioscope/config.yaml

# Set your API key — never put keys in the config file itself
export ANTHROPIC_API_KEY=sk-ant-...

vioscope config validate
```

---

## Project Structure

```
vioscope/
├── repl/            # Interactive REPL: loop, SessionContext, dispatcher, commands/ (coming)
├── agents/          # Scout, Synth (Spark, Skeptic, Scribe, Steward — coming)
├── pipeline/        # agno Workflow: 15-stage orchestration (coming)
├── configs/agents/  # Per-agent YAML defaults
├── core/            # Shared utilities: Rich console singleton, safe_path, circuit breaker
├── kb/              # Local KB markdown store + atomic session store
├── schemas/         # Pydantic v2: SynthesisReport, PipelineSession, DraftSection, etc.
└── tools/           # External API tools: Semantic Scholar, OpenAlex, citation verify
```

---

## Contributing

All contributions welcome — bug fixes, open stories, or design feedback.

### Development Workflow

1. **Find a story** — open stories are in [`_bmad-output/planning-artifacts/stories/`](_bmad-output/planning-artifacts/stories/), tracked in [`_bmad-output/implementation-artifacts/sprint-status.yaml`](_bmad-output/implementation-artifacts/sprint-status.yaml). Epics 5–11 are all open.

2. **Branch** from `main`: `feature/<description>` or `fix/<description>`

3. **Read the project context** — [`_bmad-output/project-context.md`](_bmad-output/project-context.md) is the authoritative guide for conventions and anti-patterns

4. **Test** before opening a PR:
   ```bash
   pytest                    # coverage runs automatically
   mypy vioscope             # strict type checking
   ruff check vioscope       # linting
   ```

5. **Open a PR** targeting `main`. Pre-commit hooks (ruff → ruff-format → black) run on commit — never use `--no-verify`.

### Key Conventions

- **Type annotations are mandatory** — `mypy disallow_untyped_defs = True`
- **agno framework** — use built-in `ArxivTools`, `PubmedTools`, `Workflow`, `Team`. Do not reimplement
- **Structured output** — `output_schema=PydanticModel` only, never parse LLM JSON manually
- **File safety** — all file operations through `safe_path()`
- **No secrets in code** — API keys from env vars only; constants in `vioscope/config.py` only
- **Rich console** — singleton at `vioscope/core/ui.py`; never instantiate `Console()` elsewhere

### What's Needed Now

Highest-priority open work:

| Epic | Story | Description |
|------|-------|-------------|
| E11 | S1 | REPL loop + `SessionContext` |
| E11 | S2 | Slash command dispatcher + all agent commands |
| E11 | S3 | Natural language intent router |
| E5  | S1 | Spark sub-agents + `HypothesisCandidate` schema |
| E5  | S2 | Spark broadcast team (`Team(mode="broadcast")`) |
| E6  | S1–S2 | Skeptic agent (Mode A + B) |

Story specs: [`_bmad-output/planning-artifacts/stories/`](_bmad-output/planning-artifacts/stories/)

---

## Architecture

- **PRD** — [`_bmad-output/planning-artifacts/prd.md`](_bmad-output/planning-artifacts/prd.md)
- **Architecture** — [`_bmad-output/planning-artifacts/architecture.md`](_bmad-output/planning-artifacts/architecture.md)
- **Epics & Stories** — [`_bmad-output/planning-artifacts/epics.md`](_bmad-output/planning-artifacts/epics.md)

Key decisions: agno multi-agent framework · Typer + Rich terminal UI · Pydantic v2 · LanceDB local KB · GitBook sync (MCP read, REST write)

---

## License

See [LICENSE](LICENSE).

## Contact

- **VIOS Lab** — University of Edinburgh
- **Maintainer** — Yuyang Xue ([yuyang.xue@ed.ac.uk](mailto:yuyang.xue@ed.ac.uk))
- **Issues** — [GitHub Issues](https://github.com/vios-s/VioScope/issues)
