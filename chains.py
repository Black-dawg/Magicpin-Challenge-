import json
from langchain_core.prompts import ChatPromptTemplate
from config import actor_llm, fast_llm
from models import IntentResult, DraftOutput, CriticOutput
from validators import validate
from memory import ConversationStateManager
from rag_engine import ContextRAG
from category_config import get_category_config

TRIGGER_PROMPT_MAP = {
    "research_digest": "Frame as a peer sharing a relevant research finding. Cite the source (journal, page). Connect to merchant's patient/customer cohort.",
    "regulation_change": "Frame as an urgent compliance alert. Name the regulation body. Quantify affected customers. Offer to draft notification.",
    "festival_upcoming": "Frame as a timely opportunity. Name the festival and days remaining. Suggest a specific offer from their catalog.",
    "ipl_match_today": "Frame as strategic advice. Provide match details. Give contrarian insight if applicable (e.g., dine-in drops during home matches). Suggest delivery push.",
    "perf_dip": "Frame as a supportive alert. Show the exact metric drop. Normalize if seasonal. Suggest a concrete next step.",
    "perf_spike": "Frame as a celebration + amplification opportunity. Show the exact metric increase. Suggest how to capitalize.",
    "milestone_reached": "Frame as congratulations. Name the milestone. Suggest how to leverage it (e.g., share on GBP).",
    "curious_ask_due": "Frame as a casual question asking the merchant about their business. Promise to turn their answer into a Google post or WhatsApp template. Keep it low-effort.",
    "review_theme_emerged": "Frame as a pattern spotted in customer reviews. Quote the theme. Suggest an action to address it.",
    "recall_due": "Frame as a warm recall reminder from the merchant's clinic/store. Use merchant_on_behalf. Include specific slots and pricing. Honor language preference.",
    "customer_lapsed_soft": "Frame as a warm winback. No guilt. Mention what's new since their last visit. Offer a specific incentive.",
    "customer_lapsed_hard": "Frame as a warm winback. Zero shame. Mention new offerings. Strong barrier removal (free trial, no commitment).",
    "appointment_tomorrow": "Frame as a friendly reminder. Confirm time and service. Offer reschedule option.",
    "competitor_opened": "Frame with curiosity lever. Mention competitor distance. Highlight merchant's strengths.",
    "chronic_refill_due": "Frame as a precise refill reminder. List exact molecules. Give exact runout date. Show pricing with discounts.",
    "seasonal_perf_dip": "Frame as seasonal normalization. Show benchmark data. Suggest retention focus over acquisition.",
    "default": "Frame as a helpful nudge. Be specific. Use data from context."
}

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", "Classify the merchant's reply into one of: AUTO_REPLY, EXPLICIT_ACTION, QUESTION, OBJECTION, HOSTILE, OUT_OF_SCOPE, ENGAGED. Be precise."),
    ("human", "Conversation history: {history}\nReply: {reply}")
])
intent_chain = intent_prompt | fast_llm.with_structured_output(IntentResult)

def actor_chain_fn(trigger_framing, category_config, merchant_data, trigger_data, customer_data, retrieved_fact, fsm_mode, critic_feedback, history="None"):
    number_rule = "9. Include at least 3 verifiable numbers from context (prices, percentages, dates, counts)." if trigger_data.get("id") != "reply_trigger" else "9. Address the merchant's question directly. You do not need to force numbers if not relevant."
    cta_rule = "11. Put a SINGLE CTA on the LAST line. Never ask multiple questions." if trigger_data.get("id") != "reply_trigger" else "11. Ask a question ONLY if you need more information to proceed. Otherwise, just acknowledge."
    
    prompt_str = f"""You are Vera, magicpin's merchant growth partner for Indian local businesses.
You talk on WhatsApp in natural Romanized Hindi-English (Hinglish).

ABSOLUTE RULES (VIOLATION = SCORE PENALTY):
1. NEVER include any URL (https://, www., .com, .in).
2. NEVER fabricate data not in the provided context.
3. NEVER use platform jargon with merchants (CTR, impressions, signals).
4. NEVER use category taboo words: {category_config.get('taboos', [])}.

COMPOSITION RULES:
6. Use English for business terms. Use Hindi for warmth and connectors.
7. Match category voice: {category_config.get('tone')} / {category_config.get('register')}.
8. Use domain vocabulary: {category_config.get('vocab_allowed')}.
{number_rule}
10. Keep under 70 words. Use WhatsApp bold (*...*) for key numbers.
{cta_rule}

TRIGGER SPECIFIC FRAMING: {trigger_framing}

FSM MODE INSTRUCTION:
If FSM mode is EXECUTE_ACTION: Use action words (done, sending, draft, confirm, proceed, next). NEVER use qualifying words (would you, do you, can you tell, what if, how about). Current FSM mode: {fsm_mode}

CRITIC FEEDBACK FROM PREVIOUS ATTEMPT (if any, fix these): {critic_feedback}"""

    actor_prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_str),
        ("human", "Conversation History:\n{history}\n\nMerchant: {merchant_data}\nTrigger: {trigger_data}\nCustomer: {customer_data}\nFact: {retrieved_fact}")
    ])
    
    actor_chain = actor_prompt | actor_llm.with_structured_output(DraftOutput)
    return actor_chain.invoke({
        "history": history,
        "merchant_data": json.dumps(merchant_data),
        "trigger_data": json.dumps(trigger_data),
        "customer_data": json.dumps(customer_data) if customer_data else "None",
        "retrieved_fact": json.dumps(retrieved_fact) if retrieved_fact else "None"
    })

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a strict evaluator for WhatsApp merchant messages.
Score the draft on these 5 dimensions (0-10 each).
1. Specificity: verifiable numbers, dates, source citations?
2. Category Fit: tone match? Any taboo word violations?
3. Merchant Fit: personalized to THIS merchant?
4. Trigger Relevance: is the "why now" clearly tied to the trigger?
5. Compulsion: compulsion lever used? single terminal CTA?

