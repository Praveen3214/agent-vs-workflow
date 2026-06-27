# Decision Doc — Why a Workflow, Not an Agent

*Competitive-Research Brief Generator. This is the primary deliverable: the build exists to make this argument concrete and measurable.*

---

## TL;DR

The task has **known, fixed steps** (gather → summarise → structure → format). When you already know the steps, a **deterministic workflow** beats an autonomous agent on every axis that matters here. I built both and measured them on real inputs. The headline findings:

- 💰 **~3.2× cheaper** on a clean run (measured: workflow **$0.00068** vs agent **$0.00216** for the same Notion brief), and **~1.4× faster** (21.6s vs 30.1s).
- 🧱 **Bounded by construction.** The workflow uses the premium model for exactly *one* call; the agent uses it on every turn — and in one run its retry loop re-sent its growing context until it **burned ~95K tokens and exhausted the entire free-tier daily budget**. The workflow structurally cannot do that.
- 🛡️ **More robust.** On one of two test companies (Tailscale) the agent's tool-calling **failed outright** — 4 malformed-call attempts, then it gave up and produced an **ungrounded brief with zero sources**. The workflow completed normally on the same input.

I would switch to an agent only when the *path itself* becomes unknown — Section 6 lists the exact conditions that flip the decision.

The senior principle underneath: **default to the simplest thing that works, and make the upgrade trigger explicit.**

> *Note on honesty: my pre-build estimate guessed ~8× on cost. The measured clean-run gap is ~3.2×. I've kept the real number — and the agent's **reliability** and **budget-blowup** failures turned out to be the stronger argument than raw cost anyway.*

---

## 1. The decision

| | **Workflow (chosen)** | **Agent (built for contrast)** |
|---|---|---|
| Control flow | Fixed Python pipeline; LLM only fills text inside predefined steps | LLM decides which tool to call, how often, when to stop |
| Predictability | High — same steps every run | Low — step count varies per run |
| Cost ceiling | Structural (fixed call count) | Needs explicit caps or it can run away |
| Model usage | **Tiered**: cheap 8B for bulk summarising, smart 70B for final synthesis | 70B for the whole loop (must reason about tool choice every turn) |
| Debuggability | Inspect/replay any single step | Must trace a non-deterministic trajectory |
| Best when | **Steps are known in advance** ✅ (our case) | Steps are discovered at runtime |

For *this* task the steps are knowable before we run anything, so the workflow's rigidity is a feature, not a limitation.

---

## 2. Why the workflow is cheaper — the mechanism

Three structural reasons, all of which the measured numbers (Section 4) confirm:

1. **Model tiering.** The workflow sends the *easy* job — condensing one page into bullet facts — to `llama-3.1-8b-instant` at **$0.05 / $0.08** per million tokens, and reserves `llama-3.3-70b-versatile` (**$0.59 / $0.79**) for the one step that needs real reasoning: the final synthesis. That's a **~12× cheaper rate** on the bulk of the token volume. The agent can't easily do this — it needs the strong model on every turn to decide its next tool call.

2. **No context re-processing.** The workflow passes each page through the model **once**. The agent carries a **growing message history** — every fetched page stays in context and is re-sent (and re-billed) on every subsequent turn. Input tokens grow roughly quadratically with the number of steps.

3. **Fixed call count.** The workflow makes exactly *N summaries + 1 synthesis* calls. The agent's call count is variable and only bounded by the caps we bolt on.

### Worked cost model (measured, Notion brief)

> Real numbers from `python cli.py benchmark --company "Notion"`. Both engines, same input, same day.

**Workflow** — $0.00068, 2,904 tokens, 5 LLM calls
- 4 × summary on **8B** + 1 × synthesis on **70B**. The bulk of the tokens are billed at the 8B rate ($0.05/$0.08); only the single synthesis call pays the 70B rate.

**Agent** — $0.00216, 3,519 tokens, 2 LLM calls (6 tool calls), **all on 70B**
- Similar *token count* to the workflow — but every token is billed at the **premium 70B rate**, so the cost is **3.2× higher** for an equivalent brief.

**The mechanism, confirmed:** on this task the two use comparable token volumes, so the cost gap is driven almost entirely by **model tiering** — a lever the workflow can pull (cheap model for the easy 80% of the work) and the agent cannot (it needs the strong model to choose its next tool reliably). The "no context re-processing" and "fixed call count" advantages don't show up much on a *clean* short run — but they dominate the **tail**, which is where the agent actually hurts (next section).

### The tail risk the average hides

Averages flatter the agent. Two real failures from the same test session:

1. **Budget blow-up (token re-processing, realised).** In one 70B agent run, the model emitted malformed tool calls; each retry re-sent the **entire growing conversation** on the premium model. It consumed **~95,000 tokens in a single run** and **exhausted Groq's 100K-tokens/day free-tier cap** — locking the model for the rest of the day. The workflow's premium-model usage is one bounded call (~1–2K tokens); it never approaches the cap. *(This is also why this doc's numbers were gathered across two days' worth of free quota.)*

2. **Total tool-calling failure.** On **Tailscale**, the agent's tool calls failed Groq's format validation **4 times in a row**; it gave up and emitted a brief with **0 sources read** — i.e. an ungrounded, potentially hallucinated answer. The workflow read its sources and produced a cited brief on the identical input. An autonomous agent is only as reliable as its weakest tool-call; a workflow that *calls the tools itself* removes that failure mode entirely.

---

## 3. Latency

**Measured (Notion): workflow 21.6s vs agent 30.1s — agent ~1.4× slower.**

