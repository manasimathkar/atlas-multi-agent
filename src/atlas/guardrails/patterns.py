"""Regex-based guardrail patterns. Cheap first-pass before LLM-based judge.

These are deliberately conservative: a true positive here short-circuits the LLM judge
and saves tokens. False positives are acceptable because the LLM judge runs as a backstop
on inputs that pass regex; the regex is only authoritative for the *block* path on web
content (where we want to fail closed).
"""

from __future__ import annotations

import re

# --- Prompt-injection markers (case-insensitive). ---
# Common patterns observed in jailbreak corpora and real-world injection PoCs.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_previous", re.compile(r"ignore\s+(all\s+)?(previous|prior|above|preceding)\s+(instructions|prompts|rules|directives)", re.I)),
    ("override_system", re.compile(r"(disregard|override|forget)\s+(the\s+)?(system|developer|prior)\s+(prompt|message|instructions)", re.I)),
    ("role_hijack", re.compile(r"you\s+are\s+now\s+(a\s+|an\s+)?(different|new|unrestricted|jailbroken|DAN|developer)", re.I)),
    ("reveal_system", re.compile(r"(reveal|print|show|output|repeat)\s+(your\s+)?(system\s+prompt|initial\s+instructions|hidden\s+instructions)", re.I)),
    ("execute_code", re.compile(r"(execute|run|eval)\s+the\s+following\s+(code|command|shell|python)", re.I)),
    ("data_exfil", re.compile(r"(send|post|exfiltrate|leak)\s+(this|the|all)\s+.*(to|via)\s+(http|url|webhook|endpoint)", re.I)),
    ("hidden_instruction", re.compile(r"\[(INST|SYSTEM|ADMIN)\].{0,200}\[/\1\]", re.I | re.S)),
    ("zero_width", re.compile(r"[​-‏‪-‮﻿]")),  # invisible chars often used to hide prompts
]

# --- PII patterns (output filter). ---
PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ssn_us", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("email", re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
    ("phone_us", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("api_key_like", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|tvly-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b")),
]


def find_injection_hits(text: str) -> list[str]:
    """Return list of pattern names that matched. Empty list = no regex hits."""
    return [name for name, pat in INJECTION_PATTERNS if pat.search(text)]


def find_pii_hits(text: str) -> list[str]:
    return [name for name, pat in PII_PATTERNS if pat.search(text)]


def redact_pii(text: str) -> str:
    """Replace PII matches with category tags. Used on outputs."""
    out = text
    for name, pat in PII_PATTERNS:
        out = pat.sub(f"[REDACTED:{name}]", out)
    return out
