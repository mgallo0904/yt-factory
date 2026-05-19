#!/usr/bin/env bash
#==============================================================================
# yt-factory — One-Click Setup Script
# Installs system tools, Python deps, and creates project directories.
#==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"

echo "=============================================="
echo "  yt-factory — Setup"
echo "  OS detected: $OS"
echo "  Target dir: $REPO_DIR"
echo "=============================================="

# --- 1. Install system CLI tools ---
install_system_tools() {
    echo "[1/4] Installing system CLI tools..."

    if [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew &>/dev/null; then
            echo "  Homebrew not found. Install from https://brew.sh then re-run."
            exit 1
        fi
        brew install ffmpeg imagemagick yt-dlp 2>/dev/null || true
    elif [[ "$OS" == "Linux" ]]; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg imagemagick 2>/dev/null || true
        # yt-dlp via pip if not available
        pip install --quiet yt-dlp 2>/dev/null || true
    else
        echo "  Windows detected. Use WSL2 or install ffmpeg/imagemagick via chocolatey:"
        echo "    choco install ffmpeg imagemagick yt-dlp"
    fi
}

# --- 2. Install Python packages ---
install_python_deps() {
    echo "[2/4] Installing Python dependencies..."
    pip install -r "$REPO_DIR/requirements.txt"
}

# --- 3. Verify Ollama ---
setup_ollama() {
    echo "[3/4] Checking Ollama..."
    if ! command -v ollama >/dev/null 2>&1; then
        echo "  Ollama CLI not found. Install from https://ollama.com/download"
        echo "  Or set your Ollama-compatible API endpoint in .env"
    fi
    echo "  (If using a cloud endpoint, configure API_BASE in your .env file)"
}

# --- 4. Create helper directories ---
mkdir -p "$REPO_DIR/scripts"
mkdir -p "$REPO_DIR/assets/stock"
mkdir -p "$REPO_DIR/assets/final"
mkdir -p "$REPO_DIR/assets/thumbnails"
mkdir -p "$REPO_DIR/voiceovers/full"
mkdir -p "$REPO_DIR/voiceovers/hooks"

echo "[4/4] Directory structure ready."

# --- Run ---
install_system_tools
install_python_deps
setup_ollama

echo ""
echo "=============================================="
echo "  Setup complete."
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Create a .env file with your API keys (see .env.example)"
echo "  2. python3 generate_scripts.py"
echo "  3. python3 prep_voiceover.py"
echo "  4. python3 generate_full_audio.py"
echo ""
