#!/usr/bin/env bash
#==============================================================================
# YouTube Faceless Channel — One-Click Setup Script
# Installs all free CLI tools, Python deps, and vision helpers.
#==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"

echo "=============================================="
echo "  Faceless YouTube Channel — Setup"
echo "  OS detected: $OS"
echo "  Target dir: $REPO_DIR"
echo "=============================================="

# --- 1. Install system CLI tools ---
install_system_tools() {
    echo "[1/5] Installing system CLI tools..."

    if [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew &>/dev/null; then
            echo "  Homebrew not found. Install from https://brew.sh then re-run."
            exit 1
        fi
        brew install ffmpeg imagemagick yt-dlp
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg imagemagick yt-dlp
        elif command -v yum &>/dev/null; then
            sudo yum install -y ffmpeg imagemagick yt-dlp
        else
            echo "  Unknown Linux package manager. Install ffmpeg, imagemagick, yt-dlp manually."
        fi
    else
        echo "  Windows detected. Use WSL2 or install ffmpeg/imagemagick via chocolatey:"
        echo "    choco install ffmpeg imagemagick yt-dlp"
    fi
}

# --- 2. Install Python packages ---
install_python_deps() {
    echo "[2/5] Installing Python dependencies..."
    pip install --quiet openai-whisper requests python-dotenv Pillow
}

# --- 3. Verify / setup Ollama ---
setup_ollama() {
    echo "[3/5] Checking Ollama..."
    if ! command -v ollama &>/dev/null; then
        echo "  Ollama CLI not found. Install from https://ollama.com/download"
        exit 1
    fi

    echo "  Pulling kimi-k2.6:cloud (if not present)..."
    ollama pull kimi-k2.6:cloud || echo "  (Pull may require auth via your API key; skipped if unauthorized)"

    echo "  Verifying kimi-k2.6:cloud availability..."
    if ollama list | grep -q "kimi-k2.6:cloud"; then
        echo "  ✓ Model available locally or via cloud."
    else
        echo "  ! Model not in local list. Cloud inference via API will still work."
    fi
}

# --- 4. Create helper directories ---
mkdir -p "$REPO_DIR/scripts"
mkdir -p "$REPO_DIR/thumbnails"
mkdir -p "$REPO_DIR/voiceovers"
mkdir -p "$REPO_DIR/assets/stock"
mkdir -p "$REPO_DIR/assets/music"

# --- 5. Run installers ---
install_system_tools
install_python_deps
setup_ollama

echo ""
echo "=============================================="
echo "  Setup complete."
echo "=============================================="
echo ""
echo "Helper scripts created in: $REPO_DIR"
echo "  - generate_scripts.py      (batch script writer)"
echo "  - generate_thumbnails.py     (title + thumb text)"
echo "  - vision_analyze_thumb.py    (AI vision thumbnail review) ← NEW"
echo "  - extract_broll.py           (auto-extract key frames) ← NEW"
echo ""
echo "Next steps:"
echo "  1. export OLLAMA_API_KEY='your-key-here'"
echo "  2. python3 generate_scripts.py"
echo "  3. python3 generate_thumbnails.py"
echo ""
