"""FastAPI app — custom frontend + SSE streaming of agent progress.

Run locally:
    uvicorn atlas.web.server:app --reload --host 0.0.0.0 --port 8080

The `/api/run` endpoint streams `data: <json>\\n\\n` events. Each event is a JSON
snapshot of the partial graph state, suitable for the frontend to diff and
re-render the live pipeline.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from atlas.graph.build import build_graph
from atlas.logging import get_logger, setup_logging

setup_logging()
log = get_logger("atlas.web")

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Atlas", version="0.1.0")

# Static directory is optional — only mount if it exists with files.
# Currently all CSS/JS is inline in index.html so this is a no-op.
if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_INDEX_HTML = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(content=_INDEX_HTML)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


def _serialize(state: dict[str, Any]) -> str:
    """Drop non-serializable fields (e.g., messages) and dump JSON."""
    clean = {k: v for k, v in state.items() if k != "messages"}
    return json.dumps(clean, default=str)


@app.get("/api/run")
async def run_stream(q: str = Query(..., min_length=1, max_length=2000)) -> StreamingResponse:
    """Stream agent progress as Server-Sent Events.

    Each event payload is the current full graph state (sans messages) as JSON.
    The frontend infers which agents have completed by which state fields are populated.
    """

    async def event_gen():
        graph = build_graph()
        initial = {"user_query": q, "search_calls": 0, "critic_retries": 0, "findings": []}
        try:
            # Use the async stream so we don't block uvicorn's event loop.
            async for event in graph.astream(initial, stream_mode="values"):
                yield f"event: state\ndata: {_serialize(event)}\n\n"
                # Yield control briefly so SSE flushes to client promptly.
                await asyncio.sleep(0)
            yield "event: done\ndata: {}\n\n"
        except Exception as e:  # noqa: BLE001
            log.error("run.failed", err=str(e))
            err_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering (App Runner / nginx)
            "Connection": "keep-alive",
        },
    )
