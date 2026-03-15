"""
retriever.py — Hybrid search (dense semantic + BM25 keyword) + cross-encoder re-ranking.

Uses qdrant_client.query_points() — the current API for qdrant-client >= 1.7.
"""
import re
import logging
from collections import Counter
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from .ingestion import get_embedder, COLLECTION_NAME

logger = logging.getLogger(__name__)

# ── BM25 ──────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())


def _bm25_score(query_tokens, doc_tokens, avgdl, k1=1.5, b=0.75) -> float:
    tf = Counter(doc_tokens)
    n  = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        f = tf.get(qt, 0)
        if f:
            score += (f * (k1 + 1)) / (f + k1 * (1 - b + b * n / max(avgdl, 1)))
    return score


def _rrf(rankings: List[List[str]], k=60) -> List[str]:
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda x: scores[x], reverse=True)


# ── Cross-encoder ─────────────────────────────────────────────────────────────

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


# ── Retriever class ───────────────────────────────────────────────────────────

class HybridRetriever:
    def __init__(self, top_k_dense: int = 20, top_k_final: int = 6):
        self.top_k_dense = top_k_dense
        self.top_k_final = top_k_final
        self._embedder   = None
        self._client     = None

    def init(self, embedder, client: QdrantClient):
        """Share the embedder and client created by the pipeline."""
        self._embedder = embedder
        self._client   = client

    def _embed(self, text: str) -> List[float]:
        if self._embedder is None:
            self._embedder = get_embedder()
        return self._embedder.embed_query(text)

    def retrieve(
        self,
        query: str,
        client: QdrantClient = None,
        source_filter: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        top_k  = top_k or self.top_k_final
        client = client or self._client
        if client is None:
            raise RuntimeError("HybridRetriever has no QdrantClient. Call init() first.")

        qvec    = self._embed(query)
        qfilter = None
        if source_filter:
            qfilter = Filter(must=[FieldCondition(
                key="source", match=MatchValue(value=source_filter)
            )])

        # ── Dense search using query_points (qdrant-client >= 1.7) ──────────
        try:
            result = client.query_points(
                collection_name=COLLECTION_NAME,
                query=qvec,
                limit=self.top_k_dense,
                query_filter=qfilter,
                with_payload=True,
            )
            hits = result.points
        except Exception as e:
            logger.error("Qdrant query_points error: %s", e)
            # Fallback: try legacy .search() in case of older server
            try:
                hits = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=qvec,
                    limit=self.top_k_dense,
                    query_filter=qfilter,
                    with_payload=True,
                )
            except Exception as e2:
                logger.error("Qdrant .search() fallback also failed: %s", e2)
                return []

        if not hits:
            logger.warning("Dense search returned 0 results for query: %r", query)
            return []

        docs       = [h.payload for h in hits if h.payload]
        dense_ids  = [d.get("chunk_id", str(i)) for i, d in enumerate(docs)]

        # ── BM25 re-score on retrieved pool ───────────────────────────────────
        qtokens       = _tokenize(query)
        doc_tok_lists = [_tokenize(d.get("text", "")) for d in docs]
        avgdl         = sum(len(t) for t in doc_tok_lists) / max(len(doc_tok_lists), 1)

        bm25_scores = {
            dense_ids[i]: _bm25_score(qtokens, doc_tok_lists[i], avgdl)
            for i in range(len(docs))
        }
        bm25_ranked = sorted(bm25_scores, key=lambda x: bm25_scores[x], reverse=True)

        # ── RRF fusion ────────────────────────────────────────────────────────
        fused_ids  = _rrf([dense_ids, bm25_ranked])
        id_to_doc  = {dense_ids[i]: docs[i] for i in range(len(docs))}
        fused_docs = [id_to_doc[cid] for cid in fused_ids if cid in id_to_doc]

        # ── Cross-encoder re-ranking ──────────────────────────────────────────
        if len(fused_docs) > 1:
            try:
                reranker = _get_reranker()
                pairs    = [(query, d.get("text", "")) for d in fused_docs]
                ce_scores = reranker.predict(pairs)
                fused_docs = [d for _, d in sorted(
                    zip(ce_scores, fused_docs), key=lambda x: x[0], reverse=True
                )]
            except Exception as e:
                logger.warning("Cross-encoder failed, using RRF order: %s", e)

        logger.info("retrieve() returning %d docs for query %r", len(fused_docs[:top_k]), query[:60])
        return fused_docs[:top_k]
