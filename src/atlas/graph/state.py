"""Shared graph state passed between agents. Single source of truth for the run."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class Source(TypedDict):
    """One web result: cleaned content + provenance."""

    url: str
    title: str
    snippet: str
    content: str  # sanitized
    flagged: bool  # set by content guardrail if prompt-injection / suspicious
    flag_reason: str


class SubFinding(TypedDict):
    """Researcher output for one sub-question."""

    sub_question: str
    summary: str
    sources: list[Source]


class CriticVerdict(TypedDict):
    accepted: bool
    issues: list[str]  # unsupported claims, factual errors, etc.
    confidence: int  # 0-100: how well-supported the brief is by its sources
    confidence_note: str  # one-line rationale for the score


class SecurityReport(TypedDict):
    """Aggregated guardrail findings across the run, for the UI's security panel."""

    input_check: dict
    content_checks: list[dict]
    output_check: dict
    blocked: bool
    block_reason: str


class GraphState(TypedDict, total=False):
    """LangGraph state. All fields optional so partial updates from each node merge cleanly."""

    # --- Input ---
    user_query: str

    # --- Planner output ---
    sub_questions: list[str]
    plan_rationale: str

    # --- Researcher output (accumulated, parallel-safe) ---
    findings: Annotated[list[SubFinding], lambda a, b: a + b]

    # --- Writer output ---
    draft_brief: str

    # --- Critic output ---
    critic_verdict: CriticVerdict
    critic_retries: int

    # --- Security ---
    security: SecurityReport

    # --- Final ---
    final_brief: str
    error: str

    # --- Misc / audit ---
    messages: Annotated[list, add_messages]
    # Reducer-merged so parallel Researchers can each contribute their delta safely.
    search_calls: Annotated[int, add]
