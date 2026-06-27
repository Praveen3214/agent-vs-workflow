"""
Central configuration: model IDs, pricing, and guardrail caps.

Keeping all of these in one place is itself a "senior" choice — pricing and
model names drift, and the decision doc's cost math must trace back to a single
source of truth. Update PRICING / MODELS here and every number downstream
(CLI, web UI, decision doc benchmark) stays consistent.
"""
from __future__ import annotations

# --- Model IDs (Groq production models) -----------------------------------
# Two tiers on purpose. The workflow routes the *easy* per-source summarisation
# step to the cheap 8B model and reserves the strong 70B model for the final
# synthesis. The autonomous agent uses 70B for the whole loop because it must
# reason about which tool to call next — you cannot easily downshift mid-loop.
MODEL_SMART = "llama-3.3-70b-versatile"   # strong reasoning / synthesis
MODEL_CHEAP = "llama-3.1-8b-instant"      # cheap extraction / summarisation

# --- Pricing (USD per 1,000,000 tokens) -----------------------------------
# Source: https://groq.com/pricing  (captured 2026-06-25).
# Groq's free tier bills $0 in practice; we compute *notional* cost from these
# published on-demand rates so the workflow-vs-agent comparison is meaningful.
PRICING = {
    MODEL_SMART: {"input": 0.59, "output": 0.79},
    MODEL_CHEAP: {"input": 0.05, "output": 0.08},
}

# --- Guardrail caps (the "cap cost per run" requirement) -------------------
MAX_SOURCES = 6              # most URLs we will read in one run
MAX_CHARS_PER_SOURCE = 6000  # truncate each page's text to bound input tokens
SEARCH_RESULTS = 6           # how many search hits to consider

# Agent-only safety rails. An autonomous loop with no ceiling is how you wake
# up to a surprise bill — these are the hard stops.
AGENT_MAX_STEPS = 8          # max reason->act iterations before forced stop
AGENT_MAX_TOOL_CALLS = 10    # max total tool executions
AGENT_TOKEN_BUDGET = 60_000  # abort the loop if cumulative tokens exceed this
AGENT_TOOLCALL_RETRIES = 3   # retries when Groq rejects a malformed tool call

# Shared generation settings
TEMPERATURE = 0.2            # low — we want consistent, factual briefs
REQUEST_TIMEOUT = 25         # seconds, per HTTP fetch
