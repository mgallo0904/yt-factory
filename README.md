# yt-factory

End-to-end automation pipeline for a faceless YouTube channel in the AI-tools-and-productivity niche.

## What it does

1. **Scripts** (`generate_scripts.py`) — Batch-generates video scripts and metadata via LLM
2. **Voice** (`prep_voiceover.py` → `generate_full_audio.py`) — Converts scripts to natural-soundingTTS (edge-tts/Microsoft neural voices)
3. **Stock** (`download_stock_batch.py`) — Downloads story-relevant B-roll from free sources
4. **Thumbnails** (`generate_thumbnails_images.py`) — Generates clean dark-theme thumbnails with typography
5. **Render** (`render_videos.py`) — Assembles final 1080p MP4s with hardware-accelerated encoding
6. **Upload** (`upload_to_youtube.py`) — Publishes to YouTube with captions

## Quick Start

```bash
# Clone
git clone https://github.com/mgallo0904/yt-factory.git
cd yt-factory

# Setup (NOT python3 setup.sh — it's a bash script)
bash setup.sh

# Or if you prefer manual:
pip install -r requirements.txt
mkdir -p assets/stock assets/final assets/thumbnails voiceovers/full voiceovers/hooks

# Create your .env from the template
cp .env.example .env
# Edit .env with your API keys

# Run the pipeline
python3 generate_scripts.py        # 1. Generate scripts
python3 prep_voiceover.py          # 2. Clean text for TTS
python3 generate_full_audio.py     # 3. Neural voiceover
python3 download_stock_batch.py    # 4. Download b-roll
python3 generate_thumbnails_images.py  # 5. Thumbnails
python3 render_videos.py           # 6. Final 1080p MP4s
```

## Requirements

- Python 3.11+
- ffmpeg
- imagemagick
- macOS recommended (for `say` fallback and VideoToolbox hardware encoding)

## What's in the repo

| File / Dir | Purpose |
|---|---|
| `scripts/*.md` | Generated video scripts |
| `scripts/*_meta.json` | Script metadata (titles, hooks, timestamps) |
| `setup.sh` | One-click dependency installer |
| `requirements.txt` | Python packages |
| `generate_*.py` | Pipeline scripts |
| `assets/` | Output directory for stock, final videos, thumbnails, captions |
| `voiceovers/` | Output directory for TTS audio |

## What's gitignored

All generated media is excluded from git — `assets/stock/`, `assets/final/`, `assets/thumbnails/`,
`voiceovers/*.mp3`, `voiceovers/*.txt`, `assets/captions/`, `assets/timelines/`.
Only source code and original scripts are committed.
