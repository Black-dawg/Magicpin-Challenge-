# Vera Bot — magicpin AI Challenge Submission

## 🧠 Architecture Overview (Version 3.0)

This bot is engineered with a **Two-Tier "Actor-Critic" Architecture** and a deterministic **State Machine (FSM)**. It is built entirely in pure LangChain (LCEL) and FastAPI, strictly optimizing for the 5-dimension judge rubric while eliminating hallucinations and Meta policy violations.

### 1. Deterministic Tier-1 Validator (`validators.py`)
LLMs hallucinate, and in this challenge, hallucinating a URL is a **-3 penalty** and using platform jargon is a **-1 penalty**. 
Before the LLM Critic even sees the draft, our `validators.py` runs a lightning-fast regex check. If it finds a URL, jargon, or a taboo word (like "guaranteed cure"), it instantly rejects the draft. 

### 2. Actor-Critic Self-Correction (`chains.py`)
*   **The Actor (`gpt-4o`)**: Drafts the initial outbound pitch using trigger-specific templates. It is forced via the system prompt to use Hinglish, maintain category voice, and pull 3 verifiable numbers from context.
*   **The Critic (`gpt-4o-mini`)**: Instantly grades the draft against the exact 5 dimensions the judge uses (Specificity, Category Fit, Merchant Fit, etc.). If the draft scores below 42/50, the Critic forces a rewrite.
*   **Conversational Bypass**: If the merchant replies with a natural question, the strict Critic and proactive constraints are bypassed, allowing the Actor to converse naturally.

### 3. FSM State Manager (`memory.py`)
To handle the most difficult edge cases perfectly:
*   **Auto-Reply Handling**: MD5 hashes the merchant's message to detect canned responses. Strikes 1 (probes), Strike 2 (waits 24h), Strike 3 (ends conversation).
*   **Hostile Exit**: Immediately detects "stop", "spam", etc., returns an `end` command, and suppresses the merchant for 30 days.
*   **Intent Transition**: Intercepts commitment phrases ("lets do it", "kar do") and deterministically transitions to Action Mode without confusing the LLM.

### 4. Category-Partitioned RAG (`rag_engine.py`)
Category digests are embedded using `text-embedding-3-small` and stored in isolated FAISS vector indices per category. This completely eliminates the risk of cross-category contamination (e.g., suggesting a restaurant discount to a pharmacy).

## 🚀 How to Run

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Add your keys**:
    Create a `.env` file in this directory:
    ```
    OPENAI_API_KEY=your_key_here
    ACTOR_MODEL=gpt-4o
    FAST_MODEL=gpt-4o-mini
    ```

3.  **Start the server**:
    ```bash
    python main.py
    ```

4.  **Run the Judge**:
    In a separate terminal, run the `judge_simulator.py` script provided in the challenge dataset.
