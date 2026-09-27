"""
config.py — Central configuration for the Vera bot.

Loads environment variables, initialises LLM and embedding instances,
and exposes a BOT_CONFIG metadata dict used by the /meta endpoint.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()  # reads .env in project root (or wherever the process starts)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# LLM instances
# ---------------------------------------------------------------------------

# Primary "actor" model — used for drafting messages, reasoning, critic, etc.
actor_llm = ChatOpenAI(
    model=os.getenv("ACTOR_MODEL", "gpt-4o"),
    temperature=0.3,
    api_key=OPENAI_API_KEY,
)

# Lightweight / fast model — used for intent classification and quick checks.
fast_llm = ChatOpenAI(
    model=os.getenv("FAST_MODEL", "gpt-4o-mini"),
    temperature=0.0,
    api_key=OPENAI_API_KEY,
)

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY,
)

# ---------------------------------------------------------------------------
# Bot metadata (returned by /meta and used in logging)
# ---------------------------------------------------------------------------

BOT_CONFIG: dict = {
    "team_name": "Vera",
    "model": os.getenv("ACTOR_MODEL", "gpt-4o"),
    "fast_model": os.getenv("FAST_MODEL", "gpt-4o-mini"),
    "embedding_model": "text-embedding-3-small",
    "approach": (
        "LangChain actor-critic pipeline with FAISS retrieval, "
        "category-aware tone control, and structured output parsing."
    ),
    "version": "1.0.0",
}
