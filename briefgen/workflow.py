"""
THE WORKFLOW — a fixed, deterministic pipeline.

    gather  →  summarise each source (cheap 8B)  →  synthesise brief (smart 70B)  →  format

The control flow is plain Python. The LLM only ever *fills in text* inside steps
we defined; it never decides what to do next. That is the whole point of the
decision doc: known steps → predictable cost, easy debugging, cheap model-tiering.
"""
from __future__ import annotations

import json

from . import config, kinds
from .brief import Brief
from .llm import LLM
from .metrics import RunMetrics, Stopwatch
from .search import gather_sources, Source


def _summarise_source(llm: LLM, kind: kinds.Kind, subject: str, src: Source) -> str | None:
    """Cheap model condenses one page. Returns None if not relevant."""
    msg = llm.chat(
        model=config.MODEL_CHEAP,
        messages=[
            {"role": "system", "content": kinds.summarise_system(kind)},
            {"role": "user", "content":
                f"Target {kind.subject_noun}: {subject}\nSource URL: {src.url}\n\n"
                f"--- PAGE TEXT ---\n{src.text}"},
        ],
    )
    out = (msg.content or "").strip()
    if not out or out.upper().startswith("NOT_RELEVANT"):
        return None
    return out


def run_workflow(
    company: str,
    urls: list[str] | None = None,
    csv_path: str | None = None,
    api_key: str | None = None,
    kind: str = "company",
) -> tuple[Brief, RunMetrics]:
    subject = company
    spec = kinds.get(kind)
    metrics = RunMetrics(mode="workflow", target=subject)

    with Stopwatch(metrics):
        llm = LLM(metrics, api_key=api_key)

        # STEP 1 — gather (deterministic; search + user URLs)
        query = kinds.search_query(spec, subject)
        sources = gather_sources(query=query, urls=urls)

        # Guardrail: no readable sources → return an honest empty brief.
        if not sources:
            metrics.notes = "no readable sources"
            brief = Brief(
                subject=subject, kind_id=spec.id,
                caveats="No sources could be retrieved (search failed or URLs "
                        "unreadable). No brief was generated to avoid fabrication.",
            )
            _finalise(metrics, csv_path)
            return brief, metrics

        # STEP 2 — summarise each source with the CHEAP model
        notes: list[str] = []
        for src in sources:
            summary = _summarise_source(llm, spec, subject, src)
            if summary:
                notes.append(f"SOURCE: {src.url}\n{summary}")
        metrics.tool_calls = len(sources)  # the deterministic fetches we ran

        if not notes:
            metrics.notes = "sources retrieved but none relevant"
            brief = Brief(
                subject=subject, kind_id=spec.id,
                sources=[s.url for s in sources],
                caveats="Sources were retrieved but none contained relevant, "
                        "usable information about the target.",
            )
            _finalise(metrics, csv_path)
            return brief, metrics

        # STEP 3 — synthesise structured brief with the SMART model (JSON mode)
        joined = "\n\n".join(notes)
        msg = llm.chat(
            model=config.MODEL_SMART,
            json_mode=True,
            messages=[
                {"role": "system", "content": kinds.synth_system(spec)},
                {"role": "user", "content":
                    f"Target: {subject}\n\nSOURCE NOTES:\n{joined}\n\n"
                    "Return the JSON brief now."},
            ],
        )
        brief = _parse_brief(subject, spec.id, msg.content,
                             fallback_sources=[s.url for s in sources])

    # STEP 4 — format happens in Brief.to_markdown (caller's job)
    _finalise(metrics, csv_path)
    return brief, metrics


def _parse_brief(subject: str, kind_id: str, content: str | None,
                 fallback_sources: list[str]) -> Brief:
    try:
        data = json.loads(content or "{}")
    except json.JSONDecodeError:
        data = {}
    brief = Brief.from_json(subject, data, kind_id=kind_id)
    if not brief.sources:                      # ensure citations are never empty
        brief.sources = fallback_sources
    return brief


def _finalise(metrics: RunMetrics, csv_path: str | None) -> None:
    if csv_path:
        from .metrics import append_csv
        append_csv(metrics, csv_path)
