#!/usr/bin/env python3
"""
generate_hooks_colab.py
Run this inside a Google Colab cell to restore Orpheus-TTS + your LoRA, then generate hooks.

Usage in Colab:
  !git clone https://github.com/mgallo0904/yt-factory.git /content/yt-factory
  %cd /content/yt-factory
  !python generate_hooks_colab.py --voice tara

If your yt-factory repo is already synced via Colab's GitHub integration:
  %cd /content/your-clone-path
  !python generate_hooks_colab.py --voice tara
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────
BASE_MODEL = "unsloth/orpheus-3b-0.1-ft"
LORA_REPO = "mgallo094/orpheus_lora"
MERGED_PATH = Path("/content/orpheus_lora_merged")
ORPHEUS_INSTALL = Path("/content/Orpheus-TTS")
HOOKS_OUT = Path("/content/yt-factory/voiceovers_AI/hooks")

FFMPEG_BIN = "/usr/bin/ffmpeg"
VOICE = "tara"

# ── Helpers ──────────────────────────────────────────────────────────

def run_cmd(cmd, cwd=None, timeout=300):
    print(f"  $ {' '.join(cmd[:8])}{'...' if len(cmd) > 8 else ''}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[-500:]}")
    return result.returncode == 0


def ensure_base_orpheus():
    """Clone Orpheus-TTS if not present."""
    if (ORPHEUS_INSTALL / "orpheus_tts" / "__init__.py").exists():
        print("[OK] Orpheus-TTS already present.")
        return True
    print("[STEP] Cloning Orpheus-TTS...")
    ok = run_cmd([
        "git", "clone", "https://github.com/canopyai/Orpheus-TTS.git",
        str(ORPHEUS_INSTALL)
    ], timeout=120)
    if not ok:
        print("[FAIL] Could not clone Orpheus-TTS")
        return False

    # Install in editable mode + deps
    print("[STEP] Installing Orpheus-TTS dependencies...")
    run_cmd([sys.executable, "-m", "pip", "install", "-e", str(ORPHEUS_INSTALL),
             "--quiet"], timeout=300)
    run_cmd([sys.executable, "-m", "pip", "install", "snac", "torch",
             "transformers", "accelerate", "--quiet"], timeout=300)
    return True


def merge_lora():
    """Download base model + LoRA, merge, save to /content/orpheus_lora_merged."""
    if (MERGED_PATH / "model.safetensors").exists() or (MERGED_PATH / "pytorch_model.bin").exists():
        print("[OK] Merged model already exists.")
        return True

    print("[STEP] Downloading LoRA + base model (this may take 5-10 min)...")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        import torch
    except ImportError:
        run_cmd([sys.executable, "-m", "pip", "install",
                 "transformers", "peft", "torch", "accelerate", "--quiet"],
                timeout=300)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Using device: {device}")

    print(f"[STEP] Loading base model: {BASE_MODEL}")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    print(f"[STEP] Loading LoRA: {LORA_REPO}")
    model = PeftModel.from_pretrained(model, LORA_REPO)

    print("[STEP] Merging and saving...")
    model = model.merge_and_unload()
    MERGED_PATH.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MERGED_PATH)
    tokenizer.save_pretrained(MERGED_PATH)
    print(f"[OK] Merged model saved to {MERGED_PATH}")
    return True


def generate_hooks(voice: str = VOICE):
    """Generate hook audio from voiceovers_AI/hooks/hook_NN.txt files."""
    hook_dir = Path("voiceovers_AI/hooks")
    if not hook_dir.exists():
        print(f"[FAIL] Hook text directory not found: {hook_dir}")
        print("Ensure your GitHub-synced repo has the hook text files.")
        return False

    HOOKS_OUT.mkdir(parents=True, exist_ok=True)

    # Import after ensuring Orpheus is installed
    sys.path.insert(0, str(ORPHEUS_INSTALL))
    from orpheus_tts import OrpheusModel

    print(f"[STEP] Loading merged Orpheus model from {MERGED_PATH}...")
    model = OrpheusModel(model_name=str(MERGED_PATH))

    txt_files = sorted(hook_dir.glob("hook_*.txt"))
    print(f"[INFO] Found {len(txt_files)} hook text files.")

    for txt_file in txt_files:
        idx_match = __import__('re').match(r'hook_(\d+)', txt_file.name)
        if not idx_match:
            continue
        idx = idx_match.group(1)
        hook_text = txt_file.read_text(encoding="utf-8").strip()
        if not hook_text:
            print(f"  [{idx}] Empty text — skipping")
            continue

        out_mp3 = HOOKS_OUT / f"hook_{idx}.mp3"
        out_wav = HOOKS_OUT / f"hook_{idx}.wav"

        if out_mp3.exists():
            print(f"  [{idx}] {out_mp3.name} already exists — skipping")
            continue

        print(f"  [{idx}] Generating: {hook_text[:60]}...")
        try:
            audio_segments = model.generate_speech(prompt=hook_text, voice=voice)
        except Exception as e:
            print(f"  [{idx}] generate_speech failed: {e}")
            continue

        # Write audio to WAV
        import wave
        with wave.open(str(out_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            for seg in audio_segments:
                wf.writeframes(seg)

        # Convert to MP3 via ffmpeg
        if Path(FFMPEG_BIN).exists():
            subprocess.run([
                FFMPEG_BIN, "-y", "-i", str(out_wav),
                "-codec:a", "libmp3lame", "-q:a", "4",
                str(out_mp3)
            ], capture_output=True, timeout=60)
        else:
            # fallback: just keep WAV if no ffmpeg
            out_wav.rename(out_mp3)

        if out_mp3.exists():
            print(f"  [{idx}] -> {out_mp3.name}")
        else:
            print(f"  [{idx}] output missing")

    print(f"\n[OK] Done. Hook files saved to: {HOOKS_OUT}")
    print(f"     Sync back to your repo with:")
    print(f"       %cd /content/yt-factory && git add voiceovers_AI/hooks/*.mp3")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default=VOICE, help="Voice name (tara, leah, etc.)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Orpheus LoRA Hook Generator (Colab)")
    print("=" * 60)

    if not ensure_base_orpheus():
        sys.exit(1)
    if not merge_lora():
        sys.exit(1)
    generate_hooks(voice=args.voice)

    print("\n✅ Next step: run `render_with_hooks.py --force` to rebuild final videos")


if __name__ == "__main__":
    main()
