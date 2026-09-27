"""
models.py — Pydantic models for the Vera bot.

Three logical groups:
  1. API Request models  (incoming payloads from the platform)
  2. LLM Output models   (structured output parsed from LLM responses)
  3. API Response models  (outgoing payloads back to the platform)
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# 1. API Request Models
# ═══════════════════════════════════════════════════════════════════════════


class CtxBody(BaseModel):
    """Payload sent by the platform when a context event fires."""

    scope: str
    context_id: str
    version: int
    payload: dict
    delivered_at: str


class TickBody(BaseModel):
    """Periodic tick payload — lists available trigger templates."""

    now: str
    available_triggers: list[str] = Field(default_factory=list)


class ReplyBody(BaseModel):
    """Incoming message from a customer or merchant."""

    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str
    message: str
    received_at: str
    turn_number: int


# ═══════════════════════════════════════════════════════════════════════════
# 2. LLM Output Models (structured output from chains)
# ═══════════════════════════════════════════════════════════════════════════


class IntentResult(BaseModel):
    """Classification of the customer's intent."""

    intent: Literal[
        "AUTO_REPLY",
        "EXPLICIT_ACTION",
        "QUESTION",
        "OBJECTION",
        "HOSTILE",
        "OUT_OF_SCOPE",
        "ENGAGED",
    ]


class DraftOutput(BaseModel):
    """Draft message produced by the actor chain."""

    body: str
    cta: Literal[
        "open_ended",
        "binary_yes_no",
        "binary_confirm_cancel",
        "multi_choice_slot",
        "none",
    ]
    send_as: Literal["vera", "merchant_on_behalf"]
    suppression_key: str
    rationale: str
    compulsion_lever: str


class RubricBreakdown(BaseModel):
    """Per-dimension scores (0-10 each) used by the critic."""

    specificity: int = Field(ge=0, le=10)
    category_fit: int = Field(ge=0, le=10)
    merchant_fit: int = Field(ge=0, le=10)
    trigger_relevance: int = Field(ge=0, le=10)
    compulsion: int = Field(ge=0, le=10)


class CriticOutput(BaseModel):
    """Critic chain output — scores the draft and decides pass/fail."""

    rubric: RubricBreakdown
    total_score: int = Field(ge=0, le=50)
    passed: bool
    actionable_critique: str


# ═══════════════════════════════════════════════════════════════════════════
# 3. API Response Models
# ═══════════════════════════════════════════════════════════════════════════


class BotAction(BaseModel):
    """A single outbound action (message / trigger) sent to the platform."""

    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: str
    trigger_id: Optional[str] = None
    template_name: Optional[str] = None
    template_params: Optional[list[str]] = None
    body: str
    cta: str
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    """Response to a /tick request — zero or more proactive actions."""

    actions: list[BotAction] = Field(default_factory=list)


class ReplyResponse(BaseModel):
    """Response to a /reply request — what to do next in the conversation."""

    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    rationale: str
    wait_seconds: Optional[int] = None
