"""
THE AGENT — a minimal autonomous version of the SAME task, for honest contrast.

Instead of a fixed pipeline, we hand the model two tools (web_search, fetch_url)
and let *it* decide what to call, how often, and when to stop. This is the
"agentic" approach. It is more flexible — and, as the decision doc shows with
measured numbers, more expensive, slower, and harder to bound for a task whose
steps we already knew in advance.

The caps in config (steps, tool calls, token budget) are the guardrails that
keep an open-ended loop from running away. The agent uses the SMART model
throughout because it must reason about tool selection on every turn.
"""
from __future__ import annotations

import json
import os

from . import config, kinds
from .brief import Brief
from .llm import LLM, ToolCallFormatError
from .metrics import RunMetrics, Stopwatch
from .search import web_search, fetch_url


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for a query. Returns a list of "
                           "{title, url, snippet}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Download a URL and return its extracted main text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "the page URL"}
                },
                "required": ["url"],
            },
        },
    },
]

def _agent_model() -> str:
    """The model the agent reasons with.

    Defaults to the smart 70B model (the realistic config). Overridable via the
    AGENT_MODEL env var — used to keep the agent runnable on Groq's free tier
    when the 70B daily token cap is exhausted (the agent is a token hog).
    """
    return os.environ.get("AGENT_MODEL") or config.MODEL_SMART


def _chat_with_retry(llm: LLM, messages: list[dict], metrics: RunMetrics, model: str):
    """Call the model with tools, retrying Groq's malformed-tool-call failures.

    Llama models on Groq occasionally emit a tool call in the wrong format,
    which Groq rejects with 'tool_use_failed'. We retry a few times with a
    nudged-up temperature to break the bad sample, and count how often it
    happened — that count is real evidence of agent brittleness for the doc.
    """
    last_err = None
    for attempt in range(config.AGENT_TOOLCALL_RETRIES + 1):
        # Budget check INSIDE the retry loop: a malformed-call retry re-sends the
        # whole growing context on the premium model, so retries are exactly how
        # an agent silently burns its token budget. Stop before that happens.
        if metrics.total_tokens > config.AGENT_TOKEN_BUDGET:
            raise ToolCallFormatError("token budget reached during tool-call retries")
        try:
            return llm.chat(
                messages, model=model, tools=TOOLS,
                tool_choice="auto",
                temperature=config.TEMPERATURE + 0.2 * attempt,
            )
        except ToolCallFormatError as e:
            last_err = e
            metrics.toolcall_format_failures += 1
    # Exhausted retries — re-raise so the loop can fall back to a final answer.
    raise last_err


def _execute_tool(name: str, args: dict, metrics: RunMetrics) -> str:
    """Run a tool the agent asked for; bump the tool-call counter."""
    metrics.tool_calls += 1
    if name == "web_search":
        hits = web_search(args.get("query", ""))
        return json.dumps(hits[: config.SEARCH_RESULTS])
    if name == "fetch_url":
        src = fetch_url(args.get("url", ""))
        if src.ok:
            return json.dumps({"url": src.url, "title": src.title, "text": src.text})
        return json.dumps({"url": src.url, "error": src.error or "unreadable"})
    return json.dumps({"error": f"unknown tool {name}"})


def run_agent(
    company: str,
    urls: list[str] | None = None,
    csv_path: str | None = None,
    api_key: str | None = None,
    kind: str = "company",
) -> tuple[Brief, RunMetrics]:
    subject = company
    spec = kinds.get(kind)
    metrics = RunMetrics(mode="agent", target=subject)

    model = _agent_model()
    with Stopwatch(metrics):
        llm = LLM(metrics, api_key=api_key)

        user_kick = f"Research this {spec.subject_noun} and produce the brief: {subject}"
        if urls:
            user_kick += "\n\nStart with these user-supplied URLs:\n" + "\n".join(urls)

        messages: list[dict] = [
            {"role": "system", "content": kinds.agent_system(spec)},
            {"role": "user", "content": user_kick},
        ]

        final_content: str | None = None
        for step in range(config.AGENT_MAX_STEPS):
            # Hard budget guardrails — stop an autonomous loop from running away.
            if metrics.total_tokens > config.AGENT_TOKEN_BUDGET:
                metrics.notes = f"hit token budget at step {step}"
                break
            if metrics.tool_calls >= config.AGENT_MAX_TOOL_CALLS:
                metrics.notes = "hit tool-call cap; forcing final answer"
                # one last call with tools disabled to force a JSON answer
                msg = llm.chat(messages + [
                    {"role": "user", "content":
                        "Tool budget exhausted. Output the JSON brief now using "
                        "what you have."}],
                    model=model, json_mode=True)
                final_content = msg.content
                break

            try:
                msg = _chat_with_retry(llm, messages, metrics, model)
            except ToolCallFormatError:
                # Model kept emitting malformed tool calls. Force a final answer
                # from what we have — an agent-only recovery the workflow never needs.
                metrics.notes = (
                    f"tool-call format failed {metrics.toolcall_format_failures}× "
                    "after retries; forced final answer")
                fm = llm.chat(messages + [
                    {"role": "user", "content":
                        "Output the JSON brief now using whatever you have."}],
                    model=model, json_mode=True)
                final_content = fm.content
                break

            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                final_content = msg.content      # agent decided it is done
                break

            # Echo the assistant's tool-call turn, then append each tool result.
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = _execute_tool(tc.function.name, args, metrics)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            metrics.notes = metrics.notes or "hit step cap"

        brief = _parse_agent_output(subject, spec, final_content)

    if csv_path:
        from .metrics import append_csv
        append_csv(metrics, csv_path)
    return brief, metrics


def _parse_agent_output(subject: str, spec: kinds.Kind, content: str | None) -> Brief:
    if not content:
        return Brief(subject=subject, kind_id=spec.id,
                     caveats="Agent stopped without producing a brief (hit a cap).")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Agent returned prose instead of JSON — salvage it into the first section.
        first_key = spec.sections[0].key if spec.sections else "summary"
        return Brief(subject=subject, kind_id=spec.id,
                     sections={first_key: content.strip()},
                     caveats="Agent returned unstructured text; parsed as the first section.")
    return Brief.from_json(subject, data, kind_id=spec.id)