Pass threshold: total >= 42 AND all subscores >= 7."""),
    ("human", "Draft:\n{draft_body}\nContext:\n{context_summary}")
])
critic_chain = critic_prompt | fast_llm.with_structured_output(CriticOutput)


class AgenticOrchestrator:
    def __init__(self):
        self.rag = ContextRAG()
        self.memory = ConversationStateManager()
        self.context_store = {"category": {}, "merchant": {}, "customer": {}, "trigger": {}}

    def ingest_context(self, scope, context_id, version, payload):
        self.context_store[scope][context_id] = payload
        if scope == 'category' and 'digest' in payload:
            self.rag.upsert_category_digest(payload.get('slug', context_id), payload['digest'])

    def handle_tick(self, now, available_triggers) -> list:
        actions = []
        for tid in available_triggers:
            trigger = self.context_store["trigger"].get(tid)
            if not trigger: continue
            
            merchant = self.context_store["merchant"].get(trigger.get("merchant_id"))
            if not merchant: continue
            
            category = self.context_store["category"].get(merchant.get("category_slug"))
            if not category: continue
            
            if self.memory.is_suppressed(merchant["merchant_id"]):
                continue
                
            customer = None
            if trigger.get("customer_id"):
                customer = self.context_store["customer"].get(trigger.get("customer_id"))
                
            action_dict = self.compose_message(category, merchant, trigger, customer)
            if action_dict:
                actions.append(action_dict)
                
        return actions

    def compose_message(self, category, merchant, trigger, customer=None, fsm_mode="ENGAGE_NORMAL", reply_conv_id=None, merchant_message=None) -> dict:
        query = f"{trigger.get('kind', '')} {str(trigger.get('payload', ''))}"
        if merchant_message:
            query = merchant_message
        retrieved_fact = self.rag.retrieve(category.get("slug", ""), query)
        
        trigger_framing = TRIGGER_PROMPT_MAP.get(trigger.get("kind"), TRIGGER_PROMPT_MAP["default"])
        if trigger.get("id") == "reply_trigger":
            trigger_framing = f"""You are replying to a merchant's message in an ongoing WhatsApp conversation.
The merchant just said: "{merchant_message}"

