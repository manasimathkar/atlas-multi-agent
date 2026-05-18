# Atlas — Multi-Agent Research & Brief Generator

A live multi-agent system that takes a research question and returns a sourced 1-page brief. Built for the Wipro Junior FDE pre-screening assignment.

> **Live demo:** _(deployment URL — added after deploy)_

## What it does

You ask a question like *"What's the current state of solid-state battery commercialization?"* and Atlas:

1. **Plans** — decomposes the question into 3–5 sub-questions
2. **Researches** — searches the web in parallel for each sub-question, with citations
3. **Writes** — synthesizes a structured brief
4. **Critiques** — fact-checks every claim against the sources; loops back if too many are unsupported
5. **Secures** — scans inputs, fetched web content, and the final output at three checkpoints

## Architecture

Five specialized agents orchestrated by a LangGraph state machine:

| Agent | Role | Tools | Model |
|---|---|---|---|
| **Planner** | Decompose user query into sub-questions | none | Sonnet |
| **Researcher** | Web search + summarize per sub-question (parallel fan-out) | Tavily search (allowlisted) | Sonnet |
| **Writer** | Synthesize draft brief with inline citations | none | Sonnet |
| **Critic** | Fact-check claims against research bundle | none | Sonnet |
| **Security Agent** | Input / web-content / output checkpoints | regex + Haiku classifier | Haiku |

See [`docs/architecture.svg`](docs/architecture.svg) for the diagram and [`docs/report.md`](docs/report.md) for the written report.

## Quickstart (local)

```bash
# 1. Clone and enter
git clone <repo-url> && cd atlas

# 2. Create venv + install
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Configure secrets
cp .env.example .env
# edit .env — paste your ANTHROPIC_API_KEY and TAVILY_API_KEY

# 4. Run the UI (FastAPI + custom frontend)
uvicorn atlas.web.server:app --reload --host 0.0.0.0 --port 8080
```

Open **http://localhost:8080** in your browser.

## Run a single query from CLI

```bash
python -m atlas.cli "What's the current state of solid-state battery commercialization?"
```

## Tests

```bash
pytest -v
```

## Deploy (AWS App Runner)

```bash
# Build and push to ECR
./scripts/deploy.sh
```

See [`docs/deploy.md`](docs/deploy.md) for full instructions.

## Sample prompts

- *"What are the main competing approaches for grid-scale energy storage?"*
- *"How is the EU AI Act being enforced in 2026?"*
- *"What's the evidence on GLP-1 agonists for non-diabetic indications?"*

## Security guardrails (summary)

| Threat | Mitigation |
|---|---|
| Prompt injection in user input | Input classifier (regex + Haiku LLM judge), role-locked system prompts |
| Prompt injection in fetched web content | HTML sanitization, content-injection classifier, never echo raw HTML to other agents |
| PII / secrets in output | Regex + Haiku classifier on final output |
| Runaway agents | Hard caps: max sub-questions, max search calls, max critic retries, per-agent token budgets, request timeouts |
| Unauthorized tool use | Per-agent tool allowlist (only Researcher can search; no agent can hit arbitrary URLs) |
| Auditability | Structured logging of every agent step, model call, tool call |

## License

MIT
