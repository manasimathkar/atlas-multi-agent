"""Structural tests on the compiled graph. No LLM/network calls."""

from __future__ import annotations

import os

# Ensure config loads in tests without real keys
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test")


def test_graph_compiles():
    from atlas.graph.build import build_graph

    g = build_graph()
    assert g is not None


def test_graph_has_expected_nodes():
    from atlas.graph.build import build_graph

    g = build_graph()
    # The compiled graph exposes a `.nodes` mapping
    node_names = set(g.get_graph().nodes.keys())
    for required in ("security_input", "planner", "researcher", "writer", "critic", "security_output"):
        assert required in node_names, f"Missing node: {required}"
