"""
Thin wrapper around the Groq client that records cost/latency on every call.

Both the workflow and the agent talk to the LLM exclusively through this class,
so instrumentation is automatic and the two are measured identically — that's
what makes the decision-doc comparison fair.
"""
from __future__ import annotations

import os
from time import perf_counter

from groq import Groq

from . import config
from .metrics import CallRecord, RunMetrics


class LLMError(RuntimeError):
    pass


class ToolCallFormatError(LLMError):
    """Groq rejected a malformed tool call the model emitted (tool_use_failed).

    This is an *agent-only* failure mode: it only happens when we ask the model
    to emit structured tool calls. The deterministic workflow never can hit it.
    """


class LLM:
    def __init__(self, metrics: RunMetrics, api_key: str | None = None):
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key or key == "your_key_here":
            raise LLMError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and paste "
                "your free key from https://console.groq.com/keys"
            )
        self.client = Groq(api_key=key)
        self.metrics = metrics  # records accumulate here

    def chat(
        self,
        messages: list[dict],
        model: str = config.MODEL_SMART,
        tools: list | None = None,
        tool_choice: str | None = None,
        json_mode: bool = False,
        temperature: float = config.TEMPERATURE,
    ):
        """One chat completion. Records tokens + latency, returns the raw message."""
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        t0 = perf_counter()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:  # surface a clean message to the CLI/UI
            # Detect Groq's "tool_use_failed" (model emitted a malformed tool
            # call). The agent loop can retry these; everything else is fatal.
            if "tool_use_failed" in str(e) or "tool call validation failed" in str(e):
                raise ToolCallFormatError(str(e)) from e
            raise LLMError(f"Groq API call failed: {e}") from e
        latency = perf_counter() - t0

        usage = resp.usage
        self.metrics.calls.append(
            CallRecord(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                latency_s=latency,
            )
        )
        return resp.choices[0].message
