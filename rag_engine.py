"""
rag_engine.py – Lightweight per-category RAG backed by FAISS + OpenAI embeddings.

Each category slug owns an independent FAISS index.  Digest items are
formatted into enriched text chunks with structured metadata and
upserted atomically (full rebuild per category to avoid stale data).
"""

from typing import Any, Dict, List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


class ContextRAG:
    """Manage per-category FAISS indices for digest-based retrieval."""

    def __init__(self) -> None:
        self._embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # category_slug -> FAISS index
        self._indices: Dict[str, FAISS] = {}

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------
    def upsert_category_digest(
        self,
        slug: str,
        digest_items: List[Dict[str, Any]],
    ) -> None:
        """Atomically (re)build the FAISS index for *slug*.

        Parameters
        ----------
        slug:
            Category identifier (e.g. ``"restaurant"``).
        digest_items:
            List of dicts, each expected to carry some subset of:
            ``Category``, ``Kind``, ``Title``, ``Source``, ``Data``.
        """
        if not digest_items:
            # Nothing to index – remove stale index if present
            self._indices.pop(slug, None)
            return

        documents: List[Document] = []
        for item in digest_items:
            # Build an enriched textual chunk for embedding
            parts: List[str] = []
            if item.get("Category"):
                parts.append(f"Category: {item['Category']}")
            if item.get("Kind"):
                parts.append(f"Kind: {item['Kind']}")
            if item.get("Title"):
                parts.append(f"Title: {item['Title']}")
            if item.get("Source"):
                parts.append(f"Source: {item['Source']}")
            if item.get("Data"):
                parts.append(f"Data: {item['Data']}")

            page_content: str = "\n".join(parts) if parts else str(item)

            documents.append(
                Document(page_content=page_content, metadata=item)
            )

        # Atomic rebuild – old index for this slug is fully replaced
        self._indices[slug] = FAISS.from_documents(documents, self._embeddings)

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------
    def retrieve(
        self,
        slug: str,
        query: str,
        top_k: int = 2,
    ) -> List[Dict[str, Any]]:
        """Return the top-*k* metadata dicts most similar to *query*.

        If the category index does not exist or is empty, an empty list
        is returned gracefully (no exception).
        """
        index = self._indices.get(slug)
        if index is None:
            return []

        results: List[Document] = index.similarity_search(query, k=top_k)
        return [doc.metadata for doc in results]
