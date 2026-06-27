# Project Brief — "Agent vs Workflow" Build
*Portfolio build for an AI Program Manager. This file is the COMPLETE spec — the chat you paste it into has no other context.*

## How to use this
1. Create a new empty folder (e.g. `research-brief-agent`).
2. Copy this file into it as `BRIEF.md`.
3. Open Claude Code there and paste the **Kickoff prompt** (bottom) as your first message.

## Read first, Claude — who I am & the rules
- I'm an **AI Program Manager**, not a hands-on engineer. **You write all the code**; I make the design / cost / autonomy decisions. Explain choices in plain English.
- This is a **portfolio piece** to show I understand agentic AI **and the judgment of when NOT to use an agent**. The most important output is the **decision document**, not just a working tool.
- Keep it **public-safe**: neutral inputs, no secrets committed, MIT license, clean README.
- My machine: Windows 11, 32 GB RAM, **no GPU**. Prefer free tiers.

## Goal
An AI tool that completes a real **multi-step task**, built as a **deterministic workflow**, accompanied by a **decision doc** that argues *why a workflow beats an autonomous agent here* — with cost, latency, and failure-mode analysis.

## Default task (swap if you suggest better)
**Competitive-Research Brief Generator** — input a company or topic → the tool gathers information (web search, or a provided list of source URLs to avoid paid APIs) → reads/summarizes → outputs a structured **1-page brief** (overview, products, positioning, recent news, sources).
(Equally fine: *Support-Ticket Triage* — classify an incoming ticket, route it, draft a reply.)

## What to build
1. A **fixed workflow**: defined steps (gather → read/summarize → structure → format), each with a focused prompt.
2. **Tool use** where needed (web search via a free option like DuckDuckGo, or accept user-supplied URLs).
3. **Structured output** (a clean markdown/PDF brief).
4. **Guardrails**: handle missing/contradictory info; cite sources; cap cost per run.
5. A simple **CLI or Streamlit** interface.
6. (For contrast) a **minimal autonomous-agent version** of the same task, so the comparison is real.

## ⭐ The differentiator — the decision doc (MOST IMPORTANT)
`DECISION_DOC.md` covering:
- **Workflow vs agent** — why I chose a fixed workflow (steps are known → predictable, cheaper, debuggable).
- **Cost per run** (tokens × price) and **latency**, workflow vs agent.
- **Failure modes** and the guardrails for each.
- **When I *would* switch to an agent** (the conditions that flip the decision).
This shows the senior signal: *default to the simplest thing that works.*

## Suggested stack (swappable)
Python · an LLM API (Groq free tier / Claude / OpenAI) · a free search option (DuckDuckGo) or user-supplied URLs · Streamlit or CLI · python-dotenv.

## Deliverables
- Working workflow tool + the minimal agent version for contrast.
- `DECISION_DOC.md`, 2–3 sample generated briefs in `examples/`.
- `README.md`, `.env.example`, `requirements.txt`.

## Definition of done
- [ ] Tool produces a clean, sourced brief from a single input.
- [ ] Both workflow and agent versions run; numbers in the decision doc are real (measured, not guessed).
- [ ] `DECISION_DOC.md` clearly justifies the choice with cost/latency/failure analysis.
- [ ] README lets a stranger run it in <10 min; no secrets committed.

## Kickoff prompt (paste as your first message)
> I'm an AI Program Manager building a portfolio project. Read `BRIEF.md` — it's the full spec. I don't code; you write everything and explain decisions. Start by: (1) restating the plan, (2) proposing the exact task + stack + free search approach, and (3) flagging the tradeoffs you need my call on. Build the workflow first, then the minimal agent version, then we measure both for the decision doc.
