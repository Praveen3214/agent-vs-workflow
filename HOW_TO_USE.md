# How to Use This Tool

A free tool that turns one input — a **company**, **political leader**, **political party**, or **any topic** — into a clean, **source-cited one-page brief** in seconds. It runs the same task two ways (a deterministic **workflow** and an autonomous **agent**) and shows the cost & speed of each, so you can see *why simpler is often better*.

- 🔗 **Live app:** https://Poly928829-brief-generator.hf.space
- 💻 **Source code:** https://github.com/Praveen3214/agent-vs-workflow
- 🤗 **Hugging Face Space:** https://huggingface.co/spaces/Poly928829/brief-generator

---

## Option 1 — Just use the live app (no setup)

1. Open **https://Poly928829-brief-generator.hf.space**
   *(If it's asleep, the first load takes ~30 seconds to wake up — that's normal for a free host.)*
2. **Pick a Subject type** from the dropdown: Company, Political leader, Political party, or Topic / current event.
3. **Type the name or topic** (e.g. `Notion`, or `electric vehicle adoption`).
4. *(Optional)* Paste **Source URLs**, one per line — useful if search comes up short or you already know the best sources.
5. **Choose the engine:**
   - **Workflow** — fixed, fast, cheap pipeline (recommended).
   - **Agent** — autonomous; it picks its own steps. Try it to see why it costs more.
6. Click **Generate brief**. You'll get a structured brief plus a live **cost / tokens / wall-time** readout.

### Free briefs, then bring your own key
You get **4 free briefs** to try it. After that, the app asks for **your own free Groq key** (instant, no credit card) so you can keep going on your own quota:
1. Get a key at **https://console.groq.com/keys** (it starts with `gsk_`).
2. Paste it into the **"Use my own Groq key"** box in the app. It's stored only in *your* browser and sent only with your request — never saved on the server.

### Tips
- **For people/parties/topics**, the tool stays neutral, attributes every claim to a source ("according to …"), shows different perspectives, and adds a "verify before relying" disclaimer. Treat it as a *starting point*, not a final source of truth.
- **If you see "no sources"**, the free web search was likely rate-limited — paste a couple of URLs (e.g. an official page + a news article) into the Source URLs box.

---

## Option 2 — Run it on your own computer

**Prerequisites:** Python 3.10+ and a free Groq key ([console.groq.com/keys](https://console.groq.com/keys)).

```bash
# 1. Get the code
git clone https://github.com/Praveen3214/agent-vs-workflow.git
cd agent-vs-workflow

# 2. Install
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 3. Add your key
copy .env.example .env          # macOS/Linux: cp .env.example .env
#   then edit .env and paste your GROQ_API_KEY

# 4a. Generate a brief from the command line
python cli.py run --kind company --company "Notion"
python cli.py run --kind topic   --company "electric vehicle adoption"
python cli.py run --kind leader  --company "a leader's name"
python cli.py run --kind party   --company "a party's name"

# 4b. Or run the web app
uvicorn webapp.app:app --reload
#   then open http://127.0.0.1:8000
```

**See the workflow-vs-agent comparison yourself** (runs both, prints a cost/latency table):
```bash
python cli.py benchmark --company "Notion"
```

> On **Windows PowerShell**, keep each command on one line (`\` is not a line-continuation there).

---

## Option 3 — Make it your own (deploy your own copy)

**Easiest — duplicate the Space:** on the [Hugging Face Space](https://huggingface.co/spaces/Poly928829/brief-generator), click the **⋮ menu → "Duplicate this Space"**, then add your own `GROQ_API_KEY` as a **secret**. You'll have your own live copy in minutes.

**From scratch:** see **[DEPLOY.md](DEPLOY.md)** for full Hugging Face Spaces (or Render) instructions.

**Customize it:**
- **Add a new subject type** (e.g. "product", "researcher", "city"): add an entry to `briefgen/kinds.py` with its sections and prompts — both the workflow and agent pick it up automatically.
- **Change models or cost caps:** edit `briefgen/config.py` (model names, token/step/tool caps).
- **Tune the public free-quota:** set `FREE_PER_VISITOR` / `GLOBAL_DAILY_CAP` env vars on your Space.

---

## What's actually happening under the hood

`gather sources → summarize each (cheap model) → synthesize into a structured brief (smart model) → cite`

The interesting part isn't the tool — it's the **decision** behind it. The full measured comparison of *workflow vs autonomous agent* (cost, latency, and real failure modes) is written up in **[DECISION_DOC.md](DECISION_DOC.md)**.

---

## Responsible use

This tool summarizes **public** web information and may be **incomplete or wrong**. For people, parties, and contested topics it is intentionally neutral and source-cited, but it is **not** an authority — always verify against the cited sources before relying on or sharing anything. It is for research and summarization, not persuasion, campaigning, or decisions about real individuals.

---

## Cost

Running it is **free** on Groq's free tier (no charge as long as you stay within the daily limits). The "$" figures shown in the app are *notional* — computed from Groq's published rates to compare the two engines — not money you're charged.
