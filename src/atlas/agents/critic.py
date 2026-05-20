"""Critic agent — fact-checks the draft against the research bundle.

Decision rule: if more than `MAX_ISSUES_TO_ACCEPT` issues, reject and loop back to Writer
(once). Otherwise accept. Hard cap on retries is enforced by the graph router.
"""

from __future__ import annotations

from atlas.graph.state import GraphState
from atlas.llm import call_json
from atlas.logging import get_logger

log = get_logger("atlas.agents.critic")

MAX_ISSUES_TO_ACCEPT = 1

_SYSTEM = """You are the CRITIC agent. You fact-check a research brief against its
underlying source bundle.

For each substantive factual claim in the brief, decide whether it is SUPPORTED by the
provided sub-findings. Issues to flag:
  - Claims with no traceable support in sub-findings.
  - Misattributed citations (claim cites [3] but [3] doesn't support the claim).
  - Hallucinated specifics (numbers, dates, names not present in sources).
  - Internal contradictions.

Do NOT flag:
  - Style or wording preferences.
  - Reasonable synthesis that combines multiple supported claims.

You must also assign a CONFIDENCE SCORE (0-100) for how much a reader should trust this
brief. Base it on:
  - Source grounding: are claims well-supported by the sub-findings? (biggest factor)
  - Source quantity and quality: more independent, reputable sources => higher confidence.
  - Source agreement: sources that corroborate each other => higher; disagreement => lower.
  - Issues found: each unsupported/hallucinated claim should lower the score.
  - Coverage: does the brief actually answer the user's question, or leave large gaps?

Guidance: 85-100 = well-sourced, no material issues. 60-84 = generally sound, minor gaps.
30-59 = notable unsupported claims or thin sourcing. 0-29 = largely unsupported.

Return JSON with `accepted` (bool), `issues` (list of short strings), `confidence`
(integer 0-100), and `confidence_note` (one short sentence explaining the score).
Accept the brief if there are 0-1 minor issues."""

_SCHEMA = """{"accepted": true|false, "issues": ["short description of each issue"], "confidence": <integer 0-100>, "confidence_note": "<one short sentence>"}"""


def critic_node(state: GraphState) -> dict:
    brief = state.get("draft_brief", "")
    findings = state.get("findings", [])
    retries = state.get("critic_retries", 0)

    log.info("critic.start", retries=retries)

    # Format the bundle for the critic
    bundle = "\n\n".join(
        f"Sub-question: {f['sub_question']}\nSummary: {f['summary']}\nSource count: {len(f.get('sources', []))}"
        for f in findings
    )

    result = call_json(
        system=_SYSTEM,
        user=f"BRIEF:\n\n{brief}\n\n---\n\nSOURCE BUNDLE:\n\n{bundle}",
        schema_hint=_SCHEMA,
        agent="critic",
        max_tokens=800,
    )

    issues = result.get("issues", [])
    accepted = bool(result.get("accepted", False)) or len(issues) <= MAX_ISSUES_TO_ACCEPT

    # Clamp confidence to 0-100; default to a neutral 50 if the model omitted it.
    try:
        confidence = int(result.get("confidence", 50))
    except (TypeError, ValueError):
        confidence = 50
    confidence = max(0, min(100, confidence))
    confidence_note = str(result.get("confidence_note", "")).strip()

    verdict = {
        "accepted": accepted,
        "issues": issues,
        "confidence": confidence,
        "confidence_note": confidence_note,
    }
    log.info("critic.done", accepted=accepted, n_issues=len(issues), confidence=confidence)
    return {"critic_verdict": verdict, "critic_retries": retries + 1}
