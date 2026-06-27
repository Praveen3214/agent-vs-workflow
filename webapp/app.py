"""
FastAPI backend for the brief generator.

Deliberately thin: it is just an HTTP layer over the SAME engine the CLI uses
(briefgen.run_workflow / run_agent). The separation of "engine" from "interface"
is a senior signal in itself — the decision doc's measured core is reused
verbatim, no logic duplicated.

Public-demo key strategy (see DEPLOY.md):
  - Each visitor gets a few FREE briefs on the app owner's shared Groq key.
  - After that (or if the shared free budget is used up), the visitor is asked
    to paste their own free Groq key, which is used per-request and never stored.
  - The shared key is a free-tier key Groq itself caps at 100K tokens/day, so the
    owner can never be over-charged — the worst case is "bring your own key".

Run locally:  uvicorn webapp.app:app --reload   →   http://127.0.0.1:8000
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from briefgen.workflow import run_workflow
from briefgen.agent import run_agent
from briefgen.llm import LLMError

load_dotenv()

app = FastAPI(title="Competitive-Research Brief Generator")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# --- public-demo quota knobs (override via env on the Space) ------------------
FREE_PER_VISITOR = int(os.environ.get("FREE_PER_VISITOR", "4"))   # free briefs / IP / day
GLOBAL_DAILY_CAP = int(os.environ.get("GLOBAL_DAILY_CAP", "30"))  # backstop on shared key

# In-memory counters. Ephemeral by design (reset on restart) — fine for a demo;
# DEPLOY.md notes how to make them durable if you ever need to.
_visitor_usage: dict[str, int] = {}
_global_usage = {"count": 0}
_usage_day = {"day": ""}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _roll_day() -> None:
    """Reset all counters at the start of a new UTC day."""
    if _usage_day["day"] != _today():
        _usage_day["day"] = _today()
        _visitor_usage.clear()
        _global_usage["count"] = 0


def _client_ip(request: Request) -> str:
    # Behind the HF Spaces proxy the real client is in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _owner_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY", "")
    return key if key and key != "your_key_here" else None


class BriefRequest(BaseModel):
    company: str
    mode: str = "workflow"           # "workflow" | "agent"
    kind: str = "company"            # "company" | "leader" | "party" | "topic"
    urls: list[str] = []
    api_key: str | None = None       # optional user-supplied Groq key (BYOK)


@app.post("/api/brief")
def make_brief(req: BriefRequest, request: Request):
    _roll_day()
    company = (req.company or "").strip()
    if not company:
        return {"ok": False, "error": "Please enter a company or topic."}

    ip = _client_ip(request)
    user_key = (req.api_key or "").strip()

    # --- decide which key powers this run -------------------------------------
    if user_key:
        if not user_key.startswith("gsk_"):
            return {"ok": False, "error": "That doesn't look like a Groq key (it should start with 'gsk_')."}
        key_in_use = user_key
        on_shared_key = False
    else:
        # Using the owner's shared free key — enforce the demo quotas.
        if _owner_key() is None:
            return {"ok": False, "needs_key": True,
                    "error": "This demo needs a Groq key. Paste your own free key to run it.",
                    "free_remaining": 0}
        used = _visitor_usage.get(ip, 0)
        if used >= FREE_PER_VISITOR:
            return {"ok": False, "needs_key": True,
                    "error": f"You've used your {FREE_PER_VISITOR} free briefs. "
                             "Add your own free Groq key to keep going — it's instant and free.",
                    "free_remaining": 0}
        if _global_usage["count"] >= GLOBAL_DAILY_CAP:
            return {"ok": False, "needs_key": True,
                    "error": "The shared demo budget for today is used up. "
                             "Add your own free Groq key to continue.",
                    "free_remaining": 0}
        key_in_use = _owner_key()
        on_shared_key = True

    # --- run the engine -------------------------------------------------------
    runner = run_workflow if req.mode == "workflow" else run_agent
    urls = [u for u in req.urls if u and u.strip()]
    try:
        # No CSV logging on the public endpoint (privacy + read-only containers).
        brief, metrics = runner(company, urls=urls or None,
                                csv_path=None, api_key=key_in_use, kind=req.kind)
    except LLMError as e:
        msg = str(e)
        # If the SHARED key just hit Groq's daily ceiling, fall back to BYOK.
        if on_shared_key and ("429" in msg or "rate_limit" in msg or "tokens per day" in msg.lower()):
            return {"ok": False, "needs_key": True,
                    "error": "The shared demo budget for today is used up. "
                             "Add your own free Groq key to continue.",
                    "free_remaining": 0}
        return {"ok": False, "error": msg}

    # Count a successful run against the demo quotas (never the user's own key).
    free_remaining = None
    if on_shared_key:
        _visitor_usage[ip] = _visitor_usage.get(ip, 0) + 1
        _global_usage["count"] += 1
        free_remaining = max(0, FREE_PER_VISITOR - _visitor_usage[ip])

    return {
        "ok": True,
        "markdown": brief.to_markdown(),
        "used_own_key": not on_shared_key,
        "free_remaining": free_remaining,
        "metrics": {
            "mode": metrics.mode,
            "llm_calls": metrics.llm_calls,
            "tool_calls": metrics.tool_calls,
            "total_tokens": metrics.total_tokens,
            "input_tokens": metrics.input_tokens,
            "output_tokens": metrics.output_tokens,
            "cost_usd": round(metrics.cost_usd, 5),
            "wall_time_s": round(metrics.wall_time_s, 1),
            "notes": metrics.notes,
        },
    }


@app.get("/api/quota")
def quota(request: Request):
    """Lets the page show 'N free briefs left' on load."""
    _roll_day()
    ip = _client_ip(request)
    remaining = max(0, FREE_PER_VISITOR - _visitor_usage.get(ip, 0))
    if _global_usage["count"] >= GLOBAL_DAILY_CAP or _owner_key() is None:
        remaining = 0
    return {"free_remaining": remaining, "free_limit": FREE_PER_VISITOR}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
