"""
Command-line interface.

    python cli.py run --mode workflow --company "Notion" --out examples/notion.md
    python cli.py run --mode agent --company "Notion"
    python cli.py benchmark --company "Notion"     # runs BOTH, prints comparison

`benchmark` is what feeds DECISION_DOC.md: it runs the workflow and the agent on
the same input and writes a paste-ready markdown table to benchmarks/latest.md,
plus appends raw rows to benchmarks/runs.csv.
"""
from __future__ import annotations

import argparse
import sys

# Briefs contain emoji (⚠️) and symbols (÷, ×). Windows terminals default to
# cp1252 and crash on those, so force UTF-8 output where supported.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

from briefgen.workflow import run_workflow
from briefgen.agent import run_agent
from briefgen.llm import LLMError
from briefgen.metrics import RunMetrics

load_dotenv()

CSV_PATH = "benchmarks/runs.csv"
LATEST_MD = "benchmarks/latest.md"


def _print_metrics(m: RunMetrics) -> None:
    print(f"\n  mode={m.mode}  llm_calls={m.llm_calls}  tool_calls={m.tool_calls}")
    print(f"  tokens={m.total_tokens:,} ({m.input_tokens:,} in / {m.output_tokens:,} out)")
    print(f"  cost=${m.cost_usd:.5f}   wall={m.wall_time_s:.1f}s")
    if m.notes:
        print(f"  notes: {m.notes}")


def cmd_run(args) -> int:
    runner = run_workflow if args.mode == "workflow" else run_agent
    brief, metrics = runner(args.company, urls=args.url, csv_path=CSV_PATH, kind=args.kind)
    md = brief.to_markdown(metrics)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Brief written to {args.out}")
    else:
        print("\n" + md)
    _print_metrics(metrics)
    return 0


def _comparison_table(w: RunMetrics, a: RunMetrics) -> str:
    def factor(av, wv):
        if wv == 0:
            return "n/a"
        return f"{av / wv:.1f}×"
    rows = [
        ("LLM calls", w.llm_calls, a.llm_calls),
        ("Tool calls", w.tool_calls, a.tool_calls),
        ("Total tokens", w.total_tokens, a.total_tokens),
        ("Cost (USD)", round(w.cost_usd, 5), round(a.cost_usd, 5)),
        ("Wall time (s)", round(w.wall_time_s, 1), round(a.wall_time_s, 1)),
    ]
    lines = [
        f"### Measured: workflow vs agent — `{w.target}`",
        "",
        "| Metric | Workflow | Agent | Agent ÷ Workflow |",
        "|---|---|---|---|",
    ]
    for name, wv, av in rows:
        lines.append(f"| {name} | {wv} | {av} | {factor(av, wv)} |")
    notes = []
    if w.notes:
        notes.append(f"workflow: {w.notes}")
    if a.notes:
        notes.append(f"agent: {a.notes}")
    if notes:
        lines += ["", "_Notes: " + "; ".join(notes) + "_"]
    lines.append("")
    return "\n".join(lines)


def cmd_benchmark(args) -> int:
    print(f"Running WORKFLOW on '{args.company}' ...")
    _, wm = run_workflow(args.company, urls=args.url, csv_path=CSV_PATH, kind=args.kind)
    _print_metrics(wm)

    print(f"\nRunning AGENT on '{args.company}' ...")
    _, am = run_agent(args.company, urls=args.url, csv_path=CSV_PATH, kind=args.kind)
    _print_metrics(am)

    table = _comparison_table(wm, am)
    with open(LATEST_MD, "w", encoding="utf-8") as f:
        f.write(table)
    print("\n" + "=" * 60)
    print(table)
    print(f"(Paste-ready table also saved to {LATEST_MD})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Competitive-Research Brief Generator")
    sub = p.add_subparsers(dest="cmd", required=True)

    kind_choices = ["company", "leader", "party", "topic"]

    pr = sub.add_parser("run", help="Generate one brief")
    pr.add_argument("--mode", choices=["workflow", "agent"], default="workflow")
    pr.add_argument("--company", required=True, help="subject: company/leader/party/topic name")
    pr.add_argument("--kind", choices=kind_choices, default="company",
                    help="subject type (default: company)")
    pr.add_argument("--url", action="append", help="source URL (repeatable)")
    pr.add_argument("--out", help="write markdown to this file")
    pr.set_defaults(func=cmd_run)

    pb = sub.add_parser("benchmark", help="Run workflow AND agent; compare")
    pb.add_argument("--company", required=True)
    pb.add_argument("--kind", choices=kind_choices, default="company",
                    help="subject type (default: company)")
    pb.add_argument("--url", action="append", help="source URL (repeatable)")
    pb.set_defaults(func=cmd_benchmark)

    args = p.parse_args()
    try:
        return args.func(args)
    except LLMError as e:
        print(f"\n[error] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
