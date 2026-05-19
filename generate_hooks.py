#!/usr/bin/env python3
"""Batch-generate hook voiceovers using gTTS (Google Text-to-Speech, free)."""

from gtts import gTTS
from pathlib import Path
import re

VOICE_DIR = Path("./voiceovers")
HOOK_DIR = VOICE_DIR / "hooks"

def find_hook(text_path: Path) -> str:
    raw = text_path.read_text(encoding="utf-8").strip()
    # Look for a "Hook" header and grab the paragraph after it
    m = re.search(r'(?i)Hook.*?\n(.+?)(?=\n\n|$)', raw, re.DOTALL)
    if m:
        hook = m.group(1).strip()
        if hook:
            return hook
    # Fallback: return first paragraph if no explicit hook header
    return raw.split('\n\n')[0].strip()

def generate_hook_audio(idx: str, text: str, out_path: Path):
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(str(out_path))
    duration_est = len(text.split()) / 150 * 60  # ~150 wpm
    print(f"  [{idx}] {out_path.name} — {len(text.split())} words, ~{duration_est:.0f}s")

def main():
    txt_files = sorted(VOICE_DIR.glob("*_voiceover.txt"))
    if not txt_files:
        print(f"No voiceover files found in {VOICE_DIR}")
        return

    HOOK_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Batch generating {len(txt_files)} hook audio files via gTTS...")
    print("=" * 60)

    for txt in txt_files:
        idx_match = re.match(r'^(\d+)_', txt.name)
        idx = idx_match.group(1) if idx_match else "XX"
        hook_text = find_hook(txt)
        if not hook_text:
            print(f"  [{idx}] No hook found — skipping {txt.name}")
            continue
        out_name = f"hook_{idx}.mp3"
        out_path = HOOK_DIR / out_name
        if out_path.exists():
            print(f"  [{idx}] Already exists — skipping {out_name}")
            continue
        generate_hook_audio(idx, hook_text, out_path)

    print("=" * 60)
    print(f"Done. All hook MP3s saved to {HOOK_DIR.absolute()}")
    print("\nNext: import these into DaVinci Resolve or CapCut as your video hooks.")

if __name__ == "__main__":
    main()
