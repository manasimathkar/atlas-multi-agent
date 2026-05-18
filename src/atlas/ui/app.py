"""Streamlit UI for Atlas — research brief generator.

Run with: streamlit run src/atlas/ui/app.py
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

import streamlit as st

from atlas.graph.build import build_graph
from atlas.logging import setup_logging

setup_logging()


# ───────────────────────────── Page config & global CSS ─────────────────────────────

st.set_page_config(
    page_title="Atlas — Research Brief Generator",
    layout="wide",
    page_icon="🧭",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
/* Page padding */
.main .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1180px; }

/* Header */
.atlas-header { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
.atlas-logo {
  width: 44px; height: 44px; border-radius: 10px;
  background: linear-gradient(135deg, #0F62FE 0%, #0043CE 100%);
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 22px; font-weight: 700;
  box-shadow: 0 4px 12px rgba(15, 98, 254, 0.25);
}
.atlas-title { font-size: 28px; font-weight: 700; color: #161616; line-height: 1.1; margin: 0; }
.atlas-subtitle { font-size: 14px; color: #525252; margin: 2px 0 0 0; }
.atlas-divider { border: none; border-top: 1px solid #E0E0E0; margin: 18px 0 22px 0; }

/* Pipeline */
.pipeline { display: flex; align-items: center; gap: 6px; padding: 12px 14px;
  background: #F4F4F7; border: 1px solid #E0E0E0; border-radius: 10px; margin: 8px 0 14px 0; flex-wrap: wrap; }
.pipeline-step { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #525252; }
.pipeline-step .dot {
  width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; background: #E0E0E0; color: #8D8D8D; transition: all .2s;
}
.pipeline-step.done .dot { background: #24A148; color: white; }
.pipeline-step.active .dot { background: #0F62FE; color: white; animation: pulse 1.2s infinite; }
.pipeline-step.blocked .dot { background: #DA1E28; color: white; }
.pipeline-arrow { color: #C6C6C6; font-size: 12px; padding: 0 2px; }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(15,98,254,.4);} 50% { box-shadow: 0 0 0 6px rgba(15,98,254,0);} }

/* Cards */
.atlas-card { background: white; border: 1px solid #E0E0E0; border-radius: 10px; padding: 18px 22px; margin-bottom: 12px; }
.atlas-card h4 { margin: 0 0 8px 0; font-size: 14px; color: #525252; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }

/* Source list */
.source-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid #F4F4F7; }
.source-row:last-child { border-bottom: none; }
.source-num { flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%; background: #EDF5FF; color: #0F62FE;
  display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }
.source-meta { flex: 1; min-width: 0; }
.source-title { font-size: 14px; font-weight: 500; color: #161616; margin: 0; line-height: 1.35;
  overflow: hidden; text-overflow: ellipsis; }
.source-domain { font-size: 12px; color: #6F6F6F; margin-top: 2px; }
.source-title a { color: #0F62FE; text-decoration: none; }
.source-title a:hover { text-decoration: underline; }

/* Status badges */
.badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .04em; }
.badge-safe { background: #DEFBE6; color: #0E6027; }
.badge-warn { background: #FCF4D6; color: #6F4400; }
.badge-block { background: #FFD7D9; color: #A2191F; }

/* Sample prompt buttons */
.stButton > button[kind="secondary"] {
  text-align: left; white-space: normal; height: auto; padding: 10px 14px;
  background: #F4F4F7; border: 1px solid #E0E0E0; color: #161616; font-size: 13px; line-height: 1.4;
}
.stButton > button[kind="secondary"]:hover { background: #EDF5FF; border-color: #0F62FE; color: #0F62FE; }

/* Primary CTA button */
.stButton > button[kind="primary"] {
  background: #0F62FE; border: none; height: 44px; font-weight: 600; font-size: 14px;
  letter-spacing: .02em; box-shadow: 0 1px 3px rgba(15,98,254,.25);
}
.stButton > button[kind="primary"]:hover { background: #0043CE; }
.stButton > button[kind="primary"]:disabled { background: #C6C6C6; box-shadow: none; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #E0E0E0; }
.stTabs [data-baseweb="tab"] { padding: 10px 18px; font-weight: 500; color: #525252; }
.stTabs [aria-selected="true"] { color: #0F62FE !important; }

/* Sidebar polish */
section[data-testid="stSidebar"] { background: #FAFAFA; border-right: 1px solid #E0E0E0; }
section[data-testid="stSidebar"] h2 { font-size: 16px; color: #161616; }

/* Hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.stDeployButton { display: none !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ───────────────────────────── Header ─────────────────────────────

st.markdown(
    """
    <div class="atlas-header">
      <div class="atlas-logo">A</div>
      <div>
        <p class="atlas-title">Atlas</p>
        <p class="atlas-subtitle">Multi-agent research &amp; brief generator · sourced, fact-checked, guardrail-protected</p>
      </div>
    </div>
    <hr class="atlas-divider" />
    """,
    unsafe_allow_html=True,
)


# ───────────────────────────── Sidebar ─────────────────────────────

with st.sidebar:
    st.markdown("### How it works")
    st.markdown(
        """
