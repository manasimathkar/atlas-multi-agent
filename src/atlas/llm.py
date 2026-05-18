"""Anthropic client wrapper. Centralizes retry, timeout, and token-budget enforcement.

Every agent uses this rather than calling the SDK directly so:
- we have one place to enforce budgets (defense-in-depth),
- we get consistent retry behavior, and
- we can swap the model from env without touching agent code.
"""

from __future__ import annotations

from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from atlas.config import get_settings
from atlas.logging import get_logger

log = get_logger("atlas.llm")


_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class LLMError(RuntimeError):
    """Raised when the LLM call fails after retries or violates a budget."""


def _client() -> anthropic.Anthropic:
    settings = get_settings()
    return anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.ATLAS_REQUEST_TIMEOUT_S,
    )


@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def call(
    *,
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.2,
    agent: str = "unknown",
) -> str:
    """Make a single completion call. Returns the assistant text.

    All agent calls go through this function for consistent retry/budget enforcement.
    """
    settings = get_settings()
    model = model or settings.ATLAS_MODEL_REASONING
    max_tokens = min(max_tokens or settings.ATLAS_MAX_TOKENS_PER_AGENT, settings.ATLAS_MAX_TOKENS_PER_AGENT)

    log.info("llm.call", agent=agent, model=model, max_tokens=max_tokens, user_len=len(user))

    try:
        resp = _client().messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except _RETRYABLE:
        raise
    except anthropic.BadRequestError as e:
        log.error("llm.bad_request", agent=agent, err=str(e))
        raise LLMError(f"Bad request to LLM: {e}") from e
    except anthropic.AuthenticationError as e:
        log.error("llm.auth_error", agent=agent)
        raise LLMError("Authentication failed; check ANTHROPIC_API_KEY.") from e

    # Extract text from response (content is a list of blocks)
    parts: list[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    text = "".join(parts).strip()

    log.info(
        "llm.response",
        agent=agent,
        model=model,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        stop_reason=resp.stop_reason,
    )
    return text


def call_json(
    *,
    system: str,
    user: str,
    schema_hint: str,
    model: str | None = None,
    max_tokens: int | None = None,
    agent: str = "unknown",
) -> dict[str, Any]:
    """Call LLM and parse a JSON response.

    `schema_hint` is appended to the system prompt to coerce the model into emitting JSON.
    Falls back to {"error": ...} on parse failure rather than raising — agents decide how to react.
    """
    import json
    import re

    full_system = f"{system}\n\nYou MUST respond with valid JSON matching this schema:\n{schema_hint}\n\nReturn ONLY the JSON object, no prose, no markdown fences."
    raw = call(
        system=full_system,
        user=user,
        model=model,
        max_tokens=max_tokens,
        temperature=0.1,
        agent=agent,
    )

    # Strip code fences if model added them despite instructions
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.warning("llm.json_parse_failed", agent=agent, err=str(e), raw_preview=cleaned[:200])
        # Try to find first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"_parse_error": str(e), "_raw": cleaned[:500]}
