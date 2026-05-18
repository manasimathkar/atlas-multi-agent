"""CLI entry: `python -m atlas.cli "Your research question here"`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from atlas.graph.build import build_graph
from atlas.logging import setup_logging


def run(query: str) -> dict:
    setup_logging()
    graph = build_graph()
    initial = {"user_query": query, "search_calls": 0, "critic_retries": 0, "findings": []}
    return graph.invoke(initial)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m atlas.cli \"Your research question\"", file=sys.stderr)
        return 2
    query = " ".join(sys.argv[1:])
    result = run(query)

    print("\n" + "=" * 80)
    print("FINAL BRIEF")
    print("=" * 80)
    print(result.get("final_brief", "(no brief)"))
    print("\n" + "=" * 80)
    print("SECURITY REPORT")
    print("=" * 80)
    print(json.dumps(result.get("security", {}), indent=2, default=str))

    # Persist a run record
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    out_file = runs_dir / f"run_{abs(hash(query)) % 10**8}.json"
    out_file.write_text(json.dumps({k: v for k, v in result.items() if k != "messages"}, indent=2, default=str))
    print(f"\nFull run saved to: {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
