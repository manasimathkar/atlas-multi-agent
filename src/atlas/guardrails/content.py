"""Checkpoint 2: Web-content guardrail.

This is the *highest-risk* surface for a research agent: malicious actors plant
prompt-injection payloads in web pages aiming to subvert the downstream Writer/Critic.

Strategy:
  - Regex scan for injection markers in fetched content (fail-closed: flag, don't crash).
  - Flagged content is still shown to the user (for transparency) but tagged in state;
    the Writer is instructed to ignore any instructions embedded in source material and
    only treat it as data.
  - High-confidence hits cause the source to be dropped from the synthesis bundle.
"""

from __future__ import annotations

from atlas.guardrails.patterns import find_injection_hits


def scan_web_content(text: str) -> tuple[bool, str]:
    """Return (flagged, reason). Fast regex-only — runs on every fetched page."""
    hits = find_injection_hits(text)
    if hits:
        return True, f"Injection markers: {', '.join(hits)}"
    return False, ""
