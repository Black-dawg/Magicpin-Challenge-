"""
validators.py – Deterministic Tier-1 validation for outbound messages.

Every candidate body is run through these cheap, regex / keyword checks
*before* it is sent to the merchant.  Failures are returned as typed
error codes so the caller can decide whether to regenerate or suppress.
"""

import re
from typing import List, Dict

from category_config import CATEGORY_CONFIG

# ---------------------------------------------------------------------------
# Compile-once patterns
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://|www\.|//.+\..+", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+")

# Platform jargon that should never leak into merchant-facing copy
_JARGON_WORDS: List[str] = [
    "ctr",
    "impressions",
    "platform signals",
    "conversion rate",
    "click-through",
]

# Qualifying / hedging phrases – only flagged in EXECUTE_ACTION mode
# where we expect a direct, confident action statement.
_QUALIFYING_PHRASES: List[str] = [
    "would you",
    "do you",
    "can you tell",
    "what if",
    "how about",
]


def validate(
    body: str,
    category_slug: str,
    conversation_bodies: List[str],
    fsm_mode: str = "",
) -> Dict:
    """Run all Tier-1 deterministic checks on *body*.

    Parameters
    ----------
    body:
        The candidate outbound message text.
    category_slug:
        Active category key into ``CATEGORY_CONFIG`` (for taboo words).
    conversation_bodies:
        Previously-sent bodies in this conversation (duplicate check).
    fsm_mode:
        Current FSM mode string.  When ``"EXECUTE_ACTION"`` an extra
        qualifying-phrase check is applied.

    Returns
    -------
    dict
        ``{"passed": bool, "errors": list[str], "number_count": int}``
    """
    errors: List[str] = []
    body_lower: str = body.lower()

    # 1. URL leak ──────────────────────────────────────────────────────────
    if _URL_RE.search(body):
        errors.append("CONTAINS_URL")

    # 2. Platform jargon ───────────────────────────────────────────────────
    for word in _JARGON_WORDS:
        if word in body_lower:
            errors.append(f"JARGON:{word}")

    # 3. Category-specific taboo words ─────────────────────────────────────
    cat_cfg = CATEGORY_CONFIG.get(category_slug, {})
    taboo_words: List[str] = cat_cfg.get("taboo_words", [])
    for word in taboo_words:
        if word.lower() in body_lower:
            errors.append(f"TABOO:{word}")

    # 4. Repeated body (exact duplicate in this conversation) ──────────────
    if body in conversation_bodies:
        errors.append("REPEAT_BODY")

    # 5. Multiple CTAs (more than 2 question marks) ────────────────────────
    if body.count("?") > 2:
        errors.append("MULTIPLE_CTAS")

    # 6. Low number count (fewer than 2 numeric tokens) ────────────────────
    # We only enforce this for proactive triggers, not conversational replies.
    numbers_found: List[str] = _NUMBER_RE.findall(body)
    number_count: int = len(numbers_found)
    if fsm_mode != "ENGAGE_NORMAL" and number_count < 2:
        errors.append("LOW_NUMBER_COUNT")

    # 7. Qualifying / hedging language (only in EXECUTE_ACTION mode) ───────
    if fsm_mode == "EXECUTE_ACTION":
        for phrase in _QUALIFYING_PHRASES:
            if phrase in body_lower:
                errors.append("QUALIFYING_AFTER_INTENT")
                break  # one flag is enough

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "number_count": number_count,
    }
