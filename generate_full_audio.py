#!/usr/bin/env python3
"""Batch-generate FULL audio for all voiceover scripts using edge-tts (Microsoft Neural).
Falls back to macOS 'say' if edge-tts fails."""

import asyncio
import os
import re
import subprocess
from pathlib import Path

# Try edge-tts first, fallback to say
USE_EDGE = False
EDGE_PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/numerai/bin/python"
try:
    from edge_tts import Communicate
    USE_EDGE = True
except ImportError:
    print("[WARN] edge-tts not found, falling back to macOS 'say'")

VOICE_DIR = Path("./voiceovers")
FULL_DIR = VOICE_DIR / "full"
FULL_DIR.mkdir(parents=True, exist_ok=True)

# Edge voice config — GuyNeural is a confident, clear male voice
EDGE_VOICE = "en-US-GuyNeural"
EDGE_RATE = "+15%"  # Slightly faster for energy

# macOS 'say' voice (optional: change to "Samantha" for female)
SAY_VOICE = "Tom"


def chunk_text(text: str, max_chars: int = 3900) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current += " " + s if current else s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks


async def generate_edge(idx: str, text: str, out_path: Path) -> bool:
    """Generate MP3 via edge-tts."""
    try:
        communicate = Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
        await communicate.save(str(out_path))
        return True
    except Exception as e:
        print(f"    [WARN] edge-tts failed: {e}")
        return False


def generate_say(idx: str, text: str, out_path: Path) -> bool:
    """Fallback: macOS builtin TTS."""
    aiff_path = out_path.with_suffix(".aiff")
    try:
        subprocess.run(
            ["say", "-v", SAY_VOICE, "-o", str(aiff_path)],
            input=text.encode(), capture_output=True, timeout=120
        )
        # Convert to mp3
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff_path), "-c:a", "libmp3lame", "-q:a", "2", str(out_path)],
            capture_output=True, timeout=60
        )
        aiff_path.unlink(missing_ok=True)
        return out_path.exists()
    except Exception as e:
        print(f"    [WARN] say failed: {e}")
        return False


def generate_audio(idx: str, text: str, out_dir: Path) -> Path | None:
    """Generate final merged MP3 for a given text."""
    chunks = chunk_text(text, max_chars=3900)
    part_paths = []
    for i, chunk in enumerate(chunks, 1):
        part_path = out_dir / f"full_{idx}_part{i}.mp3"
        if not part_path.exists():
            print(f"    [{idx}] Part {i}/{len(chunks)} ({len(chunk)} chars)...")
            ok = False
            if USE_EDGE:
                ok = asyncio.get_event_loop().run_until_complete(
                    generate_edge(idx, chunk, part_path)
                )
            if not ok:
                ok = generate_say(idx, chunk, part_path)
            if not ok:
                print(f"    [FAIL] Could not generate part {i}")
                return None
        part_paths.append(part_path)

    # Merge parts if needed
    final_path = out_dir / f"full_{idx}.mp3"
    if final_path.exists():
        print(f"    [{idx}] Final already exists, skipping merge.")
        return final_path

    if len(part_paths) == 1:
        part_paths[0].replace(final_path)
    else:
        list_path = final_path.with_suffix(".txt")
        with list_path.open("w") as f:
            for p in part_paths:
                f.write(f"file '{p.resolve()}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_path), "-c", "copy", str(final_path)],
            capture_output=True, timeout=60
        )
        list_path.unlink(missing_ok=True)
        # Optionally clean up part files: for p in part_paths: p.unlink(missing_ok=True)

    print(f"    [DONE] {final_path.name}")
    return final_path


def post_process_speed(path: Path, speed: float = 1.25) -> Path:
    """Use atempo filter to speed up slightly without pitch shift."""
    temp = path.with_suffix(".tmp.mp3")
    # atempo range supported: 0.5 to 2.0; chain multiple for bigger changes
    atempo = f"atempo={speed}"
    cmd = [
        "ffmpeg", "-y", "-i", str(path), "-filter:a", atempo,
        "-c:a", "libmp3lame", "-q:a", "2", str(temp)
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
        temp.replace(path)
    except FileNotFoundError:
        pass
    return path


def main():
    txt_files = sorted(VOICE_DIR.glob("*_voiceover.txt"))
    if not txt_files:
        print(f"No voiceover files found in {VOICE_DIR}")
        return

    print(f"Generating FULL audio for {len(txt_files)} scripts...")
    print(f"Engine: {'edge-tts/' + EDGE_VOICE if USE_EDGE else 'macOS say/' + SAY_VOICE}")
    print("=" * 60)

    for txt in txt_files:
        idx_match = re.match(r'^(\d+)_', txt.name)
        idx = idx_match.group(1) if idx_match else "XX"
        text = txt.read_text(encoding="utf-8").strip()

        final_path = FULL_DIR / f"full_{idx}.mp3"
        if final_path.exists():
            print(f"[{idx}] {final_path.name} already exists, skip. (rm to regenerate)")
            continue

        print(f"[{idx}] {txt.name} ({len(text)} chars)")
        generate_audio(idx, text, FULL_DIR)

    print("=" * 60)
    print(f"Done. Full audio saved to {FULL_DIR.absolute()}")


if __name__ == "__main__":
    main()
