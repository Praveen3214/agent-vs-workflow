"""
Run instrumentation: tokens, cost, and latency per LLM call.

Every claim in DECISION_DOC.md about cost/latency comes from here. We record
each individual model call, then aggregate. Cost is derived from config.PRICING
so the numbers are reproducible, not guessed.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field, asdict
from time import perf_counter

from . import config


@dataclass
class CallRecord:
    """One LLM API call."""
    model: str
    input_tokens: int
    output_tokens: int
    latency_s: float

    @property
    def cost_usd(self) -> float:
        price = config.PRICING.get(self.model)
        if not price:
            return 0.0
        return (
            self.input_tokens / 1_000_000 * price["input"]
            + self.output_tokens / 1_000_000 * price["output"]
        )


@dataclass
class RunMetrics:
    """Aggregate of all calls in a single workflow/agent run."""
    mode: str                       # "workflow" or "agent"
    target: str                     # company / topic researched
    calls: list[CallRecord] = field(default_factory=list)
    tool_calls: int = 0             # web_search / fetch_url executions
    toolcall_format_failures: int = 0  # agent-only: Groq rejected a malformed call
    wall_time_s: float = 0.0        # end-to-end, incl. network I/O
    notes: str = ""                 # e.g. "hit step cap", "search failed"

    # --- derived totals ---
    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def llm_calls(self) -> int:
        return len(self.calls)

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def summary_row(self) -> dict:
        return {
            "mode": self.mode,
            "target": self.target,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "toolcall_format_failures": self.toolcall_format_failures,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "wall_time_s": round(self.wall_time_s, 2),
            "notes": self.notes,
        }


class Stopwatch:
    """Context manager that records wall time into a RunMetrics object."""
    def __init__(self, metrics: RunMetrics):
        self.metrics = metrics

    def __enter__(self):
        self._t0 = perf_counter()
        return self

    def __exit__(self, *exc):
        self.metrics.wall_time_s = perf_counter() - self._t0
        return False


def append_csv(metrics: RunMetrics, path: str) -> None:
    """Append a run's summary to a CSV log (creates header if new)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    row = metrics.summary_row()
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
