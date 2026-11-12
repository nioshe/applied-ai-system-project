"""Input guardrails: reject or clean a request before it reaches retrieval."""
import re
from dataclasses import dataclass

MAX_QUERY_CHARS = 300
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"system prompt",
    r"disregard .{0,30}(instructions|rules)",
    r"you are now",
    r"reveal .{0,30}(prompt|instructions|key)",
]


@dataclass
class GuardrailResult:
    ok: bool
    query: str = ""
    reason: str = ""


def check_query(query) -> GuardrailResult:
    """Validate and clean a user request. Never raises; returns ok=False with a reason instead."""
    if not isinstance(query, str):
        return GuardrailResult(False, reason="Request must be text.")
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return GuardrailResult(False, reason="Request is empty. Describe a mood, activity or genre.")
    if len(cleaned) > MAX_QUERY_CHARS:
        return GuardrailResult(False, reason=f"Request is too long (max {MAX_QUERY_CHARS} characters).")
    if not re.search(r"[A-Za-z]", cleaned):
        return GuardrailResult(False, reason="Request has no words I can understand.")
    for pat in INJECTION_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GuardrailResult(False, reason="Request looks like an attempt to change my instructions; ignored.")
    return GuardrailResult(True, query=cleaned)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Keep a numeric preference (e.g. energy) inside its valid range."""
    return max(lo, min(hi, value))
