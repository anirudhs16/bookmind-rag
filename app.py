import streamlit as st
import os
import uuid
import re
from datetime import datetime

from utils.secrets import load_secrets
load_secrets()

st.set_page_config(
    page_title="BookMind",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; font-size: 15px; }
.stApp { background: #f9f8f6; }
.main .block-container { padding: 0 0 100px 0; max-width: 100%; }

/* Sidebar */
[data-testid="stSidebar"] { background: #f4f3ef !important; border-right: 1px solid #e5e4e0 !important; }
[data-testid="stSidebar"] > div { padding: 16px 12px !important; }

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton button {
    background: transparent; border: none; text-align: left;
    color: #3d3d3d; font-size: 0.84rem; padding: 7px 10px;
    border-radius: 8px; width: 100%; transition: background 0.15s;
}
[data-testid="stSidebar"] .stButton button:hover { background: #eae9e4; color: #1a1a1a; }

/* New chat primary button */
button[kind="primary"] {
    background: #1a1a1a !important; color: #fff !important;
    font-weight: 500 !important; border-radius: 8px !important;
    font-size: 0.85rem !important; border: none !important;
}
button[kind="primary"]:hover { background: #333 !important; }

/* Chat wrapper */
.chat-wrapper { max-width: 760px; margin: 0 auto; padding: 28px 20px 110px; }

/* Page header */
.page-header {
    display: flex; align-items: center; gap: 12px;
    padding: 0 0 22px; border-bottom: 1px solid #e8e7e3; margin-bottom: 28px;
}
.page-header .logo {
    width: 36px; height: 36px; background: #1a1a1a; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; flex-shrink: 0;
}
.page-header h1 { font-size: 1.2rem; font-weight: 600; color: #1a1a1a; margin: 0; letter-spacing: -0.3px; }
.page-header .subtitle { font-size: 0.76rem; color: #999; margin: 2px 0 0; }

/* Welcome */
.welcome-box { text-align: center; padding: 48px 24px 32px; }
.welcome-box .icon { font-size: 2.5rem; margin-bottom: 12px; }
.welcome-box h2 { font-size: 1.3rem; font-weight: 600; color: #1a1a1a; margin: 0 0 8px; }
.welcome-box p { font-size: 0.86rem; color: #777; margin: 0 0 28px; line-height: 1.6; }

.suggestion-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-width: 500px; margin: 0 auto; }
.suggestion-card {
    background: #fff; border: 1px solid #e5e4e0; border-radius: 10px;
    padding: 12px 14px; text-align: left;
}
.suggestion-card .s-icon { font-size: 1rem; margin-bottom: 5px; }
.suggestion-card .s-text { font-size: 0.79rem; color: #2d2d2d; line-height: 1.4; font-weight: 500; }
.suggestion-card .s-sub { font-size: 0.7rem; color: #aaa; margin-top: 2px; }

/* Messages */
.msg-row { display: flex; gap: 10px; margin: 16px 0; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
.avatar.bot { background: #1a1a1a; }
.avatar.user-av { background: #e8e7e3; }
.bubble { max-width: 80%; padding: 11px 15px; border-radius: 14px; font-size: 0.88rem; line-height: 1.65; }
.bubble.bot { background: #fff; border: 1px solid #e8e7e3; color: #1a1a1a; border-radius: 4px 14px 14px 14px; }
.bubble.user { background: #1a1a1a; color: #f0f0f0; border-radius: 14px 4px 14px 14px; }

/* Sources */
.sources-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f0eeea; }
.source-chip { display: inline-flex; align-items: center; gap: 4px; background: #f4f3ef; border: 1px solid #e5e4e0; border-radius: 20px; padding: 2px 9px; font-size: 0.71rem; color: #5a5a5a; font-weight: 500; }

/* Sidebar labels */
.sidebar-label { font-size: 0.69rem; font-weight: 600; color: #aaa; text-transform: uppercase; letter-spacing: 0.6px; padding: 4px 2px; margin: 14px 0 6px; }

/* Pills */
.pill { display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px; border-radius: 20px; font-size: 0.71rem; font-weight: 500; }
.pill-ok { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
.pill-warn { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.pill-book { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }

/* Input form */
[data-testid="stForm"] {
    background: #f9f8f6; border-top: 1px solid #e8e7e3;
    position: fixed; bottom: 0; left: 0; right: 0;
    padding: 12px 24px; z-index: 999;
}
[data-testid="stForm"] .stTextInput input {
    background: #fff !important; border: 1px solid #ddd !important;
    border-radius: 10px !important; color: #1a1a1a !important;
    font-size: 0.9rem !important;
}
[data-testid="stForm"] .stTextInput input:focus {
    border-color: #999 !important; box-shadow: 0 0 0 3px rgba(0,0,0,0.05) !important;
}
[data-testid="stForm"] .stButton button {
    background: #1a1a1a !important; color: #fff !important;
    border-radius: 10px !important; border: none !important;
    font-weight: 500 !important; font-size: 0.88rem !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }

/* Progress */
[data-testid="stProgressBar"] > div > div { background: #1a1a1a !important; }

/* Upload */
[data-testid="stFileUploader"] { border: 1.5px dashed #d5d4cf !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("sessions", {}), ("current_session", None),
             ("indexed_files", []), ("rag_ready", False), ("rag_pipeline", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

def new_session():
    sid = str(uuid.uuid4())[:8]
    st.session_state.sessions[sid] = {
        "id": sid, "title": "New conversation",
        "messages": [], "created": datetime.now().strftime("%b %d, %H:%M")
    }
    st.session_state.current_session = sid
    return sid

def get_current():
    if not st.session_state.current_session or \
       st.session_state.current_session not in st.session_state.sessions:
        new_session()
    return st.session_state.sessions[st.session_state.current_session]

def init_pipeline():
    if st.session_state.rag_pipeline is None:
        from rag.pipeline import AgenticRAGPipeline
        st.session_state.rag_pipeline = AgenticRAGPipeline()
    return st.session_state.rag_pipeline

def fmt(text):
    """Minimal safe HTML formatting for bot messages."""
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:0 0 16px;">
        <div style="background:#1a1a1a;width:30px;height:30px;border-radius:7px;
                    display:flex;align-items:center;justify-content:center;font-size:15px;">📚</div>
        <div>
            <div style="font-weight:600;font-size:0.93rem;color:#1a1a1a">BookMind</div>
            <div style="font-size:0.69rem;color:#aaa">Agentic RAG</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if st.button("＋  New chat", use_container_width=True, type="primary"):
        new_session(); st.rerun()

    st.markdown('<div class="sidebar-label">Conversations</div>', unsafe_allow_html=True)
    sessions_sorted = sorted(st.session_state.sessions.values(),
                             key=lambda x: x["created"], reverse=True)
    if not sessions_sorted:
        st.caption("No conversations yet")
    for s in sessions_sorted:
        c1, c2 = st.columns([5, 1])
        with c1:
            if st.button(s["title"][:32] + ("…" if len(s["title"]) > 32 else ""),
                         key=f"s_{s['id']}", use_container_width=True):
                st.session_state.current_session = s["id"]; st.rerun()
        with c2:
            if st.button("✕", key=f"d_{s['id']}"):
                del st.session_state.sessions[s["id"]]
                if st.session_state.current_session == s["id"]:
                    st.session_state.current_session = None
                st.rerun()

    st.markdown('<div class="sidebar-label">Books</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload PDFs", type=["pdf"],
                                accept_multiple_files=True, label_visibility="collapsed")
    new_files = [f for f in (uploaded or []) if f.name not in st.session_state.indexed_files]

    if new_files:
        if st.button("🔄  Index documents", use_container_width=True):
            pipeline = init_pipeline()
            prog = st.progress(0, text="Starting…")
            for i, f in enumerate(new_files):
                prog.progress((i + 0.2) / len(new_files), text=f"Processing {f.name[:26]}…")
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(f.read()); tmp_path = tmp.name
                pipeline.index_document(tmp_path, f.name)
                _os.unlink(tmp_path)
                st.session_state.indexed_files.append(f.name)
                prog.progress((i + 1) / len(new_files), text=f"✓ {f.name[:24]}")
            prog.empty()
            st.session_state.rag_ready = True
            st.rerun()

    if st.session_state.indexed_files:
        for fname in st.session_state.indexed_files:
            st.markdown(f'<div style="margin-bottom:4px"><span class="pill pill-book">📗 {fname[:26]}</span></div>',
                        unsafe_allow_html=True)
    else:
        st.caption("No books indexed yet")

    st.markdown('<div class="sidebar-label">Status</div>', unsafe_allow_html=True)
    gok = bool(os.getenv("GROQ_API_KEY")); qok = bool(os.getenv("QDRANT_URL"))
    st.markdown(
        f'<div style="margin-bottom:5px"><span class="pill {"pill-ok" if gok else "pill-warn"}">{"✓" if gok else "✗"} Groq</span></div>'
        f'<div><span class="pill {"pill-ok" if qok else "pill-warn"}">{"✓" if qok else "✗"} Qdrant</span></div>',
        unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
session = get_current()

st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <div class="logo">📚</div>
    <div>
        <h1>BookMind</h1>
        <div class="subtitle">Rich Dad Poor Dad · The Intelligent Investor · Agentic RAG</div>
    </div>
</div>
""", unsafe_allow_html=True)

if not session["messages"]:
    st.markdown("""
    <div class="welcome-box">
        <div class="icon">📖</div>
        <h2>What would you like to learn?</h2>
        <p>Ask questions about your uploaded books. I'll find the most relevant<br>
        passages using hybrid search and cite my sources.</p>
    </div>
    <div class="suggestion-grid">
        <div class="suggestion-card"><div class="s-icon">💰</div>
          <div class="s-text">Difference between assets and liabilities?</div>
          <div class="s-sub">Rich Dad Poor Dad</div></div>
        <div class="suggestion-card"><div class="s-icon">🛡️</div>
          <div class="s-text">Explain the margin of safety concept</div>
          <div class="s-sub">The Intelligent Investor</div></div>
        <div class="suggestion-card"><div class="s-icon">⚖️</div>
          <div class="s-text">Compare both authors' views on stocks</div>
          <div class="s-sub">Both books</div></div>
        <div class="suggestion-card"><div class="s-icon">🧠</div>
          <div class="s-text">What is the cash flow quadrant?</div>
          <div class="s-sub">Rich Dad Poor Dad</div></div>
    </div>""", unsafe_allow_html=True)
else:
    for msg in session["messages"]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="msg-row user">
                <div class="avatar user-av">👤</div>
                <div class="bubble user">{msg["content"]}</div>
            </div>""", unsafe_allow_html=True)
        else:
            sources_html = ""
            if msg.get("sources"):
                chips = "".join(f'<span class="source-chip">📄 {s}</span>' for s in msg["sources"])
                sources_html = f'<div class="sources-row">{chips}</div>'

            st.markdown(f"""
            <div class="msg-row">
                <div class="avatar bot">🤖</div>
                <div style="max-width:80%">
                    <div class="bubble bot">{fmt(msg["content"])}{sources_html}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            if msg.get("chart_data"):
                import matplotlib; matplotlib.use("Agg")
                import matplotlib.pyplot as plt, io
                cd = msg["chart_data"]
                fig, ax = plt.subplots(figsize=(6.2, 3), facecolor="#ffffff")
                ax.set_facecolor("#fafaf8")
                COLORS = ["#1a1a1a", "#555", "#888", "#aaa", "#ccc"]
                ctype = cd.get("type", "bar")
                if ctype == "bar":
                    bars = ax.bar(cd["labels"], cd["values"], color=COLORS[:len(cd["values"])], edgecolor="none", width=0.5)
                    for bar, val in zip(bars, cd["values"]):
                        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(cd["values"])*0.015,
                                str(val), ha="center", va="bottom", color="#555", fontsize=8.5, fontweight="500")
                elif ctype == "line":
                    ax.plot(cd["labels"], cd["values"], color="#1a1a1a", linewidth=2,
                            marker="o", markersize=4.5, markerfacecolor="#fff",
                            markeredgecolor="#1a1a1a", markeredgewidth=1.5)
                    ax.fill_between(range(len(cd["labels"])), cd["values"], alpha=0.06, color="#1a1a1a")
                elif ctype == "horizontal_bar":
                    ax.barh(cd["labels"], cd["values"], color=COLORS[:len(cd["values"])], edgecolor="none", height=0.5)
                ax.set_title(cd.get("title",""), color="#1a1a1a", fontsize=10.5, pad=8, fontweight="600", loc="left")
                ax.tick_params(colors="#888", labelsize=8)
                for sp in ax.spines.values(): sp.set_edgecolor("#e8e7e3")
                ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
                ax.yaxis.grid(True, color="#f0eeea", linewidth=0.8); ax.set_axisbelow(True)
                plt.tight_layout(pad=1.2)
                buf = io.BytesIO()
                plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#fff")
                buf.seek(0); st.image(buf, use_container_width=True); plt.close(fig)

st.markdown("</div>", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
if not st.session_state.rag_ready:
    st.warning("⚠️ Upload and index at least one PDF using the sidebar to start chatting.")

with st.form("chat_form", clear_on_submit=True):
    c1, c2 = st.columns([9, 1])
    with c1:
        user_input = st.text_input(
            "Message", label_visibility="collapsed",
            placeholder="Ask about your books…" if st.session_state.rag_ready else "Index a PDF first…",
            disabled=not st.session_state.rag_ready)
    with c2:
        submitted = st.form_submit_button("Send", use_container_width=True,
                                          type="primary", disabled=not st.session_state.rag_ready)

if submitted and user_input.strip():
    session["messages"].append({"role": "user", "content": user_input})
    if len(session["messages"]) == 1:
        session["title"] = user_input[:40]
    with st.spinner("Thinking…"):
        try:
            result = init_pipeline().query(question=user_input,
                                           chat_history=session["messages"][:-1])
            bot_msg = {"role": "assistant", "content": result["answer"],
                       "sources": result.get("sources", []), "chart_data": result.get("chart_data")}
        except Exception as e:
            bot_msg = {"role": "assistant", "content": f"Error: {e}", "sources": [], "chart_data": None}
    session["messages"].append(bot_msg)
    st.rerun()
