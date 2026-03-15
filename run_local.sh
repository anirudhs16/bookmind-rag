#!/bin/bash
# ── BookMind: Local dev runner ──────────────────────────────────────────────
set -e

echo "📚 BookMind — Local Dev Setup"
echo "────────────────────────────"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 not found. Install Python 3.10+"
  exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install deps
echo "→ Installing dependencies..."
pip install -q -r requirements.txt

# Check .env
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Created .env from template."
    echo "   Edit .env and add your GROQ_API_KEY and QDRANT_URL before continuing."
    echo ""
    read -p "Press Enter once you've filled in .env..."
  else
    echo "❌ No .env file found. Create one with GROQ_API_KEY and QDRANT_URL."
    exit 1
  fi
fi

echo ""
echo "✅ Starting BookMind at http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""
streamlit run app.py
