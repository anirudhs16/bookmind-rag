# 📚 BookMind — Agentic RAG Chatbot

A production-grade RAG chatbot for **Rich Dad Poor Dad** and **The Intelligent Investor** (or any PDFs you upload), powered by:

- **Groq** (LLaMA 3.3 70B) — fast LLM inference
- **BAAI/bge-small-en-v1.5** — free local embeddings (no extra API key)
- **Qdrant Cloud** — persistent hybrid vector search
- **Agentic RAG pipeline** — query decomposition → hybrid retrieval → cross-encoder re-ranking → self-reflection
- **Streamlit** — simple, shareable UI with chat history and auto-generated charts

---

## 🏗️ RAG Architecture

```
User Question
    ↓
Query Decomposer         → breaks into 2-3 targeted sub-queries
    ↓
Multi-Query Retriever    → dense semantic search (Qdrant cosine)
    ↓
BM25 Keyword Scorer      → keyword relevance on retrieved pool
    ↓
RRF Fusion               → Reciprocal Rank Fusion of both lists
    ↓
Cross-Encoder Re-ranker  → ms-marco-MiniLM-L-6-v2 final scoring
    ↓
Context Assembler        → parent chunk expansion for richer context
    ↓
LLM (Groq LLaMA 3.3 70B) → grounded answer generation
    ↓
Self-Reflection          → hallucination check, retry if needed
    ↓
Chart Detector           → auto-generates matplotlib charts for numeric queries
    ↓
Final Answer + Sources + Optional Chart
```

---

## 🚀 Deployment Guide (15 minutes to live URL)

### Step 1 — Get API Keys

**A) Groq API Key** (you already have this ✅)
- [console.groq.com](https://console.groq.com) → API Keys → Create

**B) Qdrant Cloud** (free tier, no credit card)
1. Go to [cloud.qdrant.io](https://cloud.qdrant.io)
2. Sign up → Create Cluster → choose **Free tier** → any region
3. Copy the **Cluster URL** (looks like `https://abc123.aws.cloud.qdrant.io:6333`)
4. Go to **API Keys** → Create → copy the key

---

### Step 2 — Push to GitHub

```bash
# Create a new GitHub repo (github.com → New repository)
# Then in your local terminal:

cd bookmin-rag
git init
git add .
git commit -m "Initial BookMind RAG chatbot"
git remote add origin https://github.com/YOUR_USERNAME/bookmind-rag.git
git push -u origin main
```

> ⚠️ Make sure `.gitignore` is committed. Never push `.env` or `secrets.toml`.

---

### Step 3 — Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → Branch: `main` → Main file: `app.py`
5. Click **Advanced settings** → **Secrets** tab
6. Paste the following (replace with your actual keys):

```toml
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxx"
QDRANT_URL = "https://your-cluster.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "your_qdrant_api_key"
```

7. Click **Deploy!**
8. Wait ~3 minutes for first deployment
9. 🎉 Share your URL!

---

### Step 4 — Index Your Books

1. Open your deployed app URL
2. In the sidebar, click **Browse files** → upload your PDF(s)
3. Click **🔄 Index Documents**
4. Wait for indexing to complete (Rich Dad Poor Dad ~30 sec, Intelligent Investor ~2 min)
5. Start chatting!

> Books are indexed once and persist in Qdrant Cloud permanently.
> You only need to re-index if you add new books.

---

## 💻 Local Development

```bash
# Clone your repo
git clone https://github.com/YOUR_USERNAME/bookmind-rag.git
cd bookmind-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your keys

# Run
streamlit run app.py
```

Open: http://localhost:8501

---

## 📁 Project Structure

```
bookmind-rag/
├── app.py                    # Streamlit UI
├── requirements.txt
├── .env.example              # Template for local dev
├── .gitignore
├── .streamlit/
│   ├── config.toml           # Dark theme + server config
│   └── secrets.toml.example  # Template (never commit actual secrets)
├── rag/
│   ├── __init__.py
│   ├── ingestion.py          # PDF loading, hierarchical chunking, Qdrant indexing
│   ├── retriever.py          # Hybrid search (dense + BM25) + cross-encoder re-ranking
│   └── pipeline.py           # Agentic RAG orchestration (full pipeline)
└── utils/
    └── secrets.py            # Unified secret loading (.env + Streamlit secrets)
```

---

## 🎯 Example Questions to Try

**Rich Dad Poor Dad:**
- "What is the difference between assets and liabilities according to Kiyosaki?"
- "Explain the cash flow quadrant"
- "What does Robert say about the rat race?"
- "How should I invest my first salary based on this book?"

**The Intelligent Investor:**
- "What is Graham's concept of margin of safety?"
- "How does Graham define Mr. Market?"
- "What is the difference between investing and speculation?"
- "What are Graham's criteria for a defensive investor?"

**Cross-book / Analytics:**
- "Compare Kiyosaki's and Graham's views on stock market investing"
- "What percentage of income should I invest according to both books?"
- "Show me the key principles from both books as a comparison"

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| `GROQ_API_KEY not found` | Add secrets in Streamlit Cloud → Advanced → Secrets |
| Qdrant connection failed | Check cluster URL format: must include `https://` and `:6333` |
| Slow first response | Cross-encoder model downloads on first run (~80MB). Subsequent runs are fast. |
| Empty answers | Ensure PDFs are indexed (green badge in sidebar) |
| PDF won't upload | Max file size: 200MB. Compressed PDFs work best. |

---

## 📊 Technical Details

| Component | Choice | Details |
|-----------|--------|---------|
| LLM | LLaMA 3.3 70B via Groq | `llama-3.3-70b-versatile` |
| Embeddings | BAAI/bge-small-en-v1.5 | 384-dim, free, runs on CPU |
| Vector DB | Qdrant Cloud | Free tier: 1GB, 1M vectors |
| Chunking | Hierarchical parent-child | Parent: 900 tokens, Child: 250 tokens |
| Retrieval | Hybrid (Dense + BM25) | Top-20 dense, fused with BM25 |
| Re-ranking | Cross-encoder | ms-marco-MiniLM-L-6-v2 |
| Charts | Matplotlib | Auto-generated for numeric queries |

---

Built with ❤️ using Groq, Qdrant, LangChain, and Streamlit.
