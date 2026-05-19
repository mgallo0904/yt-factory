#!/usr/bin/env python3
"""
generate_captions.py
Batch-transcribe all full narration MP3s using OpenAI Whisper (free, local).
Outputs SRT caption files for direct import into DaVinci Resolve or YouTube.

Saves to: assets/captions/video_XX.srt
"""

import whisper
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
FULL_DIR = BASE / "voiceovers" / "full"
OUT_DIR = BASE / "assets" / "captions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def transcribe_to_srt(audio_path: Path, out_path: Path) -> None:
    print(f"  Transcribing {audio_path.name} ...")
    model = whisper.load_model("base")  # tiny/base/small — base is fast + accurate for English
    result = model.transcribe(str(audio_path), verbose=False, language="en")

    segments = result.get("segments", [])
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seconds_to_srt_time(seg["start"])
        end = seconds_to_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"    -> saved {out_path.name} ({len(segments)} segments)")

def main():
    mp3_files = sorted(FULL_DIR.glob("full_*.mp3"))
    if not mp3_files:
        print("No full_*.mp3 files found in", FULL_DIR)
        sys.exit(1)

    print(f"Generating captions for {len(mp3_files)} videos ...\n")

    for mp3 in mp3_files:
        idx = mp3.stem.split("_")[-1]  # "01" from "full_01"
        slug = f"video_{idx.zfill(2)}"
        out_path = OUT_DIR / f"{slug}.srt"
        if out_path.exists():
            print(f"[{slug}] already exists, skipping.")
            continue
        print(f"[{slug}]")
        try:
            transcribe_to_srt(mp3, out_path)
        except Exception as e:
            print(f"  ! FAILED: {e}")

    print(f"\nDone. Captions saved to: {OUT_DIR}")

if __name__ == "__main__":
    main()
