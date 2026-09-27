"""
memory.py – Conversation-state manager & lightweight FSM.

Tracks per-conversation signals (auto-reply streaks, hostility,
action intent) and decides the next reply action without touching
the LLM.  Also handles merchant suppression, body dedup, and
conversation history bookkeeping.
"""

import hashlib
import time
from collections import defaultdict
from typing import Dict, List, Optional


class ConversationStateManager:
    """In-memory conversation state tracker powering the reply FSM."""

    # ------------------------------------------------------------------
    # Canned / auto-reply phrases (EN + HI)
    # ------------------------------------------------------------------
    CANNED_PHRASES_EN: List[str] = [
        "thank you for contacting",
        "our team will respond shortly",
        "automated assistant",
        "we are currently closed",
        "away right now",
        "will get back to you",
        "our working hours",
        "thank you for reaching out",
        "your message is important",
        "we will respond as soon as possible",
    ]

    CANNED_PHRASES_HI: List[str] = [
        "aapki jaankari ke liye bahut-bahut shukriya",
        "hamari team tak pahuncha diti hoon",
        "main ek automated assistant hoon",
        "shukriya, hamare executive",
        "humari team aapse sampark karegi",
        "hamare working hours",
    ]

    # ------------------------------------------------------------------
    # Hostile-exit keywords
    # ------------------------------------------------------------------
    HOSTILE_KEYWORDS: List[str] = [
        "stop",
        "spam",
        "useless",
        "bothering",
        "harassment",
        "unsubscribe",
        "not interested",
        "don't message",
        "band karo",
        "mat bhejo",
        "pareshan mat karo",
        "bakwas",
        "bekar",
        "rahne do",
    ]

    # ------------------------------------------------------------------
    # Action-intent triggers
    # ------------------------------------------------------------------
    ACTION_INTENTS: List[str] = [
        "kar do",
        "karo",
        "theek hai",
        "thik hai",
        "haan",
        "chalo",
        "go ahead",
        "ban do",
        "bana do",
        "mujhe judna hai",
        "haan kar do",
        "chalega",
        "lets do it",
        "let's do it",
        "what's next",
        "whats next",
        "yes do it",
        "sign me up",
        "ok do it",
        "done",
        "yes please",
        "sure",
        "proceed",
    ]

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        # conv_id -> count of consecutive auto-replies detected
        self._auto_counts: Dict[str, int] = defaultdict(int)
        # conv_id -> set of MD5 hashes of messages already seen as auto
        self._auto_hashes: Dict[str, set] = defaultdict(set)

        # merchant_id -> suppression expiry (epoch seconds)
        self._suppressions: Dict[str, float] = {}

        # conv_id -> set of previously-sent body strings
        self._sent_bodies: Dict[str, set] = defaultdict(set)

        # conv_id -> ordered history  [{"role": ..., "message": ...}, ...]
        self._histories: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    # ==================================================================
    # Auto-reply detection
    # ==================================================================
    def detect_auto_reply(self, merchant_id: str, message: str) -> bool:
        """Return *True* if *message* looks like a canned auto-reply."""
        msg_hash: str = hashlib.md5(message.encode("utf-8")).hexdigest()
        msg_lower: str = message.lower()

        is_canned: bool = any(
            phrase in msg_lower
            for phrase in self.CANNED_PHRASES_EN + self.CANNED_PHRASES_HI
        )

        is_duplicate_hash: bool = msg_hash in self._auto_hashes[merchant_id]

        if is_canned or is_duplicate_hash:
            self._auto_hashes[merchant_id].add(msg_hash)
            self._auto_counts[merchant_id] += 1
            return True

        return False

    # ==================================================================
    # Hostile detection
    # ==================================================================
    def detect_hostile(self, message: str) -> bool:
        """Return *True* if *message* contains a hostile / opt-out keyword."""
        msg_lower: str = message.lower()
        return any(kw in msg_lower for kw in self.HOSTILE_KEYWORDS)

    # ==================================================================
    # Action-intent detection
    # ==================================================================
    def detect_action_intent(self, message: str) -> bool:
        """Return *True* if the merchant is signalling agreement / action."""
        msg_lower: str = message.lower()
        return any(intent in msg_lower for intent in self.ACTION_INTENTS)

    # ==================================================================
    # FSM: decide next reply action
    # ==================================================================
    def get_reply_action(
        self,
        conv_id: str,
        merchant_id: str,
        message: str,
        turn_number: int,
    ) -> Dict:
        # --- 1. Auto-reply handling ------------------------------------
        if self.detect_auto_reply(merchant_id, message):
            count: int = self._auto_counts[merchant_id]
            if count >= 3:
                return {"action": "end", "rationale": "Auto-reply limit reached. Ending."}
            if count >= 2:
                return {"action": "wait", "wait_seconds": 86400, "rationale": "Auto-reply detected twice. Waiting 24h."}
            # count == 1
            return {"action": "send", "mode": "AUTO_REPLY_PROBE", "rationale": "First auto-reply detected."}

        # --- 2. Hostile ------------------------------------------------
        if self.detect_hostile(message):
            return {"action": "end", "rationale": "Hostile opt-out detected."}

        # --- 3. Action intent ------------------------------------------
        if self.detect_action_intent(message):
            return {"action": "send", "mode": "EXECUTE_ACTION", "rationale": "Action intent detected."}

        # --- 4. Normal engagement --------------------------------------
        return {"action": "send", "mode": "ENGAGE_NORMAL", "rationale": "Normal reply."}

    # ==================================================================
    # Merchant-level suppression
    # ==================================================================
    def suppress_merchant(self, merchant_id: str, days: int = 30) -> None:
        """Suppress all outreach to *merchant_id* for *days* days."""
        self._suppressions[merchant_id] = time.time() + (days * 86400)

    def is_suppressed(self, merchant_id: str) -> bool:
        """Return *True* if the merchant is currently suppressed."""
        expiry: Optional[float] = self._suppressions.get(merchant_id)
        if expiry is None:
            return False
        if time.time() >= expiry:
            # Suppression expired – clean up
            del self._suppressions[merchant_id]
            return False
        return True

    # ==================================================================
    # Body dedup
    # ==================================================================
    def record_sent_body(self, conv_id: str, body: str) -> None:
        """Record *body* so future duplicates can be detected."""
        self._sent_bodies[conv_id].add(body)

    def is_duplicate_body(self, conv_id: str, body: str) -> bool:
        """Return *True* if *body* was already sent in this conversation."""
        return body in self._sent_bodies[conv_id]

    # ==================================================================
    # Conversation history
    # ==================================================================
    def get_conversation_history(self, conv_id: str) -> List[Dict[str, str]]:
        """Return the full ordered history for *conv_id*."""
        return list(self._histories[conv_id])

    def add_to_history(
        self,
        conv_id: str,
        role: str,
        message: str,
    ) -> None:
        """Append a turn to the conversation history."""
        self._histories[conv_id].append({"role": role, "message": message})
