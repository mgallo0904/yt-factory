#!/usr/bin/env python3
"""Improved b-roll downloader using story-relevant queries per script section.
Reads script content to extract tool names and concepts, maps them to targeted search queries."""

import json
import re
import subprocess
from pathlib import Path

OUTPUT = Path("./assets/stock")
OUTPUT.mkdir(parents=True, exist_ok=True)
META_DIR = Path("./scripts")

PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/numerai/bin/python"
MAX_PER_TOPIC = 4


def extract_tool_names(script_text: str) -> list[str]:
    """Pull actual product/tool names mentioned in the script."""
    tools = []
    # Match patterns like "Microsoft Copilot", "Reclaim.ai", "Notion AI"
    pattern = r'([A-Z][a-z]+(?:\s+)?(?:AI|\.ai|[A-Z][a-zA-Z]*))'
    found = re.findall(pattern, script_text)
    for f in found:
        clean = f.strip().replace(' ', '_')
        if clean and len(clean) > 2 and clean not in tools:
            tools.append(clean)
    return tools[:6]


def extract_scene_keywords(script_text: str) -> list[str]:
    """Pull visual scene keywords from narration."""
    keywords = []

    # Common video-friendly scenes mentioned in scripts
    scene_phrases = {
        'email inbox': 'email inbox notification laptop',
        'calendar': 'calendar schedule planner screen',
        'zoom call': 'video call laptop person talking',
        'coffee': 'typing laptop morning coffee desk',
        'late night': 'late night laptop screen dark desk',
        'meeting': 'business meeting video call laptop',
        'phone buzz': 'smartphone notification messages',
        'research': 'person researching laptop screen data',
        'editing': 'video editing screen timeline',
        'automating': 'automation workflow screen typing',
        'brain': 'brain network connections digital',
        'notes': 'digital notes writing laptop',
        'deadline': 'urgent deadline clock stressed',
        'productivity': 'focused person working laptop desk',
        'money': 'money cash dollar savings',
    }

    lower = script_text.lower()
    for phrase, query in scene_phrases.items():
        if phrase in lower and query not in keywords:
            keywords.append(query)
    return keywords[:4]


def build_queries_for_script(meta_path: Path) -> list[str]:
    """Given a script meta file, find the matching .md and return search queries."""
    # meta file is like 01_meta.json, find 01_*.md
    idx_match = re.match(r'^(\d+)_', meta_path.name)
    if not idx_match:
        return []
    prefix = idx_match.group(1)
    md_files = list(META_DIR.glob(f"{prefix}_*.md"))
    if not md_files:
        return []
    md_path = md_files[0]

    text = md_path.read_text(encoding='utf-8', errors='ignore')

    # Extract speaking parts only (skip metadata)
    lines = text.split('\n')
    speaking = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^(metadata|timestamps|links|tags|description|pinned)', stripped, re.I):
            skip = True
        if skip:
            continue
        speaking.append(stripped)
    narration = ' '.join(speaking)

    # Build targeted queries
    queries = extract_scene_keywords(narration)

    # Add a generic fallback if too few
    if len(queries) < 3:
        queries.append('person working laptop technology screen')

    return queries


def download_topic(idx: str, queries: list[str]):
    topic_dir = OUTPUT / f"video_{idx}"
    topic_dir.mkdir(parents=True, exist_ok=True)

    # Check if we already have clips
    existing = list(topic_dir.glob("*.mp4"))
    if len(existing) >= MAX_PER_TOPIC:
        print(f"[{idx}] Already has {len(existing)} clips, skip.")
        return

    print(f"\n[{idx}] Queries: {queries}")

    downloaded = 0
    for q in queries:
        if downloaded >= MAX_PER_TOPIC:
            break
        cmd = [
            PYTHON, "-m", "yt_dlp",
            "--default-search", "ytsearch8",
            "--match-filter", "duration < 90",
            "--format", "best[height<=1080]",
            "--max-downloads", str(MAX_PER_TOPIC - downloaded),
            "--output", f"{topic_dir}/clip_%(autonumber)02d_%(id)s.%(ext)s",
            "--quiet", "--no-warnings",
            q
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            # Count how many new files appeared
            new_count = len(list(topic_dir.glob("*.mp4")))
            downloaded = new_count - len(existing)
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {q}")

    new_files = list(topic_dir.glob("*.mp4"))
    print(f"  [OK] {len(new_files)} clip(s)")


def main():
    meta_files = sorted(META_DIR.glob("*_meta.json"))
    print(f"=" * 60)
    print(f"Stock Downloader (story-relevant queries)")
    print(f"=" * 60)

    for mf in meta_files:
        idx_match = re.match(r'^(\d+)_', mf.name)
        idx = idx_match.group(1).zfill(2) if idx_match else "XX"
        queries = build_queries_for_script(mf)
        if queries:
            download_topic(idx, queries)
        else:
            print(f"[{idx}] No queries generated.")

    print("\n" + "=" * 60)
    print(f"Done. Stock saved to {OUTPUT.absolute()}")


if __name__ == "__main__":
    main()
