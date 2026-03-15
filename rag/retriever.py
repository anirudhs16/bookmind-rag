"""
retriever.py — Hybrid search (dense + BM25-style keyword) + cross-encoder re-ranking.

Flow:
  1. Dense semantic search via Qdrant cosine similarity
  2. Keyword search via BM25 over retrieved texts (lightweight, no extra infra)
  3. Reciprocal Rank Fusion to merge both result lists
  4. Cross-encoder re-ranking (ms-marco-MiniLM) for final top-k
"""

import os
import math
import logging
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from .ingestion import _get_embedder, _get_qdrant, COLLECTION_NAME, EMBED_DIM

logger = logging.getLogger(__name__)

# ── BM25 helpers ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    import re
    return re.findall(r'\b\w+\b', text.lower())


def _bm25_score(query_tokens: List[str], doc_tokens: List[str],
                avgdl: float, k1=1.5, b=0.75) -> float:
    from collections import Counter
    tf = Counter(doc_tokens)
    n  = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        f = tf.get(qt, 0)
        if f == 0:
            continue
        score += (f * (k1 + 1)) / (f + k1 * (1 - b + b * n / max(avgdl, 1)))
    return score


def _reciprocal_rank_fusion(rankings: List[List[str]], k=60) -> List[str]:
    """Fuse multiple ranked lists using RRF."""
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda x: scores[x], reverse=True)


# ── Cross-encoder re-ranker ───────────────────────────────────────────────────

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


# ── Main retriever ────────────────────────────────────────────────────────────

class HybridRetriever:
    def __init__(self, top_k_dense=15, top_k_final=6):
        self.top_k_dense = top_k_dense
        self.top_k_final = top_k_final
        self._embedder = None
        self._client   = None

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = _get_embedder()
        return self._embedder

    @property
    def client(self):
        if self._client is None:
            self._client = _get_qdrant()
        return self._client

    def retrieve(self, query: str,
                 source_filter: Optional[str] = None,
                 top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Returns top-k re-ranked chunks with metadata.
        Each chunk has: text, parent_text, source, page, score
        """
        top_k = top_k or self.top_k_final

        # ── 1. Dense search ──────────────────────────────────────────────
        qvec = self.embedder.embed_query(query)
        qfilter = None
        if source_filter:
            qfilter = Filter(must=[
                FieldCondition(key="source",
                               match=MatchValue(value=source_filter))
            ])

        try:
            hits = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=qvec,
                limit=self.top_k_dense,
                query_filter=qfilter,
                with_payload=True
            )
        except Exception as e:
            logger.error("Qdrant search error: %s", e)
            return []

        if not hits:
            return []

        docs = [h.payload for h in hits]
        dense_ids = [d["chunk_id"] for d in docs]

        # ── 2. BM25 re-score on retrieved pool ───────────────────────────
        query_tokens = _tokenize(query)
        doc_tokens_list = [_tokenize(d["text"]) for d in docs]
        avgdl = sum(len(t) for t in doc_tokens_list) / max(len(doc_tokens_list), 1)

        bm25_scores = {
            d["chunk_id"]: _bm25_score(query_tokens, doc_tokens_list[i], avgdl)
            for i, d in enumerate(docs)
        }
        bm25_ranked = sorted(bm25_scores, key=lambda x: bm25_scores[x], reverse=True)

        # ── 3. RRF fusion ─────────────────────────────────────────────────
        fused_ids = _reciprocal_rank_fusion([dense_ids, bm25_ranked])
        doc_map = {d["chunk_id"]: d for d in docs}
        fused_docs = [doc_map[cid] for cid in fused_ids if cid in doc_map]

        # ── 4. Cross-encoder re-ranking ───────────────────────────────────
        if len(fused_docs) > 1:
            try:
                reranker = _get_reranker()
                pairs = [(query, d["text"]) for d in fused_docs]
                ce_scores = reranker.predict(pairs)
                scored = sorted(zip(ce_scores, fused_docs),
                                key=lambda x: x[0], reverse=True)
                fused_docs = [d for _, d in scored]
            except Exception as e:
                logger.warning("Cross-encoder failed, using RRF order: %s", e)

        return fused_docs[:top_k]
