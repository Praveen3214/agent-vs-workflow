<!-- The block below is config for Hugging Face Spaces (ignored on GitHub). See DEPLOY.md. -->
---
title: Competitive Research Brief Generator
emoji: 📰
colorFrom: teal
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Competitive-Research Brief Generator — Workflow vs Agent

Generate a clean, sourced, one-page competitive brief from a single input
(a company or topic). Built **two ways** — a deterministic **workflow** and a
minimal autonomous **agent** — to make one point with real numbers:

> **When the steps are known in advance, a fixed workflow beats an autonomous
> agent — cheaper, faster, and bounded by construction.**

The headline deliverable is **[`DECISION_DOC.md`](DECISION_DOC.md)**, which
backs that claim with measured cost, latency, and failure-mode analysis. The
tool exists to make the argument concrete.

> Portfolio build by an AI Program Manager. The judgment call — *workflow vs
> agent* — is the point; the code is the evidence.

---

## Problem statement

**1. The everyday problem — company research is slow, manual, and repetitive.**
To understand a competitor, sales prospect, or investment, someone has to open a
dozen tabs, skim long pages, copy-paste the useful bits, organise it into
something readable, and track where each fact came from. That's 30–60 minutes of
tedious work per company, and the result is inconsistent every time. **This tool
turns one company name into a clean, sourced one-page brief in seconds.**

**2. The deeper problem — teams over-use autonomous "AI agents" and can't tell when they're the wrong choice.**
Agents (AI that decides its own steps) are hyped, but for tasks whose steps are
already known they're often more expensive, slower, and less reliable than a
simple fixed sequence of steps (a *workflow*) — yet teams reach for the agent
anyway, burning cost and trust. **This project builds the same task both ways,
measures them, and shows — with real numbers — when the simpler workflow wins.**
The working tool is the evidence; the [`DECISION_DOC.md`](DECISION_DOC.md) is the
deliverable.

---

## What it does

Input a subject → the tool searches the web (free, via DuckDuckGo) and/or reads
URLs you supply → summarises each source → synthesises a structured, **sourced**
brief. It supports four **subject types** (`--kind`), each with tailored sections:

| `--kind` | Subject | Sections |
|---|---|---|
| `company` *(default)* | A company | Overview · Products · Positioning · Recent News |
| `leader` | A political leader | Background & Role · Policy Positions · Recent Activity · Different Perspectives |
| `party` | A political party | Overview · Platform · Key Figures · Recent News · Different Perspectives |
| `topic` | Any topic / current event | What It Is · Key Facts · Different Perspectives · Recent Developments |

All briefs end with **Caveats** and **Sources**. Every run prints its own
**cost, tokens, and wall-time**, so the workflow-vs-agent difference is visible
on every brief.

> **Sensitive subjects** (leaders, parties, topics) are handled with guardrails:
> the model is told to stay strictly neutral, attribute every claim to a source
> ("according to …"), surface disagreement instead of taking a side, and each such
> brief carries a visible *"AI-generated — verify before relying"* disclaimer.
> This is summarisation of public information, not persuasion or campaign content.

---

## Quickstart (≈5 minutes)

**Prerequisites:** Python 3.10+ and a free Groq API key
([console.groq.com/keys](https://console.groq.com/keys) — no credit card).

```bash
# 1. Install
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Add your key
copy .env.example .env          # macOS/Linux: cp .env.example .env
#   then edit .env and paste your GROQ_API_KEY

# 3. Generate a brief (deterministic workflow)
python cli.py run --mode workflow --company "Notion" --out examples/notion.md

# 4. Same task, autonomous agent
python cli.py run --mode agent --company "Notion"

# 5. Run BOTH and compare — this feeds the decision doc
python cli.py benchmark --company "Notion"
```

`benchmark` writes a paste-ready comparison table to `benchmarks/latest.md` and
appends raw rows to `benchmarks/runs.csv`.

### Other subject types (`--kind`)

```bash
python cli.py run --kind topic   --company "electric vehicle adoption"
python cli.py run --kind leader  --company "<a political leader's name>"
python cli.py run --kind party   --company "<a political party's name>"
```

(`--company` is just the subject field — it takes any name/topic regardless of kind.)

### Supplying your own URLs (skip search, full reproducibility)

```bash
python cli.py run --mode workflow --company "Notion" --url https://en.wikipedia.org/wiki/Notion_(productivity_software) --url https://www.notion.com/about
```

> On **Windows PowerShell**, keep each command on one line — `\` is not a line
> continuation there (use a backtick `` ` `` if you must split). The commands
> above are single-line and work in PowerShell, CMD, and bash.

---

## Web UI (optional, the showcase layer)

A clean single-page interface over the **same engine** — toggle Workflow/Agent
and watch cost & latency update live.

```bash
uvicorn webapp.app:app --reload
# open http://127.0.0.1:8000
```

The FastAPI backend is deliberately thin: it reuses `briefgen.run_workflow` /
`run_agent` verbatim. Engine and interface are cleanly separated — the measured
core is never duplicated.

### Run it live for other people

The same app deploys as a public demo on **Hugging Face Spaces** (Docker). It
gives each visitor **4 free briefs** on your shared key, then asks them to paste
**their own free Groq key** to continue — so it stays effectively free for you and
can't run up a bill (your shared key is a free-tier key Groq caps at 100K
tokens/day). Step-by-step in **[`DEPLOY.md`](DEPLOY.md)**.

---

## How it's built

```
briefgen/                 the engine (shared by CLI and web UI)
├── config.py             model IDs, real Groq pricing, guardrail caps
├── llm.py                Groq wrapper — records tokens/cost/latency on every call
├── search.py             DuckDuckGo search + robust page-text extraction
├── metrics.py            per-call + per-run instrumentation, CSV logging
├── brief.py              the structured-brief schema + markdown rendering
├── workflow.py           ← THE WORKFLOW: gather → summarise(8B) → synthesise(70B)
└── agent.py              ← THE AGENT: tool-calling loop with hard caps
cli.py                    run / benchmark commands
webapp/                   FastAPI + Tailwind single-page UI
DECISION_DOC.md           ⭐ the primary deliverable
examples/                 sample generated briefs
benchmarks/               measured runs (generated)
```

**The two engines differ only in orchestration**, on purpose: both call the same
LLM wrapper, the same search tools, and emit the same brief schema — so the
comparison isolates *workflow vs agent*, nothing else.

| | Workflow | Agent |
|---|---|---|
| Control flow | Fixed pipeline | LLM-driven tool loop |
| Models | 8B (summarise) + 70B (synthesise) | 70B throughout |
| Cost ceiling | Structural | Enforced by step/token caps |
| Best for | Known steps (this task) | Unknown / branching paths |

---

## Guardrails

- **No fabrication:** if no sources are readable, it returns an honest empty
  brief rather than inventing one.
- **Citations required** and contradictions surfaced in a `Caveats` section.
- **Cost caps:** input truncation, max sources, and — for the agent —
  step / tool-call / token budgets that abort a runaway loop.

See [`DECISION_DOC.md`](DECISION_DOC.md) §5 for the full failure-mode table.

---

## Notes

- **Cost is notional.** Groq's free tier bills $0; reported costs are computed
  from Groq's published per-token rates (in `config.py`) so the comparison is
  meaningful. Update those rates / model IDs in one place if they drift.
- **DuckDuckGo can rate-limit.** If search returns nothing, supply `--url`s.
- No secrets are committed; `.env` is git-ignored. MIT licensed.