CRITICAL RULES FOR REPLIES:
- Answer their SPECIFIC question or acknowledge their SPECIFIC statement.
- If they ask about something out-of-scope (GST, elections, cricket), politely say you can only help with their business on magicpin, then pivot.
- If they ask about competitors, say you don't have that data but highlight THEIR strengths.
- If they ask about pricing/slots, use ONLY data from the provided merchant context.
- Keep it under 40 words. Be natural and conversational.
- Do NOT randomly pitch offers or dump metrics they didn't ask about."""
            
        cat_config = get_category_config(category.get("slug", ""))
        
        best_draft = None
        best_score = -1
        feedback = "None"
        conv_id = reply_conv_id or f"conv_{merchant['merchant_id']}_{trigger['id']}"
        history = self.memory.get_conversation_history(conv_id)
        history_str = "\n".join([f"{msg['role'].upper()}: {msg['message']}" for msg in history]) if history else "No previous history."
        
        for attempt in range(2):
            try:
                draft = actor_chain_fn(
                    trigger_framing, cat_config, merchant, trigger, customer, retrieved_fact, fsm_mode, feedback, history_str
                )
                
                conv_bodies = self.memory._sent_bodies.get(conv_id, [])
                val_result = validate(draft.body, category.get("slug", ""), conv_bodies, fsm_mode)
                
                if not val_result["passed"]:
                    feedback = f"VALIDATION FAILED: {', '.join(val_result['errors'])}"
                    continue
                    
                if fsm_mode == "ENGAGE_NORMAL":
                    # Bypass strict proactive critic for natural conversational replies
                    best_draft = draft
                    self.memory.record_sent_body(conv_id, draft.body)
                    return self._build_bot_action(conv_id, merchant, customer, trigger, draft)
                    
                context_summary = f"Merchant: {merchant.get('identity', {}).get('name')}, Trigger: {trigger.get('kind')}"
                critique = critic_chain.invoke({"draft_body": draft.body, "context_summary": context_summary})
                
                if critique.total_score > best_score:
                    best_draft = draft
                    best_score = critique.total_score
                    
                if critique.passed:
                    self.memory.record_sent_body(conv_id, draft.body)
                    return self._build_bot_action(conv_id, merchant, customer, trigger, draft)
                    
                feedback = critique.actionable_critique
            except Exception as e:
                print(f"Error in compose_message: {e}")
                
        if best_draft:
            self.memory.record_sent_body(conv_id, best_draft.body)
            return self._build_bot_action(conv_id, merchant, customer, trigger, best_draft)
            
        return None
        
    def _build_bot_action(self, conv_id, merchant, customer, trigger, draft):
        return {
            "conversation_id": conv_id,
            "merchant_id": merchant["merchant_id"],
            "customer_id": customer["customer_id"] if customer else None,
            "send_as": draft.send_as,
            "trigger_id": trigger["id"],
            "template_name": None,
            "template_params": None,
            "body": draft.body,
            "cta": draft.cta,
            "suppression_key": draft.suppression_key,
            "rationale": draft.rationale
        }

    def handle_reply(self, conv_id, merchant_id, customer_id, message, turn_number) -> dict:
        self.memory.add_to_history(conv_id, "merchant", message)
        action_decision = self.memory.get_reply_action(conv_id, merchant_id, message, turn_number)
        
        if action_decision["action"] == "end":
            if self.memory.detect_hostile(message):
                self.memory.suppress_merchant(merchant_id, 30)
            return {"action": "end", "rationale": action_decision.get("rationale", "Ending conversation.")}
            
        if action_decision["action"] == "wait":
            return {"action": "wait", "wait_seconds": action_decision.get("wait_seconds", 86400), "rationale": action_decision.get("rationale", "Waiting.")}
            
        mode = action_decision.get("mode", "ENGAGE_NORMAL")
        
        if mode == "AUTO_REPLY_PROBE":
            body = "Samajh gayi — jab owner dekhe, bus YES reply kar dein 😊"
            self.memory.record_sent_body(conv_id, body)
            self.memory.add_to_history(conv_id, "vera", body)
            return {"action": "send", "body": body, "cta": "binary_yes_no", "rationale": "Auto-reply probe"}
            
        if mode == "EXECUTE_ACTION":
            body = "Done! I am drafting the final message now. Reply CONFIRM to proceed."
            self.memory.record_sent_body(conv_id, body)
            self.memory.add_to_history(conv_id, "vera", body)
            return {"action": "send", "body": body, "cta": "binary_confirm_cancel", "rationale": "Action mode engaged."}
            
        merchant = self.context_store["merchant"].get(merchant_id)
        category = self.context_store["category"].get(merchant.get("category_slug")) if merchant else None
        
        if merchant and category:
            # Dynamically compose LLM reply — pass the REAL conv_id and merchant message
            trigger = {"kind": "default", "id": "reply_trigger", "payload": {}}
            action_dict = self.compose_message(category, merchant, trigger, None, fsm_mode=mode, reply_conv_id=conv_id, merchant_message=message)
            if action_dict:
                self.memory.add_to_history(conv_id, "vera", action_dict["body"])
                return {"action": "send", "body": action_dict["body"], "cta": action_dict["cta"], "rationale": action_dict["rationale"]}
                
        # Default fallback if LLM fails or context missing
        fallback_body = "I've noted that down! Is there anything else you'd like to check?"
        self.memory.add_to_history(conv_id, "vera", fallback_body)
        return {"action": "send", "body": fallback_body, "cta": "open_ended", "rationale": "Fallback engaged reply"}
