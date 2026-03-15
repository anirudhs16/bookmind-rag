"""
ingestion.py — PDF loading, chunking, embedding, and Qdrant indexing.
"""
import os
import hashlib
import logging
from typing import List

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

COLLECTION_NAME = "bookmind_docs"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM       = 384

PARENT_CHUNK  = 800
CHILD_CHUNK   = 200
CHUNK_OVERLAP = 40


def get_embedder() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_qdrant_client() -> QdrantClient:
    url     = os.getenv("QDRANT_URL", "").strip()
    api_key = os.getenv("QDRANT_API_KEY", "").strip()
    if url:
        logger.info("Connecting to Qdrant Cloud: %s", url)
        return QdrantClient(url=url, api_key=api_key or None)
    logger.warning("QDRANT_URL not set — using in-memory Qdrant (data lost on restart)")
    return QdrantClient(":memory:")


def ensure_collection(client: QdrantClient):
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        logger.info("Created collection: %s", COLLECTION_NAME)
    else:
        logger.info("Collection already exists: %s", COLLECTION_NAME)


def _chunk_id(text: str, source: str, idx: int) -> str:
    h = hashlib.md5(f"{source}:{idx}:{text[:60]}".encode()).hexdigest()[:12]
    return h


def index_pdf(
    pdf_path: str,
    display_name: str,
    embedder: HuggingFaceEmbeddings = None,
    client: QdrantClient = None,
) -> int:
    embedder = embedder or get_embedder()
    client   = client   or get_qdrant_client()
    ensure_collection(client)

    loader   = PyMuPDFLoader(pdf_path)
    raw_docs = loader.load()
    logger.info("Loaded %d pages from '%s'", len(raw_docs), display_name)

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    parent_docs = parent_splitter.split_documents(raw_docs)
    points: List[PointStruct] = []
    global_idx = 0

    for p_idx, parent in enumerate(parent_docs):
        parent_text = parent.page_content.strip()
        if not parent_text:
            continue
        parent_id = _chunk_id(parent_text, display_name, p_idx)
        children  = child_splitter.split_text(parent_text)

        for child_text in children:
            child_text = child_text.strip()
            if len(child_text) < 30:
                continue

            cid = _chunk_id(child_text, display_name, global_idx)
            # Deterministic integer ID from hash
            point_id = int(hashlib.md5(cid.encode()).hexdigest()[:15], 16)

            payload = {
                "text":        child_text,
                "parent_text": parent_text,
                "source":      display_name,
                "page":        int(parent.metadata.get("page", 0)) + 1,
                "parent_id":   parent_id,
                "chunk_id":    cid,
            }
            vec = embedder.embed_query(child_text)
            points.append(PointStruct(id=point_id, vector=vec, payload=payload))
            global_idx += 1

    # Upsert in batches of 64
    batch = 64
    for i in range(0, len(points), batch):
        client.upsert(collection_name=COLLECTION_NAME, points=points[i:i+batch])
        logger.info("Upserted batch %d/%d", i//batch + 1, (len(points)-1)//batch + 1)

    logger.info("Indexed %d child chunks for '%s'", len(points), display_name)
    return len(points)
