"""
category_config.py — Per-category tone, vocabulary, and guardrail rules.

Each key in CATEGORY_CONFIG maps a category slug (e.g. "dentists") to a dict
containing tone directives, allowed vocabulary, taboo phrases, salutation
templates, and example messages that illustrate the desired register.
"""

from __future__ import annotations

from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# Category rule-sets
# ═══════════════════════════════════════════════════════════════════════════

CATEGORY_CONFIG: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------
    # DENTISTS
    # ------------------------------------------------------------------
    "dentists": {
        "tone": "peer_clinical",
        "register": "respectful_collegial",
        "code_mix": "hindi_english_natural",
        "salutations": ["Dr. {first_name}", "Doc"],
        "vocab_allowed": [
            "fluoride varnish", "scaling", "caries", "occlusion",
            "bruxism", "endodontic", "periodontal", "implant",
            "aligner", "veneer", "OPG", "IOPA", "RCT",
            "CAD/CAM", "zirconia", "PFM",
        ],
        "taboos": [
            "guaranteed", "100% safe", "completely cure",
            "miracle", "best in city", "doctor approved",
        ],
        "tone_examples": [
            "Worth a look — JIDA Oct 2026 p.14",
            "This one likely affects your high-risk adult cohort",
            "If your case-mix is mostly cosmetic, may not be relevant",
        ],
    },
    # ------------------------------------------------------------------
    # SALONS
    # ------------------------------------------------------------------
    "salons": {
        "tone": "warm_practical",
        "register": "approachable_expert",
        "code_mix": "hindi_english_natural",
        "salutations": ["Hi {first_name}", "{salon_name} team"],
        "vocab_allowed": [
            "balayage", "highlights", "keratin", "smoothening",
            "hair spa", "manicure", "pedicure", "facial",
            "threading", "waxing", "extensions", "olaplex",
            "wella", "loreal", "schwarzkopf", "redken",
        ],
        "taboos": [
            "guaranteed glow", "permanent results",
            "instant transformation", "miracle", "best in city",
        ],
        "tone_examples": [
            "Bridal season is starting — bookings usually 2x normal in next 4 weeks",
            "Quick one — your Saturday 5-7pm slot has been the strongest this month",
        ],
    },
    # ------------------------------------------------------------------
    # RESTAURANTS
    # ------------------------------------------------------------------
    "restaurants": {
        "tone": "warm_busy_practical",
        "register": "fellow_operator",
        "code_mix": "hindi_english_natural",
        "salutations": ["Hi {first_name}", "{restaurant_name} team"],
        "vocab_allowed": [
            "footfall", "covers", "AOV", "RPC", "table turnover",
            "reservations", "GRO", "weekend brunch", "happy hour",
            "thali", "biryani", "tandoor",
        ],
        "taboos": [
            "best food in city", "guaranteed packed house",
            "miracle marketing", "viral guarantee",
        ],
        "tone_examples": [
            "Quick one — IPL match nights have been 1.5x your weekday avg this season",
            "Spotted: 'biryani delivery' searches in your sublocality up 28% this week",
        ],
    },
    # ------------------------------------------------------------------
    # GYMS
    # ------------------------------------------------------------------
    "gyms": {
        "tone": "energetic_disciplined",
        "register": "coach_to_member",
        "code_mix": "english_primary_some_hindi",
        "salutations": ["Hi {first_name}", "{gym_name} team", "Coach"],
        "vocab_allowed": [
            "footfall", "membership churn", "PT sessions", "PR",
            "1RM", "EMOM", "AMRAP", "split", "cut", "bulk",
            "BMR", "VO2max", "functional", "HIIT", "CrossFit",
            "yoga", "pilates",
        ],
        "taboos": [
            "guaranteed weight loss", "shred in 7 days",
            "miracle transformation", "fastest results",
        ],
        "tone_examples": [
            "Quick check — your weekday 7-9pm slot has been at 90%+ capacity all month",
            "Footfall pattern: April drop-off is normal; bookings recover by 2nd week May",
        ],
    },
    # ------------------------------------------------------------------
    # PHARMACIES
    # ------------------------------------------------------------------
    "pharmacies": {
        "tone": "trustworthy_precise",
        "register": "neighbourhood_pharmacist",
        "code_mix": "hindi_english_natural",
        "salutations": ["Hi {first_name}", "{pharmacy_name} team"],
        "vocab_allowed": [
            "OTC", "schedule H", "schedule X", "generic", "branded",
            "molecule", "MRP", "expiry", "batch", "PCR retail",
            "pharmacist counsel",
        ],
        "taboos": [
            "miracle cure", "guaranteed result", "100% safe",
            "doctor recommended", "best price",
        ],
        "tone_examples": [
            "Quick check — your repeat-prescription customer count is up 18% this month",
            "Heads up: a generic alternative for {molecule} just got approved — likely 30% lower MRP",
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

# Safe default returned when the category slug is unknown.
_DEFAULT_CATEGORY: dict[str, Any] = {
    "tone": "warm_practical",
    "register": "approachable_expert",
    "code_mix": "hindi_english_natural",
    "salutations": ["Hi {first_name}"],
    "vocab_allowed": [],
    "taboos": ["guaranteed", "miracle", "best in city"],
    "tone_examples": [],
}


def get_category_config(slug: str) -> dict[str, Any]:
    """Return the category config for *slug*, or a safe default if unknown.

    The lookup is case-insensitive and strips whitespace so callers don't
    need to normalise input themselves.
    """
    return CATEGORY_CONFIG.get(slug.strip().lower(), _DEFAULT_CATEGORY)
