"""
ingestion.py — PDF loading, chunking, embedding, and Qdrant indexing.

Strategy:
  - Hierarchical chunking: large parent chunks (800 tokens) + small child chunks
    (200 tokens) — parent stored for context, child used for retrieval
  - Overlap: 50 tokens to preserve context across chunk boundaries
  - Each chunk stores metadata: source file, page number, chunk_id, parent_id
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "bookmind_docs"
EMBEDDING_MODEL  = "BAAI/bge-small-en-v1.5"   # 384-dim, fast & accurate
EMBED_DIM        = 384

# Chunk sizes
PARENT_CHUNK     = 900
CHILD_CHUNK      = 250
CHUNK_OVERLAP    = 50


def _get_embedder():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


def _get_qdrant() -> QdrantClient:
    url    = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY", "")
    if url:
        return QdrantClient(url=url, api_key=api_key or None)
    # Local fallback (in-memory for quick testing)
    return QdrantClient(":memory:")


def _ensure_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE)
        )
        logger.info("Created Qdrant collection: %s", COLLECTION_NAME)


def _chunk_id(text: str, source: str, idx: int) -> str:
    h = hashlib.md5(f"{source}:{idx}:{text[:50]}".encode()).hexdigest()[:10]
    return h


def index_pdf(pdf_path: str, display_name: str,
              embedder=None, client=None) -> int:
    """
    Load a PDF, create hierarchical chunks, embed, and upsert into Qdrant.
    Returns number of child chunks indexed.
    """
    embedder = embedder or _get_embedder()
    client   = client   or _get_qdrant()
    _ensure_collection(client)

    # ── Load ──────────────────────────────────────────────────────────────
    loader = PyMuPDFLoader(pdf_path)
    raw_docs = loader.load()
    logger.info("Loaded %d pages from %s", len(raw_docs), display_name)

    # ── Parent splitter (context store) ───────────────────────────────────
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    parent_docs = parent_splitter.split_documents(raw_docs)

    # ── Child splitter (retrieval targets) ────────────────────────────────
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    points: List[PointStruct] = []
    global_idx = 0

    for p_idx, parent in enumerate(parent_docs):
        parent_id = _chunk_id(parent.page_content, display_name, p_idx)
        children  = child_splitter.split_text(parent.page_content)

        for c_idx, child_text in enumerate(children):
            if len(child_text.strip()) < 30:
                continue

            cid = _chunk_id(child_text, display_name, global_idx)
            payload = {
                "text":        child_text,
                "parent_text": parent.page_content,   # full context for LLM
                "source":      display_name,
                "page":        parent.metadata.get("page", 0) + 1,
                "parent_id":   parent_id,
                "chunk_id":    cid,
            }
            points.append(PointStruct(
                id=abs(int(hashlib.md5(cid.encode()).hexdigest(), 16)) % (2**63),
                vector=embedder.embed_query(child_text),
                payload=payload
            ))
            global_idx += 1

    # ── Upsert in batches ─────────────────────────────────────────────────
    batch_size = 64
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=COLLECTION_NAME,
                      points=points[i:i+batch_size])

    logger.info("Indexed %d child chunks for '%s'", len(points), display_name)
    return len(points)
