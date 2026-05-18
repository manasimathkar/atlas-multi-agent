"""Security agent — orchestrates the three guardrail checkpoints.

This is a *coordinating* agent: the actual checks live in atlas.guardrails.* so they're
independently testable. The Security agent's role is to:
  - run the right check at the right point in the graph,
  - aggregate findings into a single SecurityReport,
  - decide when to BLOCK the run (fail-closed).
"""

from __future__ import annotations

from atlas.graph.state import GraphState, SecurityReport
from atlas.guardrails.input import check_user_input
from atlas.guardrails.output import check_output
from atlas.logging import get_logger

log = get_logger("atlas.agents.security")


def security_input_node(state: GraphState) -> dict:
    """First checkpoint: scan the user's query before the Planner sees it."""
    query = state["user_query"]
    result = check_user_input(query)
    log.info("security.input", verdict=result["verdict"])

    sec: SecurityReport = state.get("security") or {
        "input_check": {},
        "content_checks": [],
        "output_check": {},
        "blocked": False,
        "block_reason": "",
    }
    sec["input_check"] = result

    if result["verdict"] in ("injection", "too_long", "too_short"):
        sec["blocked"] = True
        sec["block_reason"] = f"Input rejected: {result['reason']}"
        return {
            "security": sec,
            "final_brief": _refusal_message(result),
            "error": sec["block_reason"],
        }

    return {"security": sec}


def security_output_node(state: GraphState) -> dict:
    """Final checkpoint: scan the draft before returning to the user."""
    brief = state.get("draft_brief", "")
    sec: SecurityReport = state.get("security") or {
        "input_check": {},
        "content_checks": [],
        "output_check": {},
        "blocked": False,
        "block_reason": "",
    }

    # Aggregate content-check findings from researcher fan-out
    content_findings = []
    for f in state.get("findings", []):
        for s in f.get("sources", []):
            if s.get("flagged"):
                content_findings.append({"url": s["url"], "reason": s["flag_reason"]})
    sec["content_checks"] = content_findings

    if not brief:
        sec["blocked"] = True
        sec["block_reason"] = "No draft produced."
        return {"security": sec, "final_brief": "", "error": "no_draft"}

    out_check = check_output(brief)
    sec["output_check"] = out_check

    if out_check["verdict"] == "violation":
        sec["blocked"] = True
        sec["block_reason"] = f"Output policy violation: {out_check['reason']}"
        return {
            "security": sec,
            "final_brief": "[Atlas blocked this response per output policy.]",
            "error": sec["block_reason"],
        }

    final = out_check["redacted_brief"]
    log.info("security.output", pii_hits=out_check["pii_hits"])
    return {"security": sec, "final_brief": final}


def _refusal_message(input_result: dict) -> str:
    verdict = input_result["verdict"]
    if verdict == "injection":
        return (
            "**Request blocked.** Your input contained patterns associated with prompt injection. "
            "Please rephrase as a plain research question — for example: *\"What is the current state of X?\"*"
        )
    if verdict == "too_long":
        return "**Request blocked.** Please keep your research question under 2000 characters."
    if verdict == "too_short":
        return "**Request blocked.** Please provide a more specific research question (at least a sentence)."
    return "**Request blocked.**"
