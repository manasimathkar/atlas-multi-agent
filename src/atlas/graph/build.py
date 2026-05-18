"""LangGraph orchestration.

Topology:

    START
      │
      ▼
  [security_input]  ── (blocked) ──▶ END
      │
      ▼
   [planner]
      │
      ▼
   (fan-out via Send: one researcher per sub-question)
      │
      ▼
   [writer]
      │
      ▼
   [critic]
      │
      ├── (accepted) ─────▶ [security_output] ──▶ END
      │
      └── (rejected & retries<max) ─▶ [writer]   (one retry loop)
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from atlas.agents.critic import critic_node
from atlas.agents.planner import planner_node
from atlas.agents.researcher import researcher_for
from atlas.agents.security import security_input_node, security_output_node
from atlas.agents.writer import writer_node
from atlas.config import get_settings
from atlas.graph.state import GraphState


# --- Routing functions ---

def _route_after_input_security(state: GraphState) -> str:
    sec = state.get("security") or {}
    if sec.get("blocked"):
        return END
    return "planner"


def _route_after_planner(state: GraphState):
    """Fan out one Researcher per sub-question. Researchers run in parallel."""
    subs = state.get("sub_questions", [])
    if not subs:
        # Planner declined → skip to security_output which will surface the error
        return "writer"
    return [Send("researcher", {"_sub": sq, **state}) for sq in subs]


def _route_after_critic(state: GraphState) -> str:
    verdict = state.get("critic_verdict") or {}
    retries = state.get("critic_retries", 0)
    max_retries = get_settings().ATLAS_MAX_CRITIC_RETRIES + 1  # +1 because we count initial pass

    if verdict.get("accepted"):
        return "security_output"
    if retries >= max_retries:
        # Out of retries: accept anyway but mark issues in security report
        return "security_output"
    return "writer"


# --- Researcher dispatcher ---
# LangGraph's Send needs a single node; we use a dispatcher that reads `_sub` and calls
# researcher_for(sub). This keeps the graph topology simple.

def _researcher_dispatcher(state):
    sub = state.get("_sub") or ""
    node = researcher_for(sub)
    return node(state)


# --- Build the graph ---

def build_graph():
    g = StateGraph(GraphState)

    g.add_node("security_input", security_input_node)
    g.add_node("planner", planner_node)
    g.add_node("researcher", _researcher_dispatcher)
    g.add_node("writer", writer_node)
    g.add_node("critic", critic_node)
    g.add_node("security_output", security_output_node)

    g.add_edge(START, "security_input")
    g.add_conditional_edges("security_input", _route_after_input_security, {END: END, "planner": "planner"})
    g.add_conditional_edges("planner", _route_after_planner, ["researcher", "writer"])
    g.add_edge("researcher", "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", _route_after_critic, {"writer": "writer", "security_output": "security_output"})
    g.add_edge("security_output", END)

    return g.compile()
