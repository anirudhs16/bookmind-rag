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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

* { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── App background ── */
.stApp, .main { background-color: #ffffff !important; }
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #f7f7f5 !important;
    border-right: 1px solid #e8e8e4 !important;
    min-width: 260px !important;
    max-width: 280px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 20px 14px !important;
}

/* All text in sidebar */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {
    color: #1a1a1a !important;
}

/* ── Sidebar buttons ── */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #1a1a1a !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
    font-size: 0.83rem !important;
    padding: 6px 10px !important;
    text-align: left !important;
    width: 100% !important;
    font-weight: 400 !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #ebebea !important;
    border-color: transparent !important;
}

/* New chat button override */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    border: none !important;
    padding: 9px 16px !important;
    margin-bottom: 4px !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
    background: #333333 !important;
}

/* ── File uploader — force light theme ── */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1.5px dashed #cccccc !important;
    border-radius: 10px !important;
    padding: 8px !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #1a1a1a !important;
    background: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background: #ffffff !important;
    color: #1a1a1a !important;
    border: 1px solid #cccccc !important;
    border-radius: 6px !important;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #999999 !important;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin: 16px 0 6px;
    padding: 0 2px;
}

/* ── Status pills ── */
.pill {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 500;
}
.pill-ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.pill-err { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.pill-book { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }

/* ── Main chat area ── */
.chat-outer {
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 24px 120px;
    background: #ffffff;
    min-height: 100vh;
}

/* ── Page header ── */
.page-header {
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 20px;
    border-bottom: 1px solid #efefed;
    margin-bottom: 28px;
}
.ph-logo {
    width: 36px; height: 36px; background: #1a1a1a; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px;
}
.ph-title { font-size: 1.15rem; font-weight: 600; color: #1a1a1a; margin: 0; }
.ph-sub   { font-size: 0.73rem; color: #aaaaaa; margin: 2px 0 0; }

/* ── Welcome ── */
.welcome { text-align: center; padding: 52px 20px 32px; }
.welcome .w-icon { font-size: 2.4rem; margin-bottom: 12px; }
.welcome h2 { font-size: 1.25rem; font-weight: 600; color: #1a1a1a; margin: 0 0 8px; }
.welcome p  { font-size: 0.84rem; color: #777; margin: 0 0 28px; line-height: 1.6; }

.sug-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-width: 480px; margin: 0 auto; }
.sug-card {
    background: #fafaf9; border: 1px solid #e8e8e4; border-radius: 10px;
    padding: 12px 14px; text-align: left;
}
.sug-icon { font-size: 1rem; margin-bottom: 4px; }
.sug-text { font-size: 0.78rem; color: #1a1a1a; font-weight: 500; line-height: 1.4; }
.sug-sub  { font-size: 0.69rem; color: #aaaaaa; margin-top: 2px; }

/* ── Chat messages ── */
.msg-wrap { margin: 16px 0; }

.msg-user {
    display: flex; justify-content: flex-end; margin: 14px 0;
}
.msg-user .bubble-u {
    background: #1a1a1a; color: #f5f5f5;
    padding: 10px 15px; border-radius: 16px 4px 16px 16px;
    font-size: 0.88rem; line-height: 1.6;
    max-width: 75%;
}

.msg-bot { display: flex; gap: 10px; margin: 14px 0; align-items: flex-start; }
.bot-av {
    width: 28px; height: 28px; min-width: 28px; background: #1a1a1a;
    border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 13px; margin-top: 2px;
}
.bubble-b {
    background: #fafaf9; border: 1px solid #e8e8e4;
    color: #1a1a1a; padding: 12px 16px;
    border-radius: 4px 16px 16px 16px;
    font-size: 0.88rem; line-height: 1.68;
    max-width: 85%;
}

/* ── Sources row ── */
.src-row {
    display: flex; flex-wrap: wrap; gap: 5px;
    margin-top: 10px; padding-top: 10px;
    border-top: 1px solid #efefed;
}
.src-chip {
    display: inline-flex; align-items: center; gap: 3px;
    background: #f4f4f2; border: 1px solid #e8e8e4;
    border-radius: 20px; padding: 2px 9px;
    font-size: 0.69rem; color: #555555; font-weight: 500;
}

/* ── Input bar ── */
.stForm {
    position: fixed !important; bottom: 0 !important;
    left: 0 !important; right: 0 !important;
    background: #ffffff !important;
    border-top: 1px solid #efefed !important;
    padding: 12px 24px !important;
    z-index: 9999 !important;
}
.stForm .stTextInput input {
    background: #fafaf9 !important;
    border: 1px solid #e0e0dc !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
    font-size: 0.9rem !important;
    padding: 10px 16px !important;
    font-family: 'Inter', sans-serif !important;
}
.stForm .stTextInput input:focus {
    border-color: #aaaaaa !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.05) !important;
    outline: none !important;
}
.stForm .stTextInput input::placeholder { color: #aaaaaa !important; }

.stForm .stButton > button {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 10px 20px !important;
}
.stForm .stButton > button:hover { background: #333333 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: #dddddd; border-radius: 3px; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div { background: #1a1a1a !important; }

/* ── Warnings ── */
.stAlert { border-radius: 8px !important; font-size: 0.83rem !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #1a1a1a !important; }

/* ── Hide streamlit default elements ── */
#MainMenu, footer, header { visibility: hidden; }
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

def safe_fmt(text):
    """Safely convert markdown-like text to simple HTML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo row
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:0 0 16px 2px;">
        <div style="background:#1a1a1a;width:30px;height:30px;border-radius:7px;
             display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">📚</div>
        <div>
            <div style="font-size:0.92rem;font-weight:600;color:#1a1a1a;line-height:1.2;">BookMind</div>
            <div style="font-size:0.68rem;color:#aaaaaa;line-height:1.2;">Agentic RAG</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("＋  New chat", use_container_width=True, type="primary"):
        new_session()
        st.rerun()

    # ── Conversations ──
    st.markdown('<div class="section-label">Conversations</div>', unsafe_allow_html=True)
    sessions_sorted = sorted(st.session_state.sessions.values(),
                             key=lambda x: x["created"], reverse=True)
    if not sessions_sorted:
        st.markdown('<p style="font-size:0.78rem;color:#aaaaaa;margin:0;padding:2px 2px;">No conversations yet</p>',
                    unsafe_allow_html=True)
    for s in sessions_sorted:
        c1, c2 = st.columns([5, 1])
        with c1:
            label = s["title"][:30] + ("…" if len(s["title"]) > 30 else "")
            if st.button(label, key=f"s_{s['id']}", use_container_width=True):
                st.session_state.current_session = s["id"]
                st.rerun()
        with c2:
            if st.button("✕", key=f"d_{s['id']}"):
                del st.session_state.sessions[s["id"]]
                if st.session_state.current_session == s["id"]:
                    st.session_state.current_session = None
                st.rerun()

    # ── Books / Upload ──
    st.markdown('<div class="section-label">Books</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload PDFs", type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    new_files = [f for f in (uploaded or []) if f.name not in st.session_state.indexed_files]

    if new_files:
        if st.button("🔄  Index documents", use_container_width=True):
            pipeline = init_pipeline()
            prog = st.progress(0, text="Starting…")
            for i, f in enumerate(new_files):
                prog.progress((i + 0.2) / len(new_files), text=f"Processing {f.name[:26]}…")
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name
                pipeline.index_document(tmp_path, f.name)
                _os.unlink(tmp_path)
                st.session_state.indexed_files.append(f.name)
                prog.progress((i + 1) / len(new_files), text=f"✓ {f.name[:24]}")
            prog.empty()
            st.session_state.rag_ready = True
            st.rerun()

    if st.session_state.indexed_files:
        for fname in st.session_state.indexed_files:
            st.markdown(
                f'<div style="margin:3px 0"><span class="pill pill-book">📗 {fname[:26]}</span></div>',
                unsafe_allow_html=True)
    else:
        st.markdown('<p style="font-size:0.78rem;color:#aaaaaa;margin:4px 2px;">No books indexed yet</p>',
                    unsafe_allow_html=True)

    # ── Status ──
    st.markdown('<div class="section-label">Status</div>', unsafe_allow_html=True)
    gok = bool(os.getenv("GROQ_API_KEY"))
    qok = bool(os.getenv("QDRANT_URL"))
    st.markdown(
        f'<div style="margin-bottom:5px">'
        f'<span class="pill {"pill-ok" if gok else "pill-err"}">{"✓" if gok else "✗"} Groq</span></div>'
        f'<div><span class="pill {"pill-ok" if qok else "pill-err"}">{"✓" if qok else "✗"} Qdrant</span></div>',
        unsafe_allow_html=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────
session = get_current()

# Wrap everything in a centered div
st.markdown('<div class="chat-outer">', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="page-header">
    <div class="ph-logo">📚</div>
    <div>
        <div class="ph-title">BookMind</div>
        <div class="ph-sub">Rich Dad Poor Dad · The Intelligent Investor · Agentic RAG</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Not indexed warning ──
if not st.session_state.rag_ready:
    st.info("👈  Upload and index a PDF from the sidebar to start chatting.")

# ── Welcome or messages ──
if not session["messages"]:
    st.markdown("""
    <div class="welcome">
        <div class="w-icon">📖</div>
        <h2>What would you like to learn?</h2>
        <p>Ask questions about your books. I'll retrieve the most relevant passages<br>
        using hybrid search and cite every source.</p>
    </div>
    <div class="sug-grid">
        <div class="sug-card">
            <div class="sug-icon">💰</div>
            <div class="sug-text">What's the difference between assets and liabilities?</div>
            <div class="sug-sub">Rich Dad Poor Dad</div>
        </div>
        <div class="sug-card">
            <div class="sug-icon">🛡️</div>
            <div class="sug-text">Explain the margin of safety concept</div>
            <div class="sug-sub">The Intelligent Investor</div>
        </div>
        <div class="sug-card">
            <div class="sug-icon">⚖️</div>
            <div class="sug-text">Compare both authors' views on stocks</div>
            <div class="sug-sub">Both books</div>
        </div>
        <div class="sug-card">
            <div class="sug-icon">🧠</div>
            <div class="sug-text">What is the cash flow quadrant?</div>
            <div class="sug-sub">Rich Dad Poor Dad</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in session["messages"]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="msg-user">
                <div class="bubble-u">{msg["content"]}</div>
            </div>""", unsafe_allow_html=True)
        else:
            sources_html = ""
            if msg.get("sources"):
                chips = "".join(
                    f'<span class="src-chip">📄 {s}</span>'
                    for s in msg["sources"]
                )
                sources_html = f'<div class="src-row">{chips}</div>'

            st.markdown(f"""
            <div class="msg-bot">
                <div class="bot-av">🤖</div>
                <div class="bubble-b">{safe_fmt(msg["content"])}{sources_html}</div>
            </div>""", unsafe_allow_html=True)

            # Render chart if present
            if msg.get("chart_data"):
                try:
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt
                    import io

                    cd = msg["chart_data"]
                    fig, ax = plt.subplots(figsize=(6, 3), facecolor="#ffffff")
                    ax.set_facecolor("#fafaf9")
                    COLORS = ["#1a1a1a", "#555555", "#888888", "#aaaaaa", "#cccccc"]
                    ctype = cd.get("type", "bar")
                    vals = cd.get("values", [])
                    labs = cd.get("labels", [])

                    if ctype == "bar":
                        bars = ax.bar(labs, vals,
                                      color=COLORS[:len(vals)],
                                      edgecolor="none", width=0.5)
                        for bar, val in zip(bars, vals):
                            ax.text(bar.get_x() + bar.get_width()/2,
                                    bar.get_height() + max(vals) * 0.015,
                                    str(val), ha="center", va="bottom",
                                    color="#555", fontsize=8.5, fontweight="500")
                    elif ctype == "line":
                        ax.plot(labs, vals, color="#1a1a1a", linewidth=2,
                                marker="o", markersize=4.5,
                                markerfacecolor="#fff", markeredgecolor="#1a1a1a",
                                markeredgewidth=1.5)
                        ax.fill_between(range(len(labs)), vals,
                                        alpha=0.06, color="#1a1a1a")
                    elif ctype == "horizontal_bar":
                        ax.barh(labs, vals, color=COLORS[:len(vals)],
                                edgecolor="none", height=0.5)

                    ax.set_title(cd.get("title", ""), color="#1a1a1a",
                                 fontsize=10, pad=8, fontweight="600", loc="left")
                    ax.tick_params(colors="#888888", labelsize=8)
                    for sp in ax.spines.values():
                        sp.set_edgecolor("#e8e8e4")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.yaxis.grid(True, color="#f0f0ee", linewidth=0.8)
                    ax.set_axisbelow(True)
                    plt.tight_layout(pad=1.2)

                    buf = io.BytesIO()
                    plt.savefig(buf, format="png", dpi=150,
                                bbox_inches="tight", facecolor="#ffffff")
                    buf.seek(0)
                    st.image(buf, use_container_width=True)
                    plt.close(fig)
                except Exception:
                    pass

st.markdown("</div>", unsafe_allow_html=True)

# ── Fixed input form at bottom ────────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    c1, c2 = st.columns([9, 1])
    with c1:
        user_input = st.text_input(
            "Message",
            label_visibility="collapsed",
            placeholder="Ask about your books…" if st.session_state.rag_ready else "Index a PDF first to enable chat…",
            disabled=not st.session_state.rag_ready
        )
    with c2:
        submitted = st.form_submit_button(
            "Send",
            use_container_width=True,
            type="primary",
            disabled=not st.session_state.rag_ready
        )

if submitted and user_input.strip():
    session["messages"].append({"role": "user", "content": user_input})
    if len(session["messages"]) == 1:
        session["title"] = user_input[:40]

    with st.spinner("Thinking…"):
        try:
            result = init_pipeline().query(
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
                "content": f"Something went wrong: {str(e)}",
                "sources": [],
                "chart_data": None,
            }

    session["messages"].append(bot_msg)
    st.rerun()
