"""Tavily web search wrapper.

Tool-allowlisting principle: only the Researcher agent imports this module. No other agent
has any web-fetching capability. The wrapper:
  - enforces a hard cap on calls per run (defense-in-depth against runaway agents),
  - sanitizes returned content (HTML/script removal),
  - flags content with prompt-injection markers before any other agent sees it.
"""

from __future__ import annotations

from typing import Any

import bleach
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from atlas.config import get_settings
from atlas.graph.state import Source
from atlas.guardrails.content import scan_web_content
from atlas.logging import get_logger

log = get_logger("atlas.tools.search")


class SearchBudgetExceeded(RuntimeError):
    """Raised when total search calls exceed ATLAS_MAX_SEARCH_CALLS for this run."""


def _client() -> TavilyClient:
    return TavilyClient(api_key=get_settings().TAVILY_API_KEY)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
def _raw_search(query: str, max_results: int = 5) -> dict[str, Any]:
    return _client().search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )


def search(query: str, *, max_results: int = 5, budget_remaining: int) -> tuple[list[Source], int]:
    """Search the web. Returns (sources, calls_used).

    `budget_remaining` is the number of search calls left for this run — caller must
    decrement and pass forward.
    """
    if budget_remaining <= 0:
        raise SearchBudgetExceeded(
            f"Search budget exhausted (max {get_settings().ATLAS_MAX_SEARCH_CALLS} per run)."
        )

    log.info("search.start", query=query[:200], budget_remaining=budget_remaining)
    raw = _raw_search(query=query, max_results=max_results)

    sources: list[Source] = []
    for r in raw.get("results", []):
        content_raw: str = r.get("content", "") or ""
        # Strip any HTML/scripts — Tavily generally returns clean text but defense-in-depth.
        content_clean = bleach.clean(content_raw, tags=[], strip=True)
        # Scan for prompt-injection patterns BEFORE downstream agents see it.
        flagged, reason = scan_web_content(content_clean)

        sources.append(
            Source(
                url=r.get("url", ""),
                title=r.get("title", "") or "",
                snippet=(r.get("snippet") or content_clean[:240]),
                content=content_clean[:4000],  # cap per-source content
                flagged=flagged,
                flag_reason=reason,
            )
        )

    log.info("search.done", n_results=len(sources), n_flagged=sum(1 for s in sources if s["flagged"]))
    return sources, 1
