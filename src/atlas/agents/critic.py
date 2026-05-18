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

Return a JSON object with `accepted` (bool) and `issues` (list of short strings).
Accept the brief if there are 0-1 minor issues."""

_SCHEMA = """{"accepted": true|false, "issues": ["short description of each issue"]}"""


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

    verdict = {"accepted": accepted, "issues": issues}
    log.info("critic.done", accepted=accepted, n_issues=len(issues))
    return {"critic_verdict": verdict, "critic_retries": retries + 1}
