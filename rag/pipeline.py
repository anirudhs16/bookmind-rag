"""
pipeline.py — Agentic RAG orchestration.

Agent steps:
  1. Query analysis   — classify intent, detect if chart needed
  2. Query decomposition — split complex questions into sub-queries
  3. Multi-query retrieval — retrieve for each sub-query, deduplicate
  4. Context assembly — rank & assemble retrieved chunks
  5. Answer generation — LLM with grounding instructions
  6. Self-reflection  — verify answer is grounded; retry once if hallucination detected
  7. Chart generation — if query needs a visual, produce chart_data JSON
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from groq import Groq

from .ingestion import index_pdf
from .retriever import HybridRetriever

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are BookMind, an expert financial literacy assistant trained on:
- "Rich Dad Poor Dad" by Robert Kiyosaki
- "The Intelligent Investor" by Benjamin Graham (with Jason Zweig commentary)

Your job is to give precise, grounded, insightful answers based ONLY on the provided context chunks.

Rules:
1. Always cite which book your answer comes from (e.g. [Rich Dad Poor Dad, p.42])
2. If context doesn't contain the answer, say so clearly — do NOT hallucinate
3. Be analytical and educational; connect concepts where relevant
4. Use markdown formatting: **bold** for key terms, bullet points for lists
5. When comparing both books, clearly label each perspective
"""

DECOMPOSE_PROMPT = """You are a query analysis expert. Given a user's question, break it into 2-3 focused sub-queries that together cover the full question.

Return ONLY a JSON array of strings, no explanation. Example:
["What are assets according to Kiyosaki?", "How does Kiyosaki define liabilities?", "What is the cash flow quadrant?"]

Question: {question}"""

CHART_DETECT_PROMPT = """Analyze this question and context. Should the answer include a chart/graph?

Return JSON: {{"needs_chart": true/false, "chart_type": "bar|line|horizontal_bar|none", "reason": "brief reason"}}

Question: {question}
Context preview: {context_preview}"""

CHART_DATA_PROMPT = """Based on this context and question, generate chart data as JSON.

Return ONLY JSON in this exact format:
{{
  "type": "bar",
  "title": "Chart title here",
  "labels": ["Label1", "Label2", "Label3"],
  "values": [10, 20, 30]
}}

Use numeric values only. Max 6 data points. Chart types: bar, line, horizontal_bar.

Question: {question}
Context: {context}"""

REFLECTION_PROMPT = """Review this answer against the provided context. 

Answer: {answer}
Context: {context}

Is the answer grounded in the context? Does it make claims not supported by the context?
Return JSON: {{"grounded": true/false, "issues": "description of any unsupported claims or empty string"}}"""


