
#!/usr/bin/env python3

import os
import re
import sys
import wave
import subprocess
from pathlib import Path

sys.path.insert(0, "/content/Orpheus-TTS/orpheus_tts_pypi")

from orpheus_tts import OrpheusModel
import torch

SCRIPT_DIR = Path("./scripts")
HOOK_DIR = Path("./voiceovers_AI/hooks")
HOOK_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = os.getenv("ORPHEUS_MODEL_NAME", "/content/orpheus_lora_merged")
VOICE = os.getenv("ORPHEUS_VOICE", "tara")

def extract_hook(md_text: str) -> str:
    """
    Extract text under:
    ## Hook (0:00–0:30)
    until the next ## heading.
    """
    m = re.search(
        r"##\s*Hook[^\n]*\n(?P<hook>.*?)(?=\n##\s+|\Z)",
        md_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""

    hook = m.group("hook").strip()

    # Basic Markdown cleanup
    hook = re.sub(r"\*\*|__", "", hook)
    hook = re.sub(r"\*|_", "", hook)
    hook = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", hook)
    hook = re.sub(r"https?://\S+", "", hook)
    hook = re.sub(r"\s+", " ", hook).strip()

    return hook

def write_wav(path: Path, audio_chunks):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)

        for audio_chunk in audio_chunks:
            wf.writeframes(audio_chunk)

def wav_to_mp3(wav_path: Path, mp3_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1000:])

def main():
    md_files = sorted(SCRIPT_DIR.glob("*.md"))

    if not md_files:
        print(f"No .md files found in {SCRIPT_DIR.resolve()}")
        return

    print(f"Loading Orpheus model: {MODEL_NAME}")

    model = OrpheusModel(
        model_name=MODEL_NAME,
        tokenizer=MODEL_NAME,
        dtype=torch.float16,
        max_model_len=1024,
        enable_chunked_prefill=False,
    )

    print(f"Found {len(md_files)} scripts.")
    print(f"Using voice: {VOICE}")
    print("=" * 70)

    for md in md_files:
        idx_match = re.match(r"^(\d+)_", md.name)
        idx = idx_match.group(1).zfill(2) if idx_match else md.stem[:2]

        out_mp3 = HOOK_DIR / f"hook_{idx}.mp3"
        out_wav = HOOK_DIR / f"hook_{idx}.wav"

        if out_mp3.exists():
            print(f"[{idx}] {out_mp3.name} exists, skipping.")
            continue

        text = md.read_text(encoding="utf-8")
        hook = extract_hook(text)

        if not hook:
            print(f"[{idx}] No hook found in {md.name}, skipping.")
            continue

        print(f"[{idx}] Generating hook from {md.name}")
        print(f"     {hook[:180]}{'...' if len(hook) > 180 else ''}")

        audio_chunks = model.generate_speech(
            prompt=hook,
            voice=VOICE,
        )

        write_wav(out_wav, audio_chunks)
        wav_to_mp3(out_wav, out_mp3)

        out_wav.unlink(missing_ok=True)

        print(f"     done: {out_mp3}")

    print("=" * 70)
    print(f"Hook MP3s saved to: {HOOK_DIR.resolve()}")

if __name__ == "__main__":
    main()
