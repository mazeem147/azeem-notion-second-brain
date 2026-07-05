#!/usr/bin/env bash
# =============================================================================
# Second Brain — New Laptop Setup
#
# Usage:
#   1. Copy the entire "Notion Second Brain (Code)" folder to this machine
#   2. Open Terminal, cd into the folder, then run:
#        bash "New Laptop Setup/setup.sh"
# =============================================================================

set -uo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

# ── Resolve project root ──────────────────────────────────────────────────────
# Script lives in New Laptop Setup/ inside the project folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  🧠  Second Brain — New Laptop Setup${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${DIM}Project root: $PROJECT_ROOT${NC}"
    echo ""
}

step() { echo -e "${YELLOW}${BOLD}[$1/$TOTAL_STEPS] $2${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "  ${RED}✗${NC}  $1"; }
info() { echo -e "  ${DIM}$1${NC}"; }

TOTAL_STEPS=4

# ── Start ─────────────────────────────────────────────────────────────────────
print_header
cd "$PROJECT_ROOT"

# ── Step 1: Python ────────────────────────────────────────────────────────────
step 1 "Checking Python 3.9+"
echo ""

PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" --version 2>&1 | awk '{print $2}')
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
            PYTHON="$cmd"
            ok "Found $cmd ($VERSION)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.9+ not found."
    echo ""
    echo "  Install it one of these ways:"
    echo ""
    echo "  Option A — Download from python.org:"
    echo "    https://www.python.org/downloads/"
    echo ""
    echo "  Option B — Homebrew (if you have it):"
    echo "    brew install python@3.11"
    echo ""
    echo "  Then re-run this script."
    exit 1
fi
echo ""

# ── Step 2: Virtual environment ───────────────────────────────────────────────
step 2 "Setting up virtual environment"
echo ""

if [ -d "venv" ]; then
    ok "venv already exists — skipping creation"
else
    "$PYTHON" -m venv venv
    ok "venv created"
fi
echo ""

# ── Step 3: Install packages ──────────────────────────────────────────────────
step 3 "Installing Python packages"
echo ""
info "This downloads ~500 MB including sentence-transformers, Streamlit,"
info "ChromaDB, and the Anthropic SDK. Expect 3–5 minutes on first run."
echo ""

./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

ok "All packages installed"
echo ""

# ── Step 4: API keys ──────────────────────────────────────────────────────────
step 4 "Configuring API keys"
echo ""

if [ -f ".env" ] && grep -q "OPENROUTER_API_KEY" .env && grep -q "NOTION_TOKEN" .env; then
    ok ".env already configured — skipping"
else
    echo "  The app needs three keys. Get them from:"
    echo "    Notion token:       https://www.notion.so/my-integrations"
    echo "    OpenRouter key:     https://openrouter.ai/keys"
    echo "    Anthropic key:      https://console.anthropic.com/"
    echo ""

    read -rp "  Paste your NOTION_TOKEN and press Enter: " NOTION_KEY
    read -rp "  Paste your OPENROUTER_API_KEY and press Enter: " OR_KEY
    read -rp "  Paste your ANTHROPIC_API_KEY and press Enter: " ANT_KEY
    echo ""

    if [ -z "$NOTION_KEY" ] && [ -z "$OR_KEY" ] && [ -z "$ANT_KEY" ]; then
        warn "No keys entered. Create a .env file manually before running the app:"
        info "  NOTION_TOKEN=..."
        info "  OPENROUTER_API_KEY=sk-or-v1-..."
        info "  ANTHROPIC_API_KEY=sk-ant-..."
    else
        {
            [ -n "$NOTION_KEY" ] && echo "NOTION_TOKEN=$NOTION_KEY"
            [ -n "$OR_KEY" ]     && echo "OPENROUTER_API_KEY=$OR_KEY"
            [ -n "$ANT_KEY" ]    && echo "ANTHROPIC_API_KEY=$ANT_KEY"
        } > .env
        ok ".env created"
    fi
fi
echo ""

# ── Verify data ───────────────────────────────────────────────────────────────
echo -e "${BLUE}${BOLD}Checking your data...${NC}"
echo ""

RAW_COUNT=$(find data/raw -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
CHROMA_OK=false
DB_OK=false

if [ -d "data/chroma" ] && [ "$(ls -A data/chroma 2>/dev/null)" ]; then
    CHROMA_OK=true
    ok "ChromaDB vector store found"
else
    warn "No ChromaDB found — run the indexer once before chatting:"
    info "  ./venv/bin/python indexer.py"
fi

if [ -f "data/brain.db" ]; then
    DB_OK=true
    ok "brain.db found (diary entries, media logs, chat sessions)"
else
    warn "No brain.db found — it will be created automatically on first launch"
fi

ok "$RAW_COUNT note files in data/raw/"
echo ""

# ── Embedding model note ──────────────────────────────────────────────────────
if [ ! -d "$HOME/.cache/huggingface/hub" ]; then
    echo -e "  ${YELLOW}Note:${NC} The embedding model (~90 MB) will download automatically"
    echo "  the first time you run the indexer. You need internet for that step."
    echo ""
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓  Setup complete!${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  To launch the app at any time:"
echo -e "  ${BOLD}./venv/bin/streamlit run app.py${NC}"
echo ""

if [ "$CHROMA_OK" = false ]; then
    echo "  To build the search index from your notes (run once):"
    echo -e "  ${BOLD}./venv/bin/python indexer.py${NC}"
    echo ""
fi

read -rp "  Launch the app now? [Y/n]: " LAUNCH
LAUNCH="${LAUNCH:-Y}"

if [[ "$LAUNCH" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "  ${DIM}Opening at http://localhost:8501 — press Ctrl+C to stop.${NC}"
    echo ""
    ./venv/bin/streamlit run app.py
fi
