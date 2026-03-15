"""
db.py — Qdrant collection introspection and management utilities.
"""
import logging
from typing import List, Dict
from qdrant_client import QdrantClient
from .ingestion import COLLECTION_NAME

logger = logging.getLogger(__name__)


def get_indexed_sources(client: QdrantClient) -> List[Dict]:
    """
    Return list of {source, count} dicts for every unique source
    already stored in the collection. Empty list if collection missing.
    """
    try:
        existing = {c.name for c in client.get_collections().collections}
        if COLLECTION_NAME not in existing:
            return []

        # Scroll through all points and collect unique sources + counts
        source_counts: Dict[str, int] = {}
        offset = None
        while True:
            result, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=500,
                offset=offset,
                with_payload=["source"],
                with_vectors=False,
            )
            for point in result:
                src = (point.payload or {}).get("source", "Unknown")
                source_counts[src] = source_counts.get(src, 0) + 1
            if next_offset is None:
                break
            offset = next_offset

        return [{"source": k, "count": v} for k, v in sorted(source_counts.items())]

    except Exception as e:
        logger.error("get_indexed_sources error: %s", e)
        return []


def delete_source(client: QdrantClient, source_name: str) -> int:
    """
    Delete all points belonging to a specific source (book).
    Returns number of points deleted.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    try:
        # Count first
        before = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(must=[
                FieldCondition(key="source", match=MatchValue(value=source_name))
            ]),
            exact=True,
        ).count

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=[
                FieldCondition(key="source", match=MatchValue(value=source_name))
            ]),
        )
        logger.info("Deleted %d points for source '%s'", before, source_name)
        return before
    except Exception as e:
        logger.error("delete_source error: %s", e)
        return 0


def delete_all(client: QdrantClient) -> bool:
    """Drop and recreate the entire collection."""
    from .ingestion import ensure_collection, EMBED_DIM
    from qdrant_client.models import VectorParams, Distance
    try:
        existing = {c.name for c in client.get_collections().collections}
        if COLLECTION_NAME in existing:
            client.delete_collection(COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        logger.info("Collection reset: %s", COLLECTION_NAME)
        return True
    except Exception as e:
        logger.error("delete_all error: %s", e)
        return False


def total_points(client: QdrantClient) -> int:
    try:
        existing = {c.name for c in client.get_collections().collections}
        if COLLECTION_NAME not in existing:
            return 0
        return client.count(collection_name=COLLECTION_NAME, exact=True).count
    except Exception:
        return 0
