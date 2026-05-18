"""Checkpoint 3: Output guardrail.

Run on the final brief before returning to the user. Catches:
  - PII (emails, SSNs, credit cards, phones, API-key-like strings)
  - Policy violations (Haiku judge: e.g. instructions for harm, fabricated quotes from real people)
"""

from __future__ import annotations

from atlas.config import get_settings
from atlas.guardrails.patterns import find_pii_hits, redact_pii
from atlas.llm import call_json
from atlas.logging import get_logger

log = get_logger("atlas.guardrails.output")


_POLICY_SYSTEM = """You are a content policy classifier reviewing a research brief drafted
by an AI system. Flag the document ONLY if it contains:
  - step-by-step instructions for serious physical harm (weapons of mass destruction, synthesis of dangerous substances)
  - fabricated direct quotes attributed to named real people
  - explicit personal data about private individuals (not public figures)

Ordinary discussion of sensitive topics is fine. Be specific in your reason."""

_SCHEMA = """{"verdict": "safe" | "violation", "reason": "<short>"}"""


def check_output(brief: str) -> dict:
    """Return {'verdict','reason','pii_hits','redacted_brief'}."""
    pii_hits = find_pii_hits(brief)
    redacted = redact_pii(brief) if pii_hits else brief

    result = call_json(
        system=_POLICY_SYSTEM,
        user=f"Classify this brief:\n\n{redacted[:8000]}",
        schema_hint=_SCHEMA,
        model=get_settings().ATLAS_MODEL_FAST,
        agent="guardrail.output",
        max_tokens=200,
    )
    verdict = result.get("verdict", "safe")
    return {
        "verdict": verdict,
        "reason": result.get("reason", ""),
        "pii_hits": pii_hits,
        "redacted_brief": redacted,
    }
