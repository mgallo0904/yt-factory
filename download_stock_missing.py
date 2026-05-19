#!/usr/bin/env python3
"""
download_stock_missing.py
Targeted broader-search stock footage downloader for the 6 missing topics.
Uses yt_dlp Python module directly (no PATH issues).
"""

import os, sys, subprocess, textwrap, json
from pathlib import Path

BASE = Path(__file__).parent.resolve()
ASSETS = BASE / "assets" / "stock"
ASSETS.mkdir(parents=True, exist_ok=True)

# Broader search queries mapped to missing video folders
BROAD_SEARCHES = {
    "video_03": [
        "artificial intelligence robot futuristic technology dark",
        "cyberpunk city neon night future technology",
        "digital brain neural network abstract dark background",
        "AI surveillance camera security technology dystopia",
        "exhausted burnout office worker computer screen late night",
    ],
    "video_05": [
        "laptop screen typing code software developer",
        "multiple computer monitors setup tech workspace",
        "smartphone app interface scrolling social media",
        "technology comparison chart graph data analysis",
        "robot hand human hand shaking AI collaboration",
    ],
    "video_07": [
        "person studying books library knowledge learning",
        "stopwatch timer clock time lapse productivity",
        "notebook pen writing goals planner organized",
        "speed motion fast forward city rush busy",
        "meditation calm peaceful nature focus mindfulness",
    ],
    "video_08": [
        "30 days calendar month time lapse sunset",
        "experiment science lab test tubes innovation",
        "before after transformation fitness progress",
        "challenge achievement success winner celebration",
        "daily routine morning coffee sunrise laptop",
    ],
    "video_09": [
        "content creator filming camera behind the scenes",
        "video editing timeline software screen recording",
        "social media icons floating digital marketing",
        "automation gears machine factory conveyor belt",
        "upload progress bar cloud computing data transfer",
    ],
    "video_10": [
        "data center server room rows lights blinking",
        "cloud computing sky clouds technology abstract",
        "home office desk computer local workspace",
        "money cash dollar bills cost expense counting",
        "hardware circuit board chip microprocessor close up",
    ],
}

PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/numerai/bin/python"

def run_ytdlp_search(query: str, outdir: Path, idx: int) -> bool:
    """Run yt-dlp via Python module to search and download one clip."""
    outtmpl = str(outdir / f"clip_{idx:02d}_%(id)s.%(ext)s")
    cmd = [
        PYTHON, "-m", "yt_dlp",
        "--default-search", "ytsearch",
        "--playlist-end", "1",
        "--format", "best[ext=mp4]/best",
        "--max-filesize", "50M",
        "--no-playlist",
        "--output", outtmpl,
        "--quiet",
        "--no-warnings",
        f"ytsearch1:{query}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and "ERROR" not in result.stderr
    except Exception as e:
        print(f"    ! Error: {e}")
        return False


def main():
    for folder, queries in BROAD_SEARCHES.items():
        outdir = ASSETS / folder
        outdir.mkdir(parents=True, exist_ok=True)
        existing = list(outdir.glob("*.mp4"))
        if existing:
            print(f"[{folder}] already has {len(existing)} clips, skipping.")
            continue

        print(f"\n[{folder}] searching {len(queries)} broad queries ...")
        downloaded = 0
        for i, q in enumerate(queries, 1):
            if downloaded >= 3:
                break
            print(f"  Query {i}: {q}")
            if run_ytdlp_search(q, outdir, downloaded + 1):
                downloaded += 1
                print(f"    -> downloaded clip {downloaded}")
            else:
                print(f"    -> no result")

        if downloaded == 0:
            print(f"  ! ALL QUERIES FAILED for {folder}")
        else:
            print(f"  Done: {downloaded} clip(s) in {outdir}")

    print("\nAll missing topics processed.")


if __name__ == "__main__":
    main()
