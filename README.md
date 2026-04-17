<div align="center">

# VioScope

### Your research, amplified.

**Six agents. Fifteen stages. One researcher in control.**

*Researcher-controlled research augmentation for academic labs — from literature search to hypothesis generation to paper draft to lab knowledge base, in one session.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/vios-s/VioScope)](LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-orange)]()
[![VIOS Lab](https://img.shields.io/badge/VIOS%20Lab-University%20of%20Edinburgh-informational)](https://vios.science)

</div>

---

> **VioScope builds your lab's research memory while you work.**

---

## What VioScope Is

VioScope is a **conversational research agent** you run in your terminal. You direct it through natural language and slash commands — like using Claude Code, but purpose-built for academic research. It routes your intent to the right specialist agent, pauses at every critical decision for your approval, and archives everything to a searchable lab knowledge base.

VioScope **augments** your research. It does not replace your thinking, fabricate results, or write papers without your direction.

---

## See It in Action

```
$ vioscope
╔══════════════════════════════════════════╗
║  VioScope  —  VIOS Lab, Edinburgh        ║
║  Research session · type /help to start  ║
╚══════════════════════════════════════════╝

> /scout "foundation models for retinal vessel segmentation 2024-2025"
  Scout › scanning arXiv · PubMed · Semantic Scholar · OpenAlex...
  Scout › 52 papers found · verifying citations (4-layer)... ✓ 47 verified

> which papers use SAM or SAM2?
  → 8 papers match  [table rendered]

⏸  SCREEN  ─────────────────────────────────────────────────────────────
  47 papers ready. Review and select which to carry forward?
  [y] proceed with all  [s] open selection UI  [n] refine query
  > s
  Selected: 40 papers
─────────────────────────────────────────────────────────────────────────

> /synth --papers screened
  Synth › distilling 40 papers...
  Synth › SynthesisReport ready — 6 method families, 3 open gaps identified

> /spark --constraints "single-GPU reproducible"
  Spark › Innovator / Pragmatist / Contrarian internal debate...
  Spark › 3 hypothesis candidates generated

⏸  SELECT  ─────────────────────────────────────────────────────────────
  Hypothesis 1: Lightweight adapter-based SAM fine-tuning (Feasibility: High)
  Hypothesis 2: Cross-modal prompt distillation (Novelty: High)
  Hypothesis 3: Uncertainty-aware ensemble (Pragmatist preferred)
  Which hypothesis should we pursue? [1/2/3/all]
  > 2
─────────────────────────────────────────────────────────────────────────

> /skeptic
  Skeptic (Mode A) › Methodologist · Skeptic · Pragmatist review...
  Skeptic › ⚠ Hypothesis 2 — insufficient ablation baseline. PIVOT suggested.

> /spark --additional-constraint "must ablate against SAM zero-shot"
  Spark › revised candidate generated · passes Skeptic review

> /scribe --template neurips --hypothesis accepted
  Scribe › drafting NeurIPS outline + introduction section...

> /steward --action store
  Steward › archived to local KB · GitBook sync complete ✓
```

---

## Why VioScope

### You stay in control — always

Three **Human Gates** pause the pipeline at every critical decision:

| Gate | Stage | What you decide |
|------|-------|----------------|
| ⏸ **SCREEN** | After literature search | Which papers are relevant |
| ⏸ **SELECT** | After hypothesis generation | Which direction to pursue |
| ⏸ **SEAL** | After manuscript review | Whether the draft meets your bar |

VioScope does not write papers for you. It writes papers *with* you.

### Citations you can defend

Scout verifies every paper through **four independent layers** before it enters your session:

```
arXiv ID check  →  CrossRef / DataCite DOI  →  title matching  →  LLM relevance score
```

Every citation in a VioScope session carries a provenance trail. No fabricated references reach your draft.

### Your lab builds knowledge, not just outputs

After every session, Steward automatically archives search results, synthesis reports, hypothesis records, and drafts to a **local knowledge base** and syncs to your lab's GitBook wiki. The next researcher to join your lab inherits months of structured research history — not a pile of unorganised notes.

---

## How VioScope Compares

|  | **VioScope** | AutoResearchClaw | Elicit | Claude Code skills |
|--|:---:|:---:|:---:|:---:|
| Full research pipeline | ✅ | ✅ | ❌ | Partial |
| Human Gates (required) | ✅ | Optional | — | — |
| 4-layer citation verify | ✅ | ✅ | Partial | — |
| Lab knowledge base | ✅ GitBook + local | ❌ | ❌ | ❌ |
| Domain plugins | ✅ biomedical, imaging | ❌ | ❌ | ❌ |
| ML experiment execution | ❌ by design | ✅ | — | — |
| Install | `pip install vioscope` | Docker | Web | Claude Code |

**AutoResearchClaw** is a 23-stage autonomous pipeline that includes code generation and experiment execution — it is designed for ML researchers who want the machine to run experiments overnight. VioScope is designed for researchers across all disciplines who want AI assistance on the intellectual parts of research while keeping full ownership of every decision.

**Elicit** is excellent for literature discovery and systematic review. VioScope picks up where Elicit leaves off: from synthesis onwards to hypothesis generation, writing, and lab knowledge archival.

---

## The Six Agents

| Agent | Role |
|-------|------|
| **Scout** | Parallel literature search across arXiv, PubMed, Semantic Scholar, OpenAlex — with 4-layer citation verification |
| **Synth** | Distils screened papers into a structured synthesis: method taxonomy, dataset summary, identified research gaps |
| **Spark** | Generates hypothesis candidates through an internal 3-role debate — Innovator, Pragmatist, Contrarian |
| **Skeptic** | Adversarial peer-review critique in two modes: hypothesis critique (Mode A) and manuscript review (Mode B) |
| **Scribe** | Drafts paper sections in NeurIPS, CVPR, MICCAI (LaTeX) or Nature (Markdown) formats, drawing from the KB |
| **Steward** | Archives research outputs to a local KB and syncs to the lab's GitBook wiki |

---

## The 15-Stage Pipeline

```
Phase A — SCOPE       Stage 1 · SCOPE       Research question initialisation
                      Stage 2 · STRUCTURE   Problem decomposition
                      Stage 3 · STRATEGY    Search strategy planning

Phase B — SEARCH      Stage 4 · SCAN        Multi-database literature retrieval (Scout)
                      Stage 5 · SCREEN ⏸   Relevance filtering — Human Gate
                      Stage 6 · SYNTHESIZE  Knowledge distillation (Synth)

Phase C — SPARK       Stage 7 · SPARK       3-role internal debate → hypotheses
                      Stage 8 · SCRUTINIZE  Adversarial critique (Skeptic)
                                              ↪ PIVOT → back to Stage 7 if needed
                      Stage 9 · SELECT ⏸   Researcher approves hypothesis — Human Gate

Phase D — SCRIBE      Stage 10 · SKETCH     Paper outline (Scribe)
                      Stage 11 · SCRIPT     Section drafts
                      Stage 12 · SIMULATE   3-role simulated peer review (Skeptic)
                                              ↪ PIVOT → back to Stage 7 if hypothesis fails
                      Stage 13 · SHARPEN    Revision based on review feedback
                      Stage 14 · SEAL ⏸    Quality gate — Human Gate

Phase E — STORE       Stage 15 · STORE      KB archival + GitBook sync (Steward)
```

You do not need to manage stages. Open a session, describe your research question, and VioScope handles the routing. At every ⏸ gate, it pauses for you.

---

## Quick Start

### Requirements

- Python 3.11+
- At least one LLM API key (Anthropic Claude recommended — see [LLM Configuration](#llm-configuration))

### Install

```bash
pip install vioscope
```

Or for development:

```bash
git clone https://github.com/vios-s/VioScope.git
cd VioScope
uv venv .venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

### Configure

```bash
vioscope init       # interactive setup wizard — generates ~/.vioscope/config.yaml
```

Or manually:

```bash
cp config.example.yaml ~/.vioscope/config.yaml
export ANTHROPIC_API_KEY=sk-ant-...   # never put keys in the config file
vioscope config validate
```

### Run

```bash
vioscope            # open an interactive research session
```

Slash commands available: `/scout`, `/synth`, `/spark`, `/skeptic`, `/scribe`, `/steward`, `/pipeline`, `/kb`, `/session`, `/help`

### One-shot commands (scripting / automation)

```bash
vioscope research "your research question"     # full 15-stage pipeline
vioscope search "query"                        # literature search only
vioscope review --from-kb <id>                 # re-run critique on a KB record
vioscope write --template neurips              # enter at the writing stage
vioscope kb list                               # query local knowledge base
```

---

## LLM Configuration

VioScope uses [agno](https://github.com/agno-agi/agno)'s multi-provider model abstraction. Each agent can use a different model. The recommended configuration:

| Agent | Recommended model | Why |
|-------|-------------------|-----|
| Scout | `claude-haiku-4-5` | High-throughput search — speed over depth |
| Synth | `claude-sonnet-4-6` | Balanced synthesis quality |
| Spark | `claude-opus-4-6` | Most demanding reasoning — 3-role debate |
| Skeptic | `claude-sonnet-4-6` | Adversarial review |
| Scribe | `claude-sonnet-4-6` | Writing quality |
| Steward | `claude-haiku-4-5` | Lightweight KB sync |

**University of Edinburgh researchers**: If you have access to Claude via the Anthropic Campus Programme, your API key works directly with VioScope.

Alternative providers (OpenAI, Gemini, Ollama for air-gapped use) are supported — see `config.example.yaml`.

---

## Domain Plugins

VioScope's plugin system extends the pipeline for specific research disciplines:

```bash
pip install vioscope-biomedical   # PubMed MeSH deep search, ClinicalTrials, UniProt
pip install vioscope-imaging      # DICOM metadata, medical image datasets (VIOS-specific)
pip install vioscope-plant        # Plant phenotyping databases (Phenotiki integration)
```

Plugins inject domain-specific tools, agent instructions, and KB schemas into your session automatically.

**Building a plugin**: See [plugin development guide](_bmad-output/planning-artifacts/) — the `VioScopePlugin` base class takes ~50 lines to implement.

---

## Project Structure

```
vioscope/
├── repl/            # Interactive REPL: loop, SessionContext, dispatcher, commands/
├── agents/          # Scout, Synth (Spark, Skeptic, Scribe, Steward — in development)
├── pipeline/        # agno Workflow: 15-stage orchestration (in development)
├── configs/agents/  # Per-agent YAML defaults
├── core/            # Shared utilities: Rich console singleton, safe_path, circuit breaker
├── kb/              # Local KB markdown store + atomic session store
├── schemas/         # Pydantic v2: SynthesisReport, PipelineSession, DraftSection, etc.
└── tools/           # External API tools: Semantic Scholar, OpenAlex, citation verify
```

---

## Contributing

All contributions are welcome — bug fixes, open stories, new domain plugins, or design feedback.

### Development workflow

1. **Find a story** — open stories are in [`_bmad-output/planning-artifacts/stories/`](_bmad-output/planning-artifacts/stories/). Epics 5–11 are all open.
2. **Branch** from `main`: `feature/<description>` or `fix/<description>`
3. **Read the project context** — [`_bmad-output/project-context.md`](_bmad-output/project-context.md) covers all conventions
4. **Test** before opening a PR:
   ```bash
   pytest            # coverage runs automatically
   mypy vioscope     # strict type checking
   ruff check vioscope
   ```
5. **Open a PR** targeting `main`. Pre-commit hooks (ruff → ruff-format → black) run automatically.

### What's needed now

| Epic | Story | Description |
|------|-------|-------------|
| E5 | S1–S2 | Spark agent: sub-agents + broadcast team |
| E6 | S1–S2 | Skeptic agent: Mode A (hypothesis) + Mode B (review) |
| E7 | S1–S10 | Full 15-stage agno Workflow orchestration |
| E8 | S1–S4 | Scribe agent: outline, section drafts, revision |
| E9 | S1–S3 | Steward: GitBook MCP read + REST write |
| E10 | S1–S3 | Plugin system: base class, registry, biomedical example |

### Key conventions

- **Type annotations are mandatory** — `mypy disallow_untyped_defs = True`
- **agno framework** — use built-in `ArxivTools`, `PubmedTools`, `Workflow`, `Team`; never reimplement
- **Structured output** — `output_schema=PydanticModel` only; never parse LLM JSON manually
- **File safety** — all file operations through `safe_path()`
- **No secrets in code** — API keys from env vars only; constants in `vioscope/config.py`
- **Rich console** — singleton at `vioscope/core/ui.py`; never instantiate `Console()` elsewhere

---

## Architecture

- **Design document** — [`_bmad-output/DESIGN.md`](_bmad-output/DESIGN.md)
- **PRD** — [`_bmad-output/planning-artifacts/prd.md`](_bmad-output/planning-artifacts/prd.md)
- **Epics & Stories** — [`_bmad-output/planning-artifacts/epics.md`](_bmad-output/planning-artifacts/epics.md)

Key decisions: agno multi-agent framework · Typer + Rich terminal UI · Pydantic v2 · Local KB (markdown + LanceDB) · GitBook sync (official MCP read, custom REST write)

---

## Citation

If VioScope assists your research, please cite:

```bibtex
@software{vioscope2026,
  title   = {VioScope: Researcher-Controlled Multi-Agent Research Augmentation},
  author  = {Xue, Yuyang and {VIOS Lab, University of Edinburgh}},
  year    = {2026},
  url     = {https://github.com/vios-s/VioScope},
}
```

---

## License

See [LICENSE](LICENSE).

## Contact

- **VIOS Lab** — University of Edinburgh · [vios.science](https://vios.science)
- **Maintainer** — Yuyang Xue ([yuyang.xue@ed.ac.uk](mailto:yuyang.xue@ed.ac.uk))
- **Issues** — [GitHub Issues](https://github.com/vios-s/VioScope/issues)