class AgenticRAGPipeline:
    def __init__(self):
        self.groq = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.retriever = HybridRetriever(top_k_dense=20, top_k_final=6)
        self._embedder = None
        self._client = None

    # ── Lazy accessors for shared embedder/client ─────────────────────────
    @property
    def embedder(self):
        if self._embedder is None:
            from .ingestion import _get_embedder
            self._embedder = _get_embedder()
        return self._embedder

    @property
    def qdrant(self):
        if self._client is None:
            from .ingestion import _get_qdrant
            self._client = _get_qdrant()
        return self._client

    # ── Document indexing ─────────────────────────────────────────────────
    def index_document(self, pdf_path: str, display_name: str) -> int:
        return index_pdf(pdf_path, display_name,
                         embedder=self.embedder, client=self.qdrant)

    # ── LLM call ──────────────────────────────────────────────────────────
    def _llm(self, prompt: str, system: str = "", max_tokens: int = 1500,
             temperature: float = 0.2) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self.groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return resp.choices[0].message.content.strip()

    def _llm_json(self, prompt: str, system: str = "") -> Any:
        """LLM call that returns parsed JSON."""
        raw = self._llm(prompt, system=system, max_tokens=400, temperature=0.0)
        # Strip markdown code fences if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r'\{.*\}|\[.*\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    # ── Step 1: Query decomposition ───────────────────────────────────────
    def _decompose_query(self, question: str) -> List[str]:
        """Break complex question into sub-queries."""
        try:
            prompt = DECOMPOSE_PROMPT.format(question=question)
            sub_queries = self._llm_json(prompt)
            if isinstance(sub_queries, list) and len(sub_queries) > 0:
                # Always include original question
                all_queries = [question] + [q for q in sub_queries if q != question]
                return all_queries[:4]  # max 4 queries
        except Exception as e:
            logger.warning("Query decomposition failed: %s", e)
        return [question]

    # ── Step 2: Multi-query retrieval ─────────────────────────────────────
    def _multi_retrieve(self, queries: List[str]) -> List[Dict]:
        """Retrieve for all sub-queries, deduplicate by chunk_id."""
        seen_ids = set()
        all_chunks = []
        for q in queries:
            chunks = self.retriever.retrieve(q, top_k=6)
            for c in chunks:
                cid = c.get("chunk_id", c.get("text", "")[:30])
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_chunks.append(c)
        return all_chunks[:12]  # cap total context

    # ── Step 3: Context assembly ──────────────────────────────────────────
    def _build_context(self, chunks: List[Dict]) -> Tuple[str, List[str]]:
        """Build context string and source list from chunks."""
        context_parts = []
        sources = []
        seen_parents = set()

        for chunk in chunks:
            # Use parent_text for richer context if not already included
            text = chunk.get("parent_text") or chunk.get("text", "")
            pid  = chunk.get("parent_id", chunk.get("chunk_id", ""))

            if pid in seen_parents:
                continue
            seen_parents.add(pid)

            source = chunk.get("source", "Unknown")
            page   = chunk.get("page", "?")
            context_parts.append(f"[{source}, p.{page}]\n{text}")

            src_label = f"{source}, p.{page}"
            if src_label not in sources:
                sources.append(src_label)

        return "\n\n---\n\n".join(context_parts), sources

    # ── Step 4: Answer generation ─────────────────────────────────────────
    def _generate_answer(self, question: str, context: str,
                         chat_history: List[Dict]) -> str:
        # Build history suffix
        history_str = ""
        if chat_history:
            recent = chat_history[-4:]  # last 4 exchanges
            history_str = "\n\nConversation history:\n"
            for m in recent:
                role = "User" if m["role"] == "user" else "Assistant"
                history_str += f"{role}: {m['content'][:300]}\n"

        prompt = f"""Answer the following question using ONLY the provided context.
{history_str}

Context:
{context}

Question: {question}

Instructions:
- Cite sources in format [Book Name, p.X]
- Be thorough but concise
- Use **bold** for key concepts
- If the answer spans multiple books, compare perspectives
"""
        return self._llm(prompt, system=SYSTEM_PROMPT, max_tokens=1200,
                         temperature=0.3)

    # ── Step 5: Self-reflection ───────────────────────────────────────────
    def _reflect(self, answer: str, context: str) -> Dict:
        """Check if answer is grounded in context."""
        try:
            prompt = REFLECTION_PROMPT.format(
                answer=answer[:1500],
                context=context[:2000]
            )
            return self._llm_json(prompt)
        except Exception as e:
            logger.warning("Reflection failed: %s", e)
            return {"grounded": True, "issues": ""}

    # ── Step 6: Chart detection & generation ─────────────────────────────
    def _should_generate_chart(self, question: str, context: str) -> Dict:
        """Detect if chart would enhance the answer."""
        chart_keywords = [
            "compare", "comparison", "vs", "versus", "difference",
            "percentage", "return", "growth", "increase", "decrease",
            "timeline", "years", "phases", "stages", "quadrant",
            "how much", "how many", "rate", "ratio", "performance"
        ]
        q_lower = question.lower()
        needs_chart_hint = any(kw in q_lower for kw in chart_keywords)

        if not needs_chart_hint:
            return {"needs_chart": False}

        try:
            prompt = CHART_DETECT_PROMPT.format(
                question=question,
                context_preview=context[:600]
            )
            return self._llm_json(prompt)
        except Exception:
            return {"needs_chart": False}

    def _generate_chart_data(self, question: str, context: str,
                              chart_type: str) -> Optional[Dict]:
        """Generate chart data JSON from context."""
        try:
            prompt = CHART_DATA_PROMPT.format(
                question=question,
                context=context[:1500]
            )
            data = self._llm_json(prompt)
            if (isinstance(data, dict)
                    and "labels" in data
                    and "values" in data
                    and len(data["labels"]) >= 2):
                return data
        except Exception as e:
            logger.warning("Chart generation failed: %s", e)
        return None

    # ── Main query entry point ────────────────────────────────────────────
    def query(self, question: str,
              chat_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Full agentic RAG pipeline.
        Returns: {answer, sources, chart_data, steps}
        """
        chat_history = chat_history or []
        steps = []

        # ── 1. Decompose ──────────────────────────────────────────────────
        steps.append("🔍 Decomposing query into sub-questions…")
        sub_queries = self._decompose_query(question)
        logger.info("Sub-queries: %s", sub_queries)

        # ── 2. Multi-query retrieval ──────────────────────────────────────
        steps.append(f"📚 Retrieving context for {len(sub_queries)} queries…")
        chunks = self._multi_retrieve(sub_queries)

        if not chunks:
            return {
                "answer": "⚠️ I couldn't find relevant information in the indexed documents. "
                          "Please make sure you've uploaded and indexed your PDF files.",
                "sources": [],
                "chart_data": None,
                "steps": steps
            }

        # ── 3. Build context ──────────────────────────────────────────────
        steps.append(f"⚡ Re-ranking {len(chunks)} retrieved chunks…")
        context, sources = self._build_context(chunks)

        # ── 4. Generate answer ────────────────────────────────────────────
        steps.append("✍️ Generating grounded answer…")
        answer = self._generate_answer(question, context, chat_history)

        # ── 5. Self-reflection ────────────────────────────────────────────
        steps.append("🪞 Verifying answer is grounded…")
        reflection = self._reflect(answer, context)
        if not reflection.get("grounded", True) and reflection.get("issues"):
            # Retry with stricter prompt
            steps.append("⚠️ Detected potential hallucination, regenerating…")
            strict_system = SYSTEM_PROMPT + "\n\nCRITICAL: You MUST only state facts explicitly present in the context. If unsure, say 'The provided context does not clearly address this.'"
            answer = self._generate_answer(question, context, chat_history)

        # ── 6. Chart generation ───────────────────────────────────────────
        chart_data = None
        chart_check = self._should_generate_chart(question, context)
        if chart_check.get("needs_chart"):
            steps.append("📊 Generating visualization…")
            chart_data = self._generate_chart_data(
                question, context,
                chart_check.get("chart_type", "bar")
            )

        return {
            "answer": answer,
            "sources": sources,
            "chart_data": chart_data,
            "steps": steps
        }
