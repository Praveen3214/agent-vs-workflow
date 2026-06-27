"""
Subject KINDS — one engine, several brief templates.

The pipeline (gather → summarise → synthesise → cite) is identical for every
kind; only the *sections* and the *prompts* differ. Adding a new kind here is all
it takes to support a new subject type in both the workflow and the agent.

Political kinds (leader/party) and any topic are marked `sensitive=True`, which
injects strict neutrality + attribution rules and a visible disclaimer. This is a
deliberate guardrail: summarising real people/contested topics carries a
defamation and bias risk, so the tool reports "as stated by sources", never
asserts unsourced claims, and surfaces disagreement instead of taking a side.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Section:
    key: str            # JSON key the model fills
    heading: str        # markdown heading shown in the brief
    is_list: bool       # render as bullet list (True) or paragraph (False)
    guidance: str       # instruction to the model for this section


@dataclass
class Kind:
    id: str
    label: str          # human label (UI / CLI)
    title_prefix: str   # markdown H1 prefix, e.g. "Competitive Brief —"
    subject_noun: str   # e.g. "company", "political leader", "topic"
    input_label: str    # what the UI asks the user to type
    placeholder: str    # example input
    search_suffix: str  # appended to the subject to form the search query
    sections: list[Section] = field(default_factory=list)  # body sections only
    sensitive: bool = False


DISCLAIMER = (
    "_AI-generated summary compiled from public web sources. It may be incomplete "
    "or contain errors — verify against the cited sources before relying on it. "
    "Written to be neutral; nothing here is an endorsement or a factual ruling._"
)


KINDS: dict[str, Kind] = {
    "company": Kind(
        id="company", label="Company", title_prefix="Competitive Brief —",
        subject_noun="company", input_label="Company or topic", placeholder="e.g. Notion",
        search_suffix="company overview products news",
        sections=[
            Section("overview", "Overview", False,
                    "A 1-2 sentence factual overview of the company."),
            Section("products", "Products & Services", True,
                    "Main products or services offered."),
            Section("positioning", "Market Positioning", False,
                    "How the company positions itself in its market."),
            Section("recent_news", "Recent News", True,
                    "Dated recent developments, each traceable to the notes."),
        ],
    ),
    "leader": Kind(
        id="leader", label="Political leader", title_prefix="Profile —",
        subject_noun="political leader", input_label="Political leader's name",
        placeholder="e.g. a sitting MP, senator, or party leader",
        search_suffix="politician profile policy positions recent news",
        sensitive=True,
        sections=[
            Section("background", "Background & Role", False,
                    "Factual background only as stated in sources: current role/office, "
                    "party affiliation, notable career facts."),
            Section("positions", "Policy Positions", True,
                    "Stated policy positions/stances, each attributed to a source. "
                    "Use neutral wording; do not characterise them as good or bad."),
            Section("recent_activity", "Recent Activity", True,
                    "Recent dated activities, statements, or events, as reported."),
            Section("perspectives", "Different Perspectives", False,
                    "How supporters and critics view this person, per the sources, "
                    "presented even-handedly without the author taking a side."),
        ],
    ),
    "party": Kind(
        id="party", label="Political party", title_prefix="Party Profile —",
        subject_noun="political party", input_label="Political party's name",
        placeholder="e.g. a national or regional party",
        search_suffix="political party platform ideology leaders recent news",
        sensitive=True,
        sections=[
            Section("overview", "Overview", False,
                    "Factual overview: what the party is, where it operates, founding if noted."),
            Section("platform", "Platform & Stated Ideology", True,
                    "Stated platform and policy positions, attributed to sources, neutrally worded."),
            Section("key_figures", "Key Figures", True,
                    "Notable current leaders/figures, as named in sources."),
            Section("recent_news", "Recent News", True,
                    "Dated recent developments, each traceable to the notes."),
            Section("perspectives", "Different Perspectives", False,
                    "How the party is viewed across the spectrum, per sources, without taking a side."),
        ],
    ),
    "topic": Kind(
        id="topic", label="Topic / current event", title_prefix="Topic Summary —",
        subject_noun="topic", input_label="Topic or question",
        placeholder="e.g. any current event, concept, or question",
        search_suffix="explained overview latest news",
        sensitive=True,
        sections=[
            Section("summary", "What It Is", False,
                    "A clear, meaningful plain-English summary of the topic."),
            Section("key_facts", "Key Facts", True,
                    "Key facts/figures drawn from the sources, each traceable to the notes."),
            Section("perspectives", "Different Perspectives", True,
                    "Distinct viewpoints or sides on the topic, per sources, presented neutrally."),
            Section("recent", "Recent Developments", True,
                    "Recent dated developments, as reported."),
        ],
    ),
}


def get(kind_id: str | None) -> Kind:
    return KINDS.get(kind_id or "company", KINDS["company"])


def _keys_clause(kind: Kind) -> str:
    parts = [f"{s.key} ({'array of strings' if s.is_list else 'string'})" for s in kind.sections]
    parts += ["caveats (string)", "sources (array of the source URLs you used)"]
    return ", ".join(parts)


def _neutrality_block(kind: Kind) -> str:
    if not kind.sensitive:
        return ""
    return (
        "\nThis subject is SENSITIVE (a real person, party, or contested topic). "
        "Be strictly impartial. Attribute every claim to the sources ('according to "
        "...'). Never state a contested or unverified claim as fact. Do not praise, "
        "condemn, endorse, or speculate. If sources are partisan, note that in 'caveats'."
    )


def summarise_system(kind: Kind) -> str:
    return (
        f"You extract facts for a {kind.subject_noun} brief. Summarise ONLY what the "
        f"text actually says about the target in 3-5 bullet points. If the text is "
        f"irrelevant to the target, reply exactly: NOT_RELEVANT. Never invent facts."
        + _neutrality_block(kind)
    )


def synth_system(kind: Kind) -> str:
    lines = [
        f"You are a research analyst. Using ONLY the provided source notes, produce a "
        f"{kind.subject_noun} brief as STRICT JSON with keys: {_keys_clause(kind)}.",
        "Each key should contain:",
    ]
    lines += [f"- {s.key}: {s.guidance}" for s in kind.sections]
    lines += [
        "Guardrails:",
        "- Do NOT use outside knowledge; if the notes don't support a claim, omit it.",
        "- If sources disagree, state the disagreement in 'caveats'.",
        "- If coverage is thin, say so in 'caveats' rather than padding.",
    ]
    return "\n".join(lines) + _neutrality_block(kind)


def agent_system(kind: Kind) -> str:
    return (
        f"You are an autonomous research agent. Your job: produce a {kind.subject_noun} "
        f"brief for the target. Use web_search to find sources and fetch_url to read "
        f"them. Read at least two sources before concluding. Do NOT use outside "
        f"knowledge; rely only on fetched content and cite the URLs you used.\n\n"
        f"When you have enough information, STOP calling tools and reply with STRICT "
        f"JSON only (no prose) with keys: {_keys_clause(kind)}. "
        f"If information is missing or sources conflict, say so in 'caveats'."
        + _neutrality_block(kind)
    )


def search_query(kind: Kind, subject: str) -> str:
    return f"{subject} {kind.search_suffix}"
