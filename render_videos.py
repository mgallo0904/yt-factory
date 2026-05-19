#!/usr/bin/env python3
"""
render_videos.py
Headless ffmpeg renderer. Builds final 1080p MP4s from b-roll + narration.
NO subtitle burning — SRT captions are uploaded separately to YouTube (toggleable).

Output: assets/final/video_XX.mp4
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
STOCK_DIR = BASE / "assets" / "stock"
NORM_DIR = BASE / "assets" / "stock_norm"
FULL_DIR = BASE / "voiceovers" / "full"
META_DIR = BASE / "scripts"
OUT_DIR = BASE / "assets" / "final"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = "/usr/local/bin/ffmpeg"
FFPROBE = "/usr/local/bin/ffprobe"


def probe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def normalized_path(raw: Path, slug: str) -> Path:
    return NORM_DIR / slug / raw.name


def normalize_clip(raw: Path, slug: str) -> Path:
    out = normalized_path(raw, slug)
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-threads", "2",
        "-i", str(raw),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p",
        "-c:v", "h264_videotoolbox", "-allow_sw", "0",
        "-b:v", "10000k", "-maxrate", "12000k", "-bufsize", "24000k",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-an",  # strip audio, we'll use narration
        str(out)
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return out if out.exists() else raw


def build_concat_list(stock_clips: list[Path], target_dur: float, list_path: Path) -> None:
    total = 0.0
    lines = []
    clips = [c for c in stock_clips if c.exists()]
    if not clips:
        return
    idx = 0
    while total < target_dur:
        clip = clips[idx % len(clips)]
        dur = probe_duration(clip)
        if dur <= 0:
            idx += 1
            continue
        if total + dur > target_dur + 1.0 and total > 0:
            break
        lines.append(f"file '{clip}'")
        lines.append(f"duration {dur}")
        total += dur
        idx += 1
    lines.append(f"file '{clips[(idx - 1) % len(clips)]}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")


def render_video(slug: str, stock_clips: list[Path], full_audio: Path) -> Path:
    out_path = OUT_DIR / f"{slug}.mp4"
    if out_path.exists():
        print(f"  {out_path.name} already exists, skipping.")
        return out_path

    target_dur = probe_duration(full_audio)
    if target_dur <= 0:
        print(f"  ! Cannot probe duration for {full_audio}")
        return None

    # normalize each stock clip to 1080p 30fps yuv420p once (cached)
    norm_clips = [normalize_clip(c, slug) for c in stock_clips]
    norm_clips = [c for c in norm_clips if c.exists()]
    if not norm_clips:
        print(f"  ! No valid stock clips for {slug}")
        return None

    temp_dir = OUT_DIR / ".tmp" / slug
    temp_dir.mkdir(parents=True, exist_ok=True)
    concat_file = temp_dir / "concat.txt"

    build_concat_list(norm_clips, target_dur, concat_file)
    if not concat_file.exists() or concat_file.stat().st_size == 0:
        print(f"  ! No valid stock clips for {slug}")
        return None

    cmd = [
        FFMPEG, "-y",
        "-threads", "2",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(full_audio),
        "-c:v", "copy",                 # zero re-encode: clips already uniform
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(out_path)
    ]

    print(f"  Rendering {slug} (~{target_dur:.0f}s) ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            print(f"  ! ffmpeg failed: {result.stderr[-600:]}")
            return None
        print(f"  -> saved {out_path.name}")
        return out_path
    except subprocess.TimeoutExpired:
        print(f"  ! ffmpeg timeout for {slug}")
        return None


def slug_from_filename(name: str) -> str:
    """Extract video_XX slug from meta JSON filename."""
    # Match leading number like 01_ or video_01_
    m = re.match(r"^(\d+)_", name)
    if m:
        return f"video_{m.group(1).zfill(2)}"
    m = re.match(r"^(\d+)", name)
    return f"video_{m.group(1).zfill(2)}" if m else name.replace("_meta.json", "")


def main():
    meta_files = sorted(META_DIR.glob("*_meta.json"))
    if not meta_files:
        print("No meta files found.")
        sys.exit(1)

    print(f"Rendering {len(meta_files)} videos ...\n")

    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        print(f"[{slug}]")

        idx = slug.split("_")[-1]
        full_audio = FULL_DIR / f"full_{idx.zfill(2)}.mp3"
        stock_dir = STOCK_DIR / slug
        stock_clips = sorted(stock_dir.glob("*.mp4")) if stock_dir.exists() else []

        if not full_audio.exists():
            print(f"  ! Missing audio: {full_audio}")
            continue
        if not stock_clips:
            print(f"  ! No stock clips in {stock_dir}")
            continue

        render_video(slug, stock_clips, full_audio)

    print(f"\nDone. Final videos saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