Five specialized agents collaborate through a LangGraph state machine:

1. **🛡️ Security · input** — prompt-injection check
2. **🧠 Planner** — decomposes the question
3. **🔎 Researcher × N** — parallel web search
4. **✍️ Writer** — synthesizes the brief
5. **🔍 Critic** — fact-checks against sources
6. **🛡️ Security · output** — PII + policy filter
        """
    )

    st.markdown("### Guardrails")
    st.markdown(
        """
- Prompt-injection detection (input + web content)
- Tool allowlist — search only
- Hard budget caps (sub-Qs, searches, retries)
- PII redaction on output
- Structured audit logs
        """
    )

    st.markdown("### Try a sample")
    samples = [
        "What's the current state of solid-state battery commercialization?",
        "What are the main competing approaches for grid-scale energy storage?",
        "How is the EU AI Act being enforced in 2026?",
        "What's the evidence on GLP-1 agonists for non-diabetic indications?",
    ]
    for s in samples:
        if st.button(s, key=f"s_{hash(s)}", use_container_width=True):
            st.session_state["query"] = s
            st.session_state["auto_run"] = True


# ───────────────────────────── Query input ─────────────────────────────

col_q, col_btn = st.columns([5, 1])
with col_q:
    query = st.text_area(
        "Research question",
        value=st.session_state.get("query", ""),
        height=88,
        placeholder="e.g., What's the current state of solid-state battery commercialization?",
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<div style='height: 6px'></div>", unsafe_allow_html=True)
    run_btn = st.button(
        "Run research",
        type="primary",
        disabled=not query.strip(),
        use_container_width=True,
    )

auto_run = st.session_state.pop("auto_run", False)
should_run = run_btn or (auto_run and query.strip())


# ───────────────────────────── Pipeline helper ─────────────────────────────

STEPS = [
    ("security_input", "🛡️", "Security"),
    ("planner", "🧠", "Planner"),
    ("researcher", "🔎", "Research"),
    ("writer", "✍️", "Writer"),
    ("critic", "🔍", "Critic"),
    ("security_output", "🛡️", "Output"),
]


def render_pipeline(completed: set, active, blocked: set) -> str:
    parts = ['<div class="pipeline">']
    for i, (key, icon, label) in enumerate(STEPS):
        cls = "pipeline-step"
        if key in blocked:
            cls += " blocked"
            mark = "✕"
        elif key in completed:
            cls += " done"
            mark = "✓"
        elif key == active:
            cls += " active"
            mark = "…"
        else:
            mark = str(i + 1)
        parts.append(f'<div class="{cls}"><div class="dot">{mark}</div><span>{icon} {label}</span></div>')
        if i < len(STEPS) - 1:
            parts.append('<span class="pipeline-arrow">›</span>')
    parts.append("</div>")
    return "".join(parts)


# ───────────────────────────── Run ─────────────────────────────

if should_run and query.strip():
    pipeline_slot = st.empty()
    pipeline_slot.markdown(render_pipeline(set(), "security_input", set()), unsafe_allow_html=True)

    started = time.time()
    initial = {"user_query": query.strip(), "search_calls": 0, "critic_retries": 0, "findings": []}

    graph = build_graph()
    final_state: dict = {}

    # Stream events live; capture the merged final state from each tick.
    try:
        for event in graph.stream(initial, stream_mode="values"):
            final_state = event
            done = set()
            if final_state.get("security", {}).get("input_check"):
                done.add("security_input")
            if final_state.get("sub_questions"):
                done.add("planner")
            if final_state.get("findings") and len(final_state["findings"]) >= len(
                final_state.get("sub_questions", [1])
            ):
                done.add("researcher")
            if final_state.get("draft_brief"):
                done.add("writer")
            if final_state.get("critic_verdict"):
                done.add("critic")
            if final_state.get("security", {}).get("output_check") or final_state.get("security", {}).get("blocked"):
                done.add("security_output")

            active = next((k for k, _, _ in STEPS if k not in done), None)
            blocked = set()
            if final_state.get("security", {}).get("blocked"):
                if not final_state.get("sub_questions"):
                    blocked = {"security_input"}
                else:
                    blocked = {"security_output"}
            pipeline_slot.markdown(render_pipeline(done, active, blocked), unsafe_allow_html=True)
    except Exception as e:  # noqa: BLE001
        st.error(f"Run failed: {e}")
        st.exception(e)
        st.stop()

    elapsed = time.time() - started
    sec = final_state.get("security", {}) or {}

    # Final pipeline render
    blocked = set()
    if sec.get("blocked"):
        if not final_state.get("sub_questions"):
            blocked = {"security_input"}
        else:
            blocked = {"security_output"}
        completed_set = {k for k, _, _ in STEPS if k not in blocked and (
            (k == "security_input" and sec.get("input_check"))
            or (k == "planner" and final_state.get("sub_questions"))
            or (k == "researcher" and final_state.get("findings"))
            or (k == "writer" and final_state.get("draft_brief"))
            or (k == "critic" and final_state.get("critic_verdict"))
        )}
    else:
        completed_set = {k for k, _, _ in STEPS}
    pipeline_slot.markdown(render_pipeline(completed_set, None, blocked), unsafe_allow_html=True)

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sub-questions", len(final_state.get("sub_questions", [])))
    m2.metric("Findings", len(final_state.get("findings", [])))
    n_sources = sum(len(f.get("sources", [])) for f in final_state.get("findings", []))
    m3.metric("Sources used", n_sources)
    m4.metric("Run time", f"{elapsed:.1f}s")

    # Tabs
    tab_brief, tab_plan, tab_sources, tab_security, tab_raw = st.tabs(
        ["📄 Brief", "🧠 Plan", "🔎 Sources", "🛡️ Security", "🔬 Raw"]
    )

    with tab_brief:
        brief = final_state.get("final_brief", "")
        if sec.get("blocked"):
            st.error(f"**Blocked:** {sec.get('block_reason', '')}")
            if brief:
                st.markdown(brief)
        elif not brief:
            st.warning("No brief was produced.")
        else:
            st.markdown(brief)

    with tab_plan:
        subs = final_state.get("sub_questions", [])
        rationale = final_state.get("plan_rationale", "")
        if rationale:
            st.markdown(
                f"<div class='atlas-card'><h4>Plan rationale</h4><div>{rationale}</div></div>",
                unsafe_allow_html=True,
            )
        if subs:
            items_html = "".join(f"<div style='padding: 6px 0;'><strong>{i+1}.</strong> {sq}</div>" for i, sq in enumerate(subs))
            st.markdown(
                f"<div class='atlas-card'><h4>Sub-questions</h4>{items_html}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No plan was produced.")

    with tab_sources:
        findings = final_state.get("findings", [])
        if not findings:
            st.info("No sources gathered.")
        for f in findings:
            with st.expander(f["sub_question"], expanded=False):
                if f.get("summary"):
                    st.markdown(f["summary"])
                if f.get("sources"):
                    parts = []
                    for i, s in enumerate(f["sources"], start=1):
                        domain = urlparse(s.get("url", "")).netloc
                        flag = "  ⚠️ flagged" if s.get("flagged") else ""
                        title = s.get("title") or s["url"]
                        parts.append(
                            f'<div class="source-row">'
                            f'<div class="source-num">{i}</div>'
                            f'<div class="source-meta">'
                            f'<p class="source-title"><a href="{s["url"]}" target="_blank">{title}</a></p>'
                            f'<div class="source-domain">{domain}{flag}</div>'
                            f"</div></div>"
                        )
                    st.markdown("".join(parts), unsafe_allow_html=True)

    with tab_security:
        c1, c2, c3 = st.columns(3)
        in_v = sec.get("input_check", {}).get("verdict", "—")
        out_v = sec.get("output_check", {}).get("verdict", "—")
        n_flags = len(sec.get("content_checks", []))

        def badge(v: str) -> str:
            cls = "badge-safe" if v == "safe" else "badge-block" if v in ("injection", "violation") else "badge-warn"
            return f'<span class="badge {cls}">{v}</span>'

        c1.markdown(f"**Input check**<br>{badge(in_v)}", unsafe_allow_html=True)
        c2.markdown(f"**Web-content flags**<br>{n_flags} of {n_sources}", unsafe_allow_html=True)
        c3.markdown(f"**Output check**<br>{badge(out_v)}", unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("#### Input checkpoint")
        ic = sec.get("input_check", {})
        if ic:
            st.json(ic, expanded=False)
        else:
            st.caption("No input check recorded.")

        st.markdown("#### Web content scans")
        content = sec.get("content_checks", [])
        if content:
            for c in content:
                st.markdown(f"- `{c.get('url','')}` — {c.get('reason','')}")
        else:
            st.caption("No content flags raised — all fetched sources passed injection scan.")

        st.markdown("#### Output checkpoint")
        oc = sec.get("output_check", {})
        if oc:
            st.json({k: v for k, v in oc.items() if k != "redacted_brief"}, expanded=False)
            if oc.get("pii_hits"):
                st.warning(f"PII detected and redacted: {', '.join(oc['pii_hits'])}")
        else:
            st.caption("No output check recorded.")

    with tab_raw:
        st.caption("Full final graph state (for debugging / audit).")
        clean = {k: v for k, v in final_state.items() if k != "messages"}
        st.json(clean, expanded=False)

else:
    # Idle state
    st.markdown(
        """
        <div class="atlas-card">
          <h4>Get started</h4>
          <div style="color: #525252; line-height: 1.55;">
            Type a research question above or pick a sample from the sidebar.
            Atlas decomposes the question into sub-questions, runs parallel web searches,
            synthesizes a sourced brief, and applies prompt-injection &amp; PII guardrails at three checkpoints.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
