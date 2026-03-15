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

# ─────────────────────────────────────────────────────────────────────────────
# CSS — minimal, surgical, no position:fixed hacks, no kind= selectors
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* App shell */
.stApp { background: #ffffff !important; }
.main .block-container {
    max-width: 780px !important;
    padding: 2rem 1.5rem 2rem !important;
    margin: 0 auto !important;
}

/* ── Sidebar shell ── */
[data-testid="stSidebar"] {
    background: #f7f7f5 !important;
    border-right: 1px solid #e5e5e2 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.2rem 1rem !important;
}

/* ── ALL sidebar text dark ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* ── File uploader: force white bg, dark text ── */
[data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1.5px dashed #d0d0cb !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] * {
    background: #ffffff !important;
    color: #1a1a1a !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: #ffffff !important;
    color: #1a1a1a !important;
    border: 1px solid #d0d0cb !important;
    border-radius: 6px !important;
}
[data-testid="stFileUploaderDropzone"] small {
    color: #888888 !important;
}

/* ── Sidebar buttons — default (history / delete) ── */
[data-testid="stSidebar"] button {
    background: transparent !important;
    color: #1a1a1a !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
    font-size: 0.83rem !important;
    text-align: left !important;
    box-shadow: none !important;
    font-weight: 400 !important;
}
[data-testid="stSidebar"] button:hover {
    background: #ebebea !important;
    border-color: transparent !important;
}

/* ── New Chat button: the FIRST button rendered in sidebar ── */
[data-testid="stSidebar"] > div:first-child > div > div:first-child button,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
    background: #333333 !important;
    color: #ffffff !important;
}

/* ── Index documents button ── */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: #f0f0ec !important;
    color: #1a1a1a !important;
    border: 1px solid #d8d8d2 !important;
    border-radius: 7px !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
}

/* ── Main send button ── */
.main-area [data-testid="stBaseButton-primary"],
.stForm [data-testid="stBaseButton-primary"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    min-height: 42px !important;
}
.main-area [data-testid="stBaseButton-primary"]:hover,
.stForm [data-testid="stBaseButton-primary"]:hover {
    background: #333333 !important;
}

