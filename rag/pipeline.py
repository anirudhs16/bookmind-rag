"""
pipeline.py — Agentic RAG pipeline.

Steps per query:
  1. Query decomposition   — break into 2-3 sub-queries via LLM
  2. Multi-query retrieval — hybrid search for each sub-query, deduplicated
  3. Context assembly      — expand to parent chunks, build context string
  4. Answer generation     — Groq LLM with grounding instructions
  5. Self-reflection       — verify answer; retry once if hallucination detected
  6. Chart generation      — auto-detect if a chart would help; generate data
"""

import os
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from .ingestion import get_embedder, get_qdrant_client, index_pdf
from .retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Configure logging so we can see what's happening in Streamlit Cloud logs
logging.basicConfig(level=logging.INFO)

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are BookMind, an expert financial literacy assistant.
You have access to passages from:
- "Rich Dad Poor Dad" by Robert Kiyosaki
- "The Intelligent Investor" by Benjamin Graham

Answer ONLY from the provided context. Always cite [Book, p.X].
Use **bold** for key terms. If context doesn't cover the question, say so honestly.
"""

DECOMPOSE_PROMPT = """\
Break the following question into 2-3 focused sub-queries for better retrieval.
Return ONLY a valid JSON array of strings, no other text, no markdown fences.
Example: ["sub-query 1", "sub-query 2", "sub-query 3"]

Question: {question}"""

CHART_DETECT_PROMPT = """\
Should the answer to this question include a chart? Consider: comparisons, \
numeric data, timelines, stages, rankings.
Return ONLY valid JSON, no markdown: {{"needs_chart": true, "chart_type": "bar"}}
Chart types: bar, line, horizontal_bar

Question: {question}
Context preview: {context_preview}"""

CHART_DATA_PROMPT = """\
Generate chart data for the answer to this question.
Return ONLY valid JSON, no markdown, no explanation:
{{"type":"bar","title":"Title here","labels":["A","B","C"],"values":[1,2,3]}}
Max 6 data points. Values must be numbers.

Question: {question}
Context: {context}"""

REFLECTION_PROMPT = """\
Does this answer only use facts from the context, or does it hallucinate?
Return ONLY valid JSON, no markdown: {{"grounded": true, "issues": ""}}

