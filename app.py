import streamlit as st
import os
import uuid
import json
from datetime import datetime

# Load secrets from Streamlit Cloud or .env
from utils.secrets import load_secrets
load_secrets()

st.set_page_config(
    page_title="BookMind — RAG Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=Inter:wght@300;400;500;600&display=swap');

/* Base */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0f0f13; }
.stApp { background: #0f0f13; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #16161d !important;
    border-right: 1px solid #2a2a35;
}
[data-testid="stSidebar"] * { color: #c8c8d8 !important; }

/* Header */
.app-header {
    display: flex; align-items: center; gap: 14px;
    padding: 18px 0 10px 0; margin-bottom: 8px;
}
.app-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 1.9rem; color: #f0ece2; margin: 0;
    letter-spacing: -0.5px;
}
.app-header .subtitle { font-size: 0.78rem; color: #7a7a8c; margin: 0; }

/* Chat messages */
.msg-user {
    display: flex; justify-content: flex-end; margin: 10px 0;
}
.msg-user .bubble {
    background: #2563eb; color: #fff;
    padding: 11px 16px; border-radius: 18px 18px 4px 18px;
    max-width: 70%; font-size: 0.91rem; line-height: 1.55;
}
.msg-bot {
    display: flex; justify-content: flex-start; margin: 10px 0; gap: 10px;
}
.msg-bot .avatar {
    width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg, #7c3aed, #2563eb);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0; margin-top: 2px;
}
.msg-bot .bubble {
    background: #1e1e2a; color: #ddd8f0;
    padding: 12px 16px; border-radius: 4px 18px 18px 18px;
    max-width: 80%; font-size: 0.91rem; line-height: 1.65;
    border: 1px solid #2a2a38;
}

/* Sources */
.sources-box {
    margin-top: 10px; padding: 10px 14px;
    background: #13131c; border: 1px solid #2a2a38;
    border-radius: 10px; font-size: 0.78rem; color: #8888a8;
}
.sources-box strong { color: #a0a0c0; }
.source-tag {
    display: inline-block; background: #1e1e30;
    border: 1px solid #3a3a50; border-radius: 6px;
    padding: 2px 8px; margin: 3px 3px 0 0;
    font-size: 0.74rem; color: #9898b8;
}

/* Chat history sidebar items */
.chat-item {
    padding: 8px 12px; border-radius: 8px; cursor: pointer;
    margin-bottom: 4px; border: 1px solid transparent;
    font-size: 0.83rem; color: #9898b8;
    transition: all 0.15s;
}
.chat-item:hover { background: #1e1e2a; border-color: #2a2a38; color: #d0d0e0; }
.chat-item.active { background: #1e1e2a; border-color: #3a3aff44; color: #d0d0e8; }

/* Input area */
.stTextInput input, .stTextArea textarea {
    background: #1a1a24 !important; color: #e0e0f0 !important;
    border: 1px solid #2a2a38 !important; border-radius: 12px !important;
}
.stButton button {
    border-radius: 10px !important; font-weight: 500 !important;
}

/* Status badges */
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.5px;
}
.badge-green { background: #0d2b1a; color: #4ade80; border: 1px solid #166534; }
.badge-yellow { background: #2b2000; color: #fbbf24; border: 1px solid #78350f; }
.badge-blue { background: #0d1b3e; color: #60a5fa; border: 1px solid #1e3a8a; }

/* Spinner override */
.stSpinner > div { border-top-color: #7c3aed !important; }

/* Thinking step */
.thinking-step {
    font-size: 0.78rem; color: #5555780; padding: 4px 0;
    display: flex; align-items: center; gap: 6px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []
if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False
if "rag_pipeline" not in st.session_state:
    st.session_state.rag_pipeline = None

def new_session():
    sid = str(uuid.uuid4())[:8]
    st.session_state.sessions[sid] = {
        "id": sid,
        "title": "New Chat",
        "messages": [],
        "created": datetime.now().strftime("%b %d, %H:%M")
    }
    st.session_state.current_session = sid
    return sid

def get_current():
    if st.session_state.current_session not in st.session_state.sessions:
        new_session()
    return st.session_state.sessions[st.session_state.current_session]

def init_pipeline():
    """Lazy-load the RAG pipeline."""
    if st.session_state.rag_pipeline is None:
        from rag.pipeline import AgenticRAGPipeline
        st.session_state.rag_pipeline = AgenticRAGPipeline()
    return st.session_state.rag_pipeline

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 BookMind")
    st.markdown("<hr style='border-color:#2a2a38;margin:8px 0 14px'>", unsafe_allow_html=True)

    if st.button("＋  New Chat", use_container_width=True, type="primary"):
        new_session()
        st.rerun()

    st.markdown("**Chat History**")
    sessions_sorted = sorted(st.session_state.sessions.values(),
                             key=lambda x: x["created"], reverse=True)
    for s in sessions_sorted:
        is_active = s["id"] == st.session_state.current_session
        label = s["title"][:28] + ("…" if len(s["title"]) > 28 else "")
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(f"{'▶ ' if is_active else ''}{label}",
                         key=f"sess_{s['id']}", use_container_width=True):
                st.session_state.current_session = s["id"]
                st.rerun()
        with col2:
            if st.button("✕", key=f"del_{s['id']}"):
                del st.session_state.sessions[s["id"]]
                if st.session_state.current_session == s["id"]:
                    st.session_state.current_session = None
                st.rerun()

    st.markdown("<hr style='border-color:#2a2a38;margin:14px 0'>", unsafe_allow_html=True)

    # ── Document upload ──────────────────────────────────────────────────────
    st.markdown("**📎 Upload Books / PDFs**")
    uploaded = st.file_uploader("Drop PDF files here", type=["pdf"],
                                accept_multiple_files=True,
                                label_visibility="collapsed")

    if uploaded:
        new_files = [f for f in uploaded if f.name not in st.session_state.indexed_files]
        if new_files:
            if st.button("🔄 Index Documents", use_container_width=True):
                pipeline = init_pipeline()
                progress = st.progress(0, text="Initialising…")
                for i, f in enumerate(new_files):
                    progress.progress((i + 0.3) / len(new_files),
                                      text=f"Processing {f.name}…")
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(f.read())
                        tmp_path = tmp.name
                    pipeline.index_document(tmp_path, f.name)
                    os.unlink(tmp_path)
                    st.session_state.indexed_files.append(f.name)
                    progress.progress((i + 1) / len(new_files),
                                      text=f"Indexed {f.name}")
                progress.empty()
                st.session_state.rag_ready = True
                st.success(f"✅ Indexed {len(new_files)} file(s)")
                st.rerun()

    if st.session_state.indexed_files:
        st.markdown("**Indexed Books**")
        for fname in st.session_state.indexed_files:
            st.markdown(f'<span class="badge badge-green">📗 {fname[:24]}</span>',
                        unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#2a2a38;margin:14px 0'>", unsafe_allow_html=True)

    # ── API key check ────────────────────────────────────────────────────────
    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    qdrant_ok = bool(os.getenv("QDRANT_URL"))
    st.markdown(f'<span class="badge {"badge-green" if groq_ok else "badge-yellow"}">{"✓" if groq_ok else "✗"} Groq API</span>', unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown(f'<span class="badge {"badge-green" if qdrant_ok else "badge-yellow"}">{"✓" if qdrant_ok else "✗"} Qdrant DB</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("BookMind v1.0 · Agentic RAG")

# ── Main area ────────────────────────────────────────────────────────────────
session = get_current()

st.markdown("""
<div class="app-header">
    <div style="font-size:2rem">📚</div>
    <div>
        <h1>BookMind</h1>
        <p class="subtitle">Agentic RAG · Rich Dad Poor Dad · The Intelligent Investor</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Render messages ──────────────────────────────────────────────────────────
chat_container = st.container()

with chat_container:
    if not session["messages"]:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#4a4a60;">
            <div style="font-size:3rem;margin-bottom:12px">💬</div>
            <div style="font-size:1.1rem;color:#6a6a88;font-family:'Playfair Display',serif">
                Ask anything about your books
            </div>
            <div style="font-size:0.82rem;margin-top:8px;color:#444458">
                Try: "What is Robert Kiyosaki's key lesson about assets?" or 
                "How does Graham define a margin of safety?"
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in session["messages"]:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="msg-user">
                    <div class="bubble">{msg["content"]}</div>
                </div>""", unsafe_allow_html=True)
            else:
                # Bot message
                content = msg["content"]
                sources_html = ""
                if msg.get("sources"):
                    tags = "".join(f'<span class="source-tag">📄 {s}</span>'
                                   for s in msg["sources"])
                    sources_html = f'<div class="sources-box"><strong>Sources:</strong><br>{tags}</div>'

                st.markdown(f"""
                <div class="msg-bot">
                    <div class="avatar">🤖</div>
                    <div>
                        <div class="bubble">{content}</div>
                        {sources_html}
                    </div>
                </div>""", unsafe_allow_html=True)

                # Render chart if present
                if msg.get("chart_data"):
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt
                    import io
                    cd = msg["chart_data"]
                    fig, ax = plt.subplots(figsize=(7, 3.5),
                                           facecolor="#13131c")
                    ax.set_facecolor("#1a1a28")
                    ctype = cd.get("type", "bar")
                    if ctype == "bar":
                        bars = ax.bar(cd["labels"], cd["values"],
                                      color=["#7c3aed", "#2563eb", "#0891b2",
                                             "#059669", "#d97706"][:len(cd["values"])],
                                      edgecolor="none", width=0.5)
                        for bar, val in zip(bars, cd["values"]):
                            ax.text(bar.get_x() + bar.get_width()/2,
                                    bar.get_height() + max(cd["values"])*0.02,
                                    str(val), ha="center", va="bottom",
                                    color="#b0b0d0", fontsize=9)
                    elif ctype == "line":
                        ax.plot(cd["labels"], cd["values"],
                                color="#7c3aed", linewidth=2.5,
                                marker="o", markersize=6, markerfacecolor="#2563eb")
                        ax.fill_between(range(len(cd["labels"])), cd["values"],
                                        alpha=0.15, color="#7c3aed")
                    elif ctype == "horizontal_bar":
                        ax.barh(cd["labels"], cd["values"],
                                color=["#7c3aed", "#2563eb", "#0891b2",
                                       "#059669", "#d97706"][:len(cd["values"])],
                                edgecolor="none", height=0.5)

                    ax.set_title(cd.get("title", ""), color="#c0c0e0",
                                 fontsize=11, pad=10, fontweight="600")
                    ax.tick_params(colors="#6060808", labelsize=8.5)
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#2a2a38")
                    plt.tight_layout(pad=1.5)
                    buf = io.BytesIO()
                    plt.savefig(buf, format="png", dpi=150,
                                bbox_inches="tight", facecolor="#13131c")
                    buf.seek(0)
                    st.image(buf, use_container_width=True)
                    plt.close(fig)

# ── Input ────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

if not st.session_state.rag_ready:
    st.warning("⚠️ Please upload and index at least one PDF to start chatting.")

with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([9, 1])
    with col1:
        user_input = st.text_input(
            "Message",
            placeholder="Ask about Rich Dad Poor Dad, The Intelligent Investor, or both…",
            label_visibility="collapsed",
            disabled=not st.session_state.rag_ready
        )
    with col2:
        submitted = st.form_submit_button("Send", use_container_width=True,
                                          type="primary",
                                          disabled=not st.session_state.rag_ready)

if submitted and user_input.strip():
    # Save user message
    session["messages"].append({"role": "user", "content": user_input})

    # Update session title from first message
    if len(session["messages"]) == 1:
        session["title"] = user_input[:35]

    with st.spinner("🧠 Thinking…"):
        try:
            pipeline = init_pipeline()
            result = pipeline.query(
                question=user_input,
                chat_history=session["messages"][:-1]
            )
            bot_msg = {
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
                "chart_data": result.get("chart_data"),
            }
        except Exception as e:
            bot_msg = {
                "role": "assistant",
                "content": f"⚠️ Error: {str(e)}\n\nPlease check your API keys in the `.env` file.",
                "sources": [],
                "chart_data": None,
            }

    session["messages"].append(bot_msg)
    st.rerun()