/* ── Text input ── */
[data-testid="stTextInput"] input {
    background: #fafaf8 !important;
    border: 1px solid #e0e0da !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #aaaaaa !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.05) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #aaaaaa !important;
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div { background: #1a1a1a !important; }

/* ── Info / warning boxes ── */
[data-testid="stAlertContainer"] { border-radius: 8px !important; }

/* ── Horizontal rule ── */
hr { border-color: #eeeee9 !important; margin: 0.8rem 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #d8d8d2; border-radius: 4px; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Sidebar section label ── */
.slabel {
    font-size: 0.68rem;
    font-weight: 600;
    color: #999999;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin: 1rem 0 0.4rem;
    display: block;
}

/* ── Pills ── */
.pill {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 500; line-height: 1.4;
}
.p-ok   { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.p-err  { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.p-book { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

/* ── Chat messages ── */
.msg-user {
    display: flex;
    justify-content: flex-end;
    margin: 12px 0;
}
.bubble-user {
    background: #1a1a1a;
    color: #f5f5f5;
    padding: 10px 15px;
    border-radius: 16px 4px 16px 16px;
    font-size: 0.88rem;
    line-height: 1.6;
    max-width: 76%;
    word-wrap: break-word;
}

.msg-bot {
    display: flex;
    gap: 10px;
    margin: 12px 0;
    align-items: flex-start;
}
.bot-avatar {
    width: 28px; height: 28px; min-width: 28px;
    background: #1a1a1a; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; margin-top: 3px;
}
.bubble-bot {
    background: #fafaf8;
    border: 1px solid #e8e8e3;
    color: #1a1a1a;
    padding: 12px 16px;
    border-radius: 4px 16px 16px 16px;
    font-size: 0.88rem;
    line-height: 1.7;
    max-width: 85%;
    word-wrap: break-word;
}
.bubble-bot strong { font-weight: 600; color: #111111; }

/* ── Source chips ── */
.src-row {
    display: flex; flex-wrap: wrap; gap: 5px;
    margin-top: 10px; padding-top: 10px;
    border-top: 1px solid #eeeee9;
}
.src-chip {
    display: inline-flex; align-items: center; gap: 3px;
    background: #f4f4f1; border: 1px solid #e5e5e0;
    border-radius: 20px; padding: 2px 9px;
    font-size: 0.69rem; color: #555555; font-weight: 500;
}

/* ── Welcome cards ── */
.sug-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px; max-width: 500px; margin: 0 auto;
}
.sug-card {
    background: #fafaf8; border: 1px solid #e8e8e3;
    border-radius: 10px; padding: 14px;
    cursor: default;
}
.sug-icon { font-size: 1.1rem; margin-bottom: 6px; }
.sug-text { font-size: 0.78rem; color: #111; font-weight: 500; line-height: 1.4; }
.sug-sub  { font-size: 0.68rem; color: #aaaaaa; margin-top: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
for k, v in [
    ("sessions", {}),
    ("current_session", None),
    ("indexed_files", []),
    ("rag_ready", False),
    ("rag_pipeline", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


def new_session():
    sid = str(uuid.uuid4())[:8]
    st.session_state.sessions[sid] = {
        "id": sid,
        "title": "New conversation",
        "messages": [],
        "created": datetime.now().strftime("%b %d, %H:%M"),
    }
    st.session_state.current_session = sid
    return sid


def get_current():
    if (
        not st.session_state.current_session
        or st.session_state.current_session not in st.session_state.sessions
    ):
        new_session()
    return st.session_state.sessions[st.session_state.current_session]


def init_pipeline():
    if st.session_state.rag_pipeline is None:
        from rag.pipeline import AgenticRAGPipeline
        st.session_state.rag_pipeline = AgenticRAGPipeline()
    return st.session_state.rag_pipeline


def safe_fmt(text: str) -> str:
    """Convert plain text + **bold** to safe HTML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:

    # Logo
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;padding:0 0 14px 2px">
          <div style="background:#1a1a1a;width:30px;height:30px;border-radius:7px;
               flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px">📚</div>
          <div>
            <div style="font-size:0.92rem;font-weight:600;color:#1a1a1a;line-height:1.2">BookMind</div>
            <div style="font-size:0.67rem;color:#999;line-height:1.2">Agentic RAG</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # New chat
    if st.button("＋  New chat", use_container_width=True, type="primary", key="new_chat_btn"):
        new_session()
        st.rerun()

    # ── Conversations ──────────────────────────────────────────────────────
    st.markdown('<span class="slabel">Conversations</span>', unsafe_allow_html=True)

    sessions_sorted = sorted(
        st.session_state.sessions.values(), key=lambda x: x["created"], reverse=True
    )
    if not sessions_sorted:
        st.markdown(
            '<p style="font-size:0.78rem;color:#aaa;margin:2px 0 8px">No conversations yet</p>',
            unsafe_allow_html=True,
        )
    for s in sessions_sorted:
        col_title, col_del = st.columns([5, 1])
        with col_title:
            label = s["title"][:28] + ("…" if len(s["title"]) > 28 else "")
            if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
                st.session_state.current_session = s["id"]
                st.rerun()
        with col_del:
            if st.button("✕", key=f"del_{s['id']}"):
                del st.session_state.sessions[s["id"]]
                if st.session_state.current_session == s["id"]:
                    st.session_state.current_session = None
                st.rerun()

    # ── Books ──────────────────────────────────────────────────────────────
    st.markdown('<span class="slabel">Books</span>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="pdf_uploader",
    )
    new_files = [f for f in (uploaded or []) if f.name not in st.session_state.indexed_files]

    if new_files:
        if st.button("🔄  Index documents", use_container_width=True, key="index_btn"):
            pipeline = init_pipeline()
            prog = st.progress(0, text="Starting…")
            import tempfile, os as _os
            for i, f in enumerate(new_files):
                prog.progress((i + 0.2) / len(new_files), text=f"Processing {f.name[:26]}…")
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
                f'<div style="margin:3px 0"><span class="pill p-book">📗 {fname[:26]}</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<p style="font-size:0.78rem;color:#aaa;margin:2px 0">No books indexed yet</p>',
            unsafe_allow_html=True,
        )

    # ── Status ─────────────────────────────────────────────────────────────
    st.markdown('<span class="slabel">Status</span>', unsafe_allow_html=True)
    gok = bool(os.getenv("GROQ_API_KEY"))
    qok = bool(os.getenv("QDRANT_URL"))
    g_cls = "p-ok" if gok else "p-err"
    q_cls = "p-ok" if qok else "p-err"
    g_sym = "✓" if gok else "✗"
    q_sym = "✓" if qok else "✗"
    st.markdown(
        f'<div style="margin-bottom:5px"><span class="pill {g_cls}">{g_sym} Groq</span></div>'
        f'<div><span class="pill {q_cls}">{q_sym} Qdrant</span></div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
session = get_current()

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;padding-bottom:18px;
         border-bottom:1px solid #eeeee9;margin-bottom:24px">
      <div style="background:#1a1a1a;width:34px;height:34px;border-radius:8px;flex-shrink:0;
           display:flex;align-items:center;justify-content:center;font-size:16px">📚</div>
      <div>
        <div style="font-size:1.1rem;font-weight:600;color:#1a1a1a;line-height:1.2">BookMind</div>
        <div style="font-size:0.72rem;color:#aaa;line-height:1.2">
          Rich Dad Poor Dad · The Intelligent Investor · Agentic RAG</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Upload reminder ─────────────────────────────────────────────────────────
if not st.session_state.rag_ready:
    st.info("👈  Upload and index a PDF from the sidebar to start chatting.", icon="ℹ️")

# ── Welcome screen ─────────────────────────────────────────────────────────
if not session["messages"]:
    st.markdown(
        """
        <div style="text-align:center;padding:40px 20px 28px">
          <div style="font-size:2.2rem;margin-bottom:12px">📖</div>
          <div style="font-size:1.2rem;font-weight:600;color:#1a1a1a;margin-bottom:8px">
            What would you like to learn?</div>
          <div style="font-size:0.84rem;color:#777;line-height:1.6">
            Ask questions about your books. I'll find the most relevant passages<br>
            using hybrid search and cite every source.
          </div>
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
            <div class="sug-text">Compare both authors' views on stock investing</div>
            <div class="sug-sub">Both books</div>
          </div>
          <div class="sug-card">
            <div class="sug-icon">🧠</div>
            <div class="sug-text">What is the cash flow quadrant?</div>
            <div class="sug-sub">Rich Dad Poor Dad</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Chat messages ───────────────────────────────────────────────────────────
for msg in session["messages"]:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-user"><div class="bubble-user">{msg["content"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        sources_html = ""
        if msg.get("sources"):
            chips = "".join(f'<span class="src-chip">📄 {s}</span>' for s in msg["sources"])
            sources_html = f'<div class="src-row">{chips}</div>'

        st.markdown(
            f"""
            <div class="msg-bot">
              <div class="bot-avatar">🤖</div>
              <div class="bubble-bot">{safe_fmt(msg["content"])}{sources_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Chart rendering
        if msg.get("chart_data"):
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                import io

                cd = msg["chart_data"]
                vals = cd.get("values", [])
                labs = cd.get("labels", [])
                if vals and labs:
                    COLORS = ["#1a1a1a", "#555", "#888", "#aaa", "#ccc"]
                    fig, ax = plt.subplots(figsize=(6, 3), facecolor="#ffffff")
                    ax.set_facecolor("#fafaf8")
                    ctype = cd.get("type", "bar")

                    if ctype == "bar":
                        bars = ax.bar(labs, vals, color=COLORS[: len(vals)],
                                      edgecolor="none", width=0.5)
                        for bar, val in zip(bars, vals):
                            ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + max(vals) * 0.015,
                                str(val), ha="center", va="bottom",
                                color="#555", fontsize=8.5, fontweight="500",
                            )
                    elif ctype == "line":
                        ax.plot(labs, vals, color="#1a1a1a", linewidth=2,
                                marker="o", markersize=5,
                                markerfacecolor="#fff", markeredgecolor="#1a1a1a",
                                markeredgewidth=1.5)
                        ax.fill_between(range(len(labs)), vals, alpha=0.06, color="#1a1a1a")
                    elif ctype == "horizontal_bar":
                        ax.barh(labs, vals, color=COLORS[: len(vals)],
                                edgecolor="none", height=0.5)

                    ax.set_title(cd.get("title", ""), color="#1a1a1a",
                                 fontsize=10, pad=8, fontweight="600", loc="left")
                    ax.tick_params(colors="#888", labelsize=8)
                    for sp in ax.spines.values():
                        sp.set_edgecolor("#e8e8e3")
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
                pass  # silently skip chart errors

# ─────────────────────────────────────────────────────────────────────────────
# INPUT — use st.chat_input (Streamlit's native, always at bottom, always works)
# ─────────────────────────────────────────────────────────────────────────────
placeholder = (
    "Ask about your books…"
    if st.session_state.rag_ready
    else "Index a PDF from the sidebar first…"
)

user_input = st.chat_input(placeholder, disabled=False)
# Note: st.chat_input is NEVER disabled — if not ready we show a clear message above
# and handle gracefully below

if user_input and user_input.strip():
    if not st.session_state.rag_ready:
        st.warning("Please index a PDF first using the sidebar.")
        st.stop()

    session["messages"].append({"role": "user", "content": user_input})
    if len(session["messages"]) == 1:
        session["title"] = user_input[:40]

    with st.spinner("Thinking…"):
        try:
            result = init_pipeline().query(
                question=user_input,
                chat_history=session["messages"][:-1],
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
