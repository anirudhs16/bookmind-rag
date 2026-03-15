"""
utils/secrets.py — Unified secret loading for local dev (.env) and Streamlit Cloud (st.secrets).
"""
import os

def load_secrets():
    """Load secrets from Streamlit secrets or .env file."""
    try:
        import streamlit as st
        # Streamlit Cloud — inject into environment
        for key in ["GROQ_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = st.secrets[key]
    except Exception:
        pass

    # Fallback: load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
