"""
Free information gathering: DuckDuckGo web search + robust page-text extraction.

No paid APIs and no keys. DuckDuckGo can rate-limit or fail, so every function
degrades gracefully and the caller (workflow or agent) can fall back to
user-supplied URLs. This is one of the named guardrails in the decision doc.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests
import trafilatura

from . import config


@dataclass
class Source:
    url: str
    title: str = ""
    text: str = ""
    ok: bool = False
    error: str = ""


def web_search(query: str, max_results: int = config.SEARCH_RESULTS) -> list[dict]:
    """Return [{title, url, snippet}]. Empty list on failure (never raises)."""
    try:
        from ddgs import DDGS  # imported lazily so a missing/renamed dep is obvious
        with DDGS() as ddgs:
            hits = ddgs.text(query, max_results=max_results)
        return [
            {
                "title": h.get("title", ""),
                "url": h.get("href") or h.get("url", ""),
                "snippet": h.get("body", ""),
            }
            for h in hits
            if h.get("href") or h.get("url")
        ]
    except Exception:
        return []  # caller decides how to fall back


def fetch_url(url: str) -> Source:
    """Download a page and extract its main text. Bounded + failure-safe."""
    src = Source(url=url)
    try:
        resp = requests.get(
            url,
            timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (research-brief-bot)"},
        )
        resp.raise_for_status()
        extracted = trafilatura.extract(
            resp.text, include_comments=False, include_tables=False
        )
        if not extracted:
            src.error = "no extractable text"
            return src
        # Title via trafilatura metadata (best-effort)
        meta = trafilatura.extract_metadata(resp.text)
        src.title = (meta.title if meta and meta.title else url)[:200]
        src.text = extracted[: config.MAX_CHARS_PER_SOURCE]
        src.ok = True
    except Exception as e:
        src.error = str(e)[:200]
    return src


def gather_sources(
    query: str | None = None,
    urls: list[str] | None = None,
    max_sources: int = config.MAX_SOURCES,
) -> list[Source]:
    """
    Deterministic gather step used by the WORKFLOW.

    Priority: user-supplied URLs first (most trustworthy / reproducible), then
    top web-search results to fill up to max_sources. Only successfully-read
    pages are returned.
    """
    candidate_urls: list[str] = []
    if urls:
        candidate_urls.extend(u.strip() for u in urls if u.strip())

    if query and len(candidate_urls) < max_sources:
        for hit in web_search(query, max_results=config.SEARCH_RESULTS):
            if hit["url"] not in candidate_urls:
                candidate_urls.append(hit["url"])

    sources: list[Source] = []
    for url in candidate_urls:
        if len(sources) >= max_sources:
            break
        src = fetch_url(url)
        if src.ok:
            sources.append(src)
    return sources