- **Workflow:** the summary calls go to the *fast* 8B model (≈840 tok/s on Groq); only the single 70B synthesis is on the critical path. Network fetches dominate wall time.
- **Agent:** every turn is a 70B call (≈394 tok/s) and turns are **strictly sequential** — the model must see turn *k*'s tool result before it can plan turn *k+1*. Slower model × premium-only × growing context = consistently higher wall time when it works.
- **Caveat in the data:** on Tailscale the agent was *faster* (2.6s) — but only because it **failed fast and gave up**. Lower latency from doing less work is not a win. This is exactly why latency must be read next to a success/quality check, never alone.

---

## 4. Measured results

Both engines, same input, real Groq calls. Reproduce with `python cli.py benchmark --company "<name>"`. Costs are notional (Groq free tier bills $0) computed from published per-token rates in `config.py`.

### Notion — both engines succeed (the "good case")

| Metric | Workflow | Agent | Agent ÷ Workflow |
|---|---|---|---|
| LLM calls | 5 | 2 | 0.4× |
| Tool calls | 4 | 6 | 1.5× |
| Total tokens | 2,904 | 3,519 | 1.2× |
| **Cost (USD)** | **$0.00068** | **$0.00216** | **3.2×** |
| **Wall time (s)** | **21.6** | **30.1** | **1.4×** |

Even when the agent works perfectly, it costs **3.2×** more and runs **1.4×** slower for an equivalent brief — purely because it can't tier down to the cheap model.

### Tailscale — the agent fails (the case averages hide)

| Metric | Workflow | Agent | Note |
|---|---|---|---|
| LLM calls | 5 | 1 | |
| Tool calls | 4 | **0** | agent read **no sources** |
| Total tokens | 4,746 | 383 | |
| Cost (USD) | $0.00102 | $0.00026 | agent "cheap" only because it gave up |
| Wall time (s) | 11.2 | 2.6 | |
| Outcome | ✅ cited brief | ❌ **4 malformed tool calls → ungrounded answer** | |

The agent's tool-calling failed Groq's format validation 4 times, hit the retry ceiling, and emitted a brief with no sources. **A cheaper, faster number here is worse, not better** — it bought a useless result.

### Plus: the budget blow-up (observed, not in the table)

A separate 70B agent run's malformed-call retries re-sent its growing context until it consumed **~95,000 tokens** and tripped the **100K-tokens/day free-tier ceiling**, locking the model for hours. Workflow runs use ~1–2K premium-model tokens each and never came close.

> Raw rows for every run are in [`benchmarks/runs.csv`](benchmarks/runs.csv); sample briefs are in [`examples/`](examples/).

---

## 5. Failure modes & the guardrail for each

| # | Failure mode | Guardrail (where it lives) |
|---|---|---|
| 1 | Search returns nothing / DuckDuckGo rate-limits | Fall back to user-supplied URLs; if still empty, return an **honest empty brief** instead of fabricating — `workflow.py`, `search.py` |
| 2 | Page paywalled / unreadable | `fetch_url` fails safe and is skipped; run continues with remaining sources — `search.py` |
| 3 | Model invents facts not in sources | "Use ONLY the provided notes" system prompts + **required source citations** — `workflow.py`, `agent.py` |
| 4 | Sources contradict each other | Synthesis prompt must surface disagreement in a **`caveats`** field rather than silently picking one |
| 5 | Thin / low-confidence coverage | `caveats` field states the gap instead of padding the brief |
| 6 | **Agent cost runaway** | Hard **step cap, tool-call cap, and token budget** abort the loop — `config.py`, `agent.py` |
| 7 | Model returns malformed JSON | Tolerant parser with graceful fallback — `brief.py`, `agent.py` |
| 8 | Input token blow-up from huge pages | `MAX_CHARS_PER_SOURCE` / `MAX_SOURCES` truncation — `config.py` |

Note that **failure mode #6 only exists for the agent.** The workflow's cost is bounded by its structure; the agent needs explicit caps to get the same guarantee. That asymmetry *is* the argument.

---

## 6. When I *would* switch to an agent

The decision flips when the **path stops being knowable in advance**. Concretely, I'd reach for an agent when:

1. **The next step depends on what the last step found.** e.g. *"If it's a public company, pull the 10-K; if it's a startup, find the latest funding round; if it's open-source, read the GitHub activity."* Many conditional branches that we can't reasonably pre-wire.
2. **The tool/sub-task space is large and dynamic** — dozens of possible tools where hard-coding every routing rule costs more (in engineering and maintenance) than letting the model route.
3. **Open-ended exploration** where success means following leads we can't enumerate up front.
4. **Recovery from novel obstacles** is worth paying for — the agent can improvise around a blocker a fixed pipeline would just fail on.

**Hybrid is often the real answer:** use an agent (or an LLM router) for the *unknown* branching at the top, and call **deterministic workflows** for each *known* sub-task underneath. You get adaptability where you need it and predictability/cost-control everywhere else.

For the competitive-brief task as scoped, none of conditions 1–4 hold — so the workflow is the right default, and this doc is the receipt.

---

## 7. What this demonstrates (the senior signal)

- I can build the agentic version — but I can also **argue when not to**, with cost, latency, and failure analysis behind the call.
- I made the **cost levers explicit** (model tiering, single-pass context, fixed call count) rather than treating "use an LLM" as one undifferentiated thing.
- I put **real guardrails** on the open-ended path and showed that the bounded path doesn't need them.
- I wrote down the **upgrade trigger** so the decision is revisitable, not dogmatic.
