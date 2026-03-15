@echo off
echo BookMind -- Local Dev Setup
echo ----------------------------

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo WARNING: Created .env from template.
    echo Edit .env and add your GROQ_API_KEY and QDRANT_URL before continuing.
    echo.
    pause
)

echo.
echo Starting BookMind at http://localhost:8501
echo Press Ctrl+C to stop
echo.
streamlit run app.py