Answer: {answer}
Context: {context}"""


class AgenticRAGPipeline:

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable is not set.")
        self.groq      = Groq(api_key=api_key)
        self.embedder  = get_embedder()
        self.db        = get_qdrant_client()
        self.retriever = HybridRetriever(top_k_dense=20, top_k_final=6)
        self.retriever.init(self.embedder, self.db)
        logger.info("AgenticRAGPipeline initialised. Qdrant collections: %s",
                    [c.name for c in self.db.get_collections().collections])

    # ── Document indexing ──────────────────────────────────────────────────
    def index_document(self, pdf_path: str, display_name: str) -> int:
        n = index_pdf(pdf_path, display_name,
                      embedder=self.embedder, client=self.db)
        logger.info("index_document: %d chunks for '%s'", n, display_name)
        return n

    # ── LLM helpers ───────────────────────────────────────────────────────
    def _llm(self, prompt: str, system: str = "",
             max_tokens: int = 1500, temperature: float = 0.2) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self.groq.chat.completions.create(
            model=GROQ_MODEL, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        return resp.choices[0].message.content.strip()

    def _llm_json(self, prompt: str) -> Any:
        raw = self._llm(prompt, max_tokens=400, temperature=0.0)
        raw = re.sub(r"```json\s*|```", "", raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            raise

    # ── Pipeline steps ────────────────────────────────────────────────────
    def _decompose(self, question: str) -> List[str]:
        try:
            sub = self._llm_json(DECOMPOSE_PROMPT.format(question=question))
            if isinstance(sub, list) and sub:
                combined = [question] + [q for q in sub if q != question]
                return combined[:4]
        except Exception as e:
            logger.warning("Decomposition failed (%s), using original query", e)
        return [question]

    def _multi_retrieve(self, queries: List[str]) -> List[Dict]:
        seen, all_chunks = set(), []
        for q in queries:
            for chunk in self.retriever.retrieve(q, client=self.db, top_k=6):
                cid = chunk.get("chunk_id", chunk.get("text", "")[:30])
                if cid not in seen:
                    seen.add(cid)
                    all_chunks.append(chunk)
        logger.info("_multi_retrieve: %d unique chunks from %d queries",
                    len(all_chunks), len(queries))
        return all_chunks[:12]

    def _build_context(self, chunks: List[Dict]) -> Tuple[str, List[str]]:
        parts, sources, seen_parents = [], [], set()
        for c in chunks:
            text = (c.get("parent_text") or c.get("text", "")).strip()
            pid  = c.get("parent_id") or c.get("chunk_id", "")
            if pid in seen_parents or not text:
                continue
            seen_parents.add(pid)
            src   = c.get("source", "Unknown")
            page  = c.get("page", "?")
            parts.append(f"[{src}, p.{page}]\n{text}")
            label = f"{src}, p.{page}"
            if label not in sources:
                sources.append(label)
        return "\n\n---\n\n".join(parts), sources

    def _generate_answer(self, question: str, context: str,
                         history: List[Dict]) -> str:
        hist_str = ""
        if history:
            recent   = history[-4:]
            hist_str = "\n\nRecent conversation:\n" + "\n".join(
                f"{'User' if m['role']=='user' else 'Assistant'}: {m['content'][:250]}"
                for m in recent
            )
        prompt = (
            f"Answer using ONLY the context below.{hist_str}\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Rules: cite [Book, p.X], use **bold** for key terms, be thorough but concise."
        )
        return self._llm(prompt, system=SYSTEM_PROMPT, max_tokens=1200, temperature=0.3)

    def _reflect(self, answer: str, context: str) -> Dict:
        try:
            return self._llm_json(REFLECTION_PROMPT.format(
                answer=answer[:1500], context=context[:2000]
            ))
        except Exception as e:
            logger.warning("Reflection failed: %s", e)
            return {"grounded": True, "issues": ""}

    def _chart_check(self, question: str, context: str) -> Dict:
        kw = ["compare","vs","versus","difference","percent","return","growth",
              "increase","decrease","timeline","years","phases","stages",
              "quadrant","how much","how many","rate","ratio","performance","ranking"]
        if not any(k in question.lower() for k in kw):
            return {"needs_chart": False}
        try:
            return self._llm_json(CHART_DETECT_PROMPT.format(
                question=question, context_preview=context[:600]
            ))
        except Exception:
            return {"needs_chart": False}

    def _chart_data(self, question: str, context: str, ctype: str) -> Optional[Dict]:
        try:
            data = self._llm_json(CHART_DATA_PROMPT.format(
                question=question, context=context[:1500]
            ))
            if isinstance(data, dict) and len(data.get("labels", [])) >= 2:
                return data
        except Exception as e:
            logger.warning("Chart data generation failed: %s", e)
        return None

    # ── Main entry point ──────────────────────────────────────────────────
    def query(self, question: str,
              chat_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        chat_history = chat_history or []
        logger.info("query() called: %r", question[:80])

        # 1. Decompose
        sub_queries = self._decompose(question)
        logger.info("Sub-queries: %s", sub_queries)

        # 2. Retrieve
        chunks = self._multi_retrieve(sub_queries)
        if not chunks:
            logger.warning("No chunks retrieved for question: %r", question)
            return {
                "answer": (
                    "I couldn't find relevant passages in your indexed documents.\n\n"
                    "**Possible reasons:**\n"
                    "- The PDF may not have been indexed yet — try clicking 'Index documents' again\n"
                    "- The PDF might be image-based (scanned) with no extractable text\n"
                    "- Try rephrasing your question with different keywords"
                ),
                "sources": [],
                "chart_data": None,
            }

        # 3. Build context
        context, sources = self._build_context(chunks)
        logger.info("Context built: %d chars, %d sources", len(context), len(sources))

        # 4. Generate answer
        answer = self._generate_answer(question, context, chat_history)

        # 5. Self-reflect (one retry if hallucination detected)
        reflection = self._reflect(answer, context)
        if not reflection.get("grounded", True) and reflection.get("issues"):
            logger.info("Reflection flagged issues: %s — retrying", reflection["issues"])
            answer = self._generate_answer(question, context, chat_history)

        # 6. Chart
        chart_data = None
        cc = self._chart_check(question, context)
        if cc.get("needs_chart"):
            chart_data = self._chart_data(question, context, cc.get("chart_type", "bar"))

        return {"answer": answer, "sources": sources, "chart_data": chart_data}
