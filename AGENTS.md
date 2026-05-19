<!-- Generated: 2026-05-19 | Updated: 2026-05-19 -->

# yt_factory

## Purpose
A faceless YouTube channel content factory that automates the end-to-end pipeline for producing AI-tools-and-productivity niche videos. The project includes Python scripts and shell helpers for generating video scripts, thumbnail concepts, voiceover text, and downloading stock footage. This is a work-in-progress project; not all pipeline stages are fully completed.

## Key Files

| File | Description |
|------|-------------|
| `setup.sh` | One-click setup script: installs ffmpeg, imagemagick, yt-dlp, Python deps, and pulls the Ollama model |
| `.env` | Environment variables (API keys, Ollama config) |
| `generate_scripts.py` | Batch-generates video scripts + metadata via Ollama OpenAI-compatible endpoint |
| `generate_thumbnails.py` | Generates high-CTR titles and thumbnail text overlays via Ollama |
| `generate_thumbnails_images.py` | Creates thumbnail image assets using image generation or overlays |
| `generate_thumbnails_pillow.py` | Pillow-based thumbnail image rendering and text overlay |
| `vision_analyze_thumb.py` | AI vision review of generated thumbnails for quality/CTR feedback |
| `generate_full_audio.py` | Converts full video scripts into voiceover audio |
| `generate_hooks.py` | Generates short hook audio clips for video intros |
| `prep_voiceover.py` | Prepares voiceover text files for TTS/audio generation |
| `download_stock.py` | Auto-downloads free stock footage from Coverr/Pexels per video topic |
| `download_stock_batch.py` | Batch version of stock footage downloader |
| `download_stock_yt.sh` | Shell-based stock footage downloader using yt-dlp |
| `generate_missing.py` | Identifies and regenerates missing pipeline outputs |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Generated video scripts and metadata per video (see `scripts/AGENTS.md`) |
| `assets/` | Media assets: stock footage and thumbnails (see `assets/AGENTS.md`) |
| `voiceovers/` | Generated voiceover text, hook audio, and full audio files (see `voiceovers/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- All scripts are Python 3 with standard library + requests, Pillow, and openai-whisper
- The project uses an Ollama-compatible endpoint (model: kimi-k2.6:cloud) for LLM calls
- Environment variables are loaded from `.env`; do not commit secrets
- Generated outputs go into `scripts/`, `assets/`, and `voiceovers/` — preserve existing content when regenerating

### Testing Requirements
- Run `python3 <script> --help` or inspect the `if __name__ == "__main__"` block to verify script behavior
- Validate that `.env` contains required keys before running API-dependent scripts
- Check that `scripts/` and `assets/stock/` directories exist before running generators

### Common Patterns
- Each script is standalone and can be run independently
- File naming convention: `<index>_<sanitized_topic>.<ext>`
- Scripts use `pathlib.Path` for cross-platform path handling
- API calls include retry logic with `time.sleep` for rate limiting

## Dependencies

### Internal
- `scripts/` — scripts read/write markdown scripts and JSON metadata here
- `assets/stock/` — download scripts save footage here
- `assets/thumbnails/` — thumbnail generators save images here
- `voiceovers/` — audio generators save TTS outputs here

### External
- `requests` — HTTP client for Ollama and stock footage APIs
- `Pillow` — Image manipulation for thumbnail generation
- `openai-whisper` — Audio transcription and voiceover processing
- `ffmpeg` — Video/audio processing (installed via setup.sh)
- `imagemagick` — Image conversion and manipulation
- `yt-dlp` — YouTube video downloader for stock footage
- Ollama endpoint at `https://ollama.com/v1/chat/completions`

<!-- MANUAL: Project is incomplete; additional pipeline stages (video assembly, upload) may be added later. -->