"""
The structured output: a one-page research brief.

A brief is section-driven — its shape is defined by the chosen `Kind`
(see kinds.py), so the same dataclass serves companies, political leaders,
political parties, and general topics. Both the workflow and the agent must
produce this same shape, so the comparison is about *how* they get there, not
what they output.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import kinds
from .metrics import RunMetrics


@dataclass
class Brief:
    subject: str
    kind_id: str = "company"
    sections: dict = field(default_factory=dict)   # key -> str | list[str]
    caveats: str = ""                              # missing/contradictory-info notes
    sources: list[str] = field(default_factory=list)

    # Backwards-compatible alias (older call sites / tests used .company).
    @property
    def company(self) -> str:
        return self.subject

    @classmethod
    def from_json(cls, subject: str, data: dict, kind_id: str = "company") -> "Brief":
        """Build from the LLM's JSON, tolerating missing keys, per the kind's schema."""
        kind = kinds.get(kind_id)

        def as_list(v):
            if isinstance(v, list):
                return [str(x) for x in v if str(x).strip()]
            if isinstance(v, str) and v.strip():
                return [v.strip()]
            return []

        sections: dict = {}
        for s in kind.sections:
            raw = data.get(s.key)
            sections[s.key] = as_list(raw) if s.is_list else str(raw or "").strip()

        return cls(
            subject=subject,
            kind_id=kind.id,
            sections=sections,
            caveats=str(data.get("caveats", "")).strip(),
            sources=as_list(data.get("sources")),
        )

    def to_markdown(self, metrics: RunMetrics | None = None) -> str:
        kind = kinds.get(self.kind_id)
        lines: list[str] = [f"# {kind.title_prefix} {self.subject}", ""]

        if kind.sensitive:
            lines += [f"> {kinds.DISCLAIMER}", ""]

        for s in kind.sections:
            lines.append(f"## {s.heading}")
            val = self.sections.get(s.key)
            if s.is_list:
                if val:
                    lines += [f"- {item}" for item in val]
                else:
                    lines.append("_None found in sources._")
            else:
                lines.append(val or "_Not determined from sources._")
            lines.append("")

        if self.caveats:
            lines += ["## ⚠️ Caveats & Gaps", self.caveats, ""]

        lines.append("## Sources")
        if self.sources:
            lines += [f"{i}. {s}" for i, s in enumerate(self.sources, 1)]
        else:
            lines.append("_No sources cited — treat this brief as unverified._")
        lines.append("")

        if metrics:
            lines += [
                "---",
                "### Run metrics",
                f"- **Mode:** {metrics.mode}",
                f"- **LLM calls:** {metrics.llm_calls}  |  "
                f"**Tool calls:** {metrics.tool_calls}",
                f"- **Tokens:** {metrics.total_tokens:,} "
                f"({metrics.input_tokens:,} in / {metrics.output_tokens:,} out)",
                f"- **Notional cost:** ${metrics.cost_usd:.5f}",
                f"- **Wall time:** {metrics.wall_time_s:.1f}s",
            ]
            if metrics.notes:
                lines.append(f"- **Notes:** {metrics.notes}")
            lines.append("")

        return "\n".join(lines)
