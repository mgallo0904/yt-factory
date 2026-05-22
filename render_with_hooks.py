#!/usr/bin/env python3
"""
render_with_hooks.py
Concatenate hook audio + full narration audio, then build final 1080p MP4s.

Prerequisite: place hook_NN.mp3 files in HOOKS_DIR (your Orpheus LoRA output).
          full_NN.mp3 files are taken from FULL_DIR.

Uses ffmpeg concat demuxer for gapless audio joining.
"""

from pathlib import Path
import subprocess
import sys
import re

BASE = Path(__file__).parent.resolve()
HOOKS_DIR = BASE / "voiceovers_AI" / "hooks"
FULL_DIR = BASE / "voiceovers_AI" / "full"
COMBINED_DIR = BASE / "voiceovers_AI" / "combined"
STOCK_DIR = BASE / "assets" / "stock"
NORM_DIR = BASE / "assets" / "stock_norm"
OUT_DIR = BASE / "assets" / "final"
META_DIR = BASE / "scripts"

FFMPEG = "/usr/bin/ffmpeg"
FFPROBE = "/usr/bin/ffprobe"

OUT_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)
COMBINED_DIR.mkdir(parents=True, exist_ok=True)


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


def normalize_clip(raw: Path, slug: str) -> Path:
    out = NORM_DIR / slug / raw.name
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-threads", "2",
        "-i", str(raw),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", "10000k", "-maxrate", "12000k", "-bufsize", "24000k",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out)
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return out if out.exists() else raw


def build_concat_list(stock_clips, target_dur, list_path):
    total = 0.0
    lines = []
    clips = [c for c in stock_clips if c.exists()]
    if not clips:
        return None
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
    if not lines:
        return None
    lines.append(f"file '{clips[(idx - 1) % len(clips)]}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")
    return total


def combine_audio(hook_mp3: Path, full_mp3: Path, out_mp3: Path) -> bool:
    """Concatenate hook then full audio using ffmpeg concat demuxer."""
    if out_mp3.exists():
        return True
    # Use concat filter for gapless joining (same codec, no re-encode needed since both MP3)
    # We decode and re-encode aac to ensure seamless stitching
    cmd = [
        FFMPEG, "-y",
        "-i", str(hook_mp3), "-i", str(full_mp3),
        "-filter_complex", "[0:a:0][1:a:0]concat=n=2:v=0:a=1[outa]",
        "-map", "[outa]",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(out_mp3)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ! Audio combine failed: {result.stderr[-400:]}")
        return False
    return True


def render_video(slug: str, stock_clips, combined_audio: Path, force: bool = False):
    out_path = OUT_DIR / f"{slug}.mp4"
    if out_path.exists() and not force:
        print(f"  {out_path.name} already exists, skipping.")
        return out_path

    target_dur = probe_duration(combined_audio)
    if target_dur <= 0:
        print(f"  ! Cannot probe duration for {combined_audio}")
        return None

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
        "-i", str(combined_audio),
        "-c:v", "copy",
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
    m = re.match(r"^(\d+)", name)
    return f"video_{m.group(1).zfill(2)}" if m else name


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--hooks-dir", default=str(HOOKS_DIR), type=Path, help="Directory with hook_NN.mp3")
    ap.add_argument("--full-dir", default=str(FULL_DIR), type=Path, help="Directory with full_NN.mp3")
    ap.add_argument("--force", action="store_true", help="Overwrite final videos")
    args = ap.parse_args()

    meta_files = sorted(META_DIR.glob("*_meta.json"))
    if not meta_files:
        print("No meta files found.")
        sys.exit(1)

    any_missing = False
    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        idx = slug.split("_")[-1]
        hook_mp3 = args.hooks_dir / f"hook_{idx}.mp3"
        full_mp3 = args.full_dir / f"full_{idx}.mp3"
        combined_mp3 = COMBINED_DIR / f"combined_{idx}.mp3"

        if not hook_mp3.exists():
            print(f"[{slug}] ! Missing hook: {hook_mp3}")
            any_missing = True
            continue
        if not full_mp3.exists():
            print(f"[{slug}] ! Missing full: {full_mp3}")
            any_missing = True
            continue

    if any_missing:
        print("\nSome hook audio files are missing.")
        print("Generate them with your Orpheus LoRA and place in voiceovers/hooks/")
        print("Then run this script again.")
        sys.exit(1)

    print(f"Rendering {len(meta_files)} videos with hooks prepended...\n")

    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        print(f"[{slug}]")

        idx = slug.split("_")[-1]
        hook_mp3 = args.hooks_dir / f"hook_{idx}.mp3"
        full_mp3 = args.full_dir / f"full_{idx}.mp3"
        combined_mp3 = COMBINED_DIR / f"combined_{idx}.mp3"

        # Combine hook + full audio
        ok = combine_audio(hook_mp3, full_mp3, combined_mp3)
        if not ok:
            continue

        stock_dir = STOCK_DIR / slug
        stock_clips = sorted(stock_dir.glob("*.mp4")) if stock_dir.exists() else []
        if not stock_clips:
            print(f"  ! No stock clips in {stock_dir}")
            continue

        render_video(slug, stock_clips, combined_mp3, force=args.force)

    print(f"\nDone. Final videos saved to {OUT_DIR}")
    dur = probe_duration(list(COMBINED_DIR.glob("combined_*.mp3"))[0]) if list(COMBINED_DIR.glob("combined_*.mp3")) else 0
    print(f"Combined audio is in {COMBINED_DIR}")


if __name__ == "__main__":
    main()
