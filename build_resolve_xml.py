#!/usr/bin/env python3
"""
build_resolve_xml.py
Generates DaVinci Resolve / Final Cut Pro compatible XML timeline
for each video. Imports audio + b-roll clips at correct timestamps.

Output: assets/timelines/video_XX.fcpxml

Timeline structure per video:
  Track 1: B-roll stock clips (looped/cycled to fill duration)
  Track 2: Hook audio (first 5s)
  Track 3: Full narration (starts at 0 or after hook)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

BASE       = Path(__file__).parent.resolve()
VOICE_DIR  = BASE / "voiceovers"
HOOK_DIR   = VOICE_DIR / "hooks"
FULL_DIR   = VOICE_DIR / "full"
STOCK_DIR  = BASE / "assets" / "stock"
THUMB_DIR  = BASE / "assets" / "thumbnails"
META_DIR   = BASE / "scripts"
OUT_DIR    = BASE / "assets" / "timelines"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FFPROBE = "/usr/local/bin/ffprobe"
FPS = 24
WIDTH, HEIGHT = 1920, 1080


def get_media_duration(path: Path) -> float:
    """Get audio/video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def seconds_to_frames(sec: float) -> int:
    return int(round(sec * FPS))


def frames_to_timecode(frames: int) -> str:
    """00:00:00:00 format at 24fps."""
    total_seconds = frames / FPS
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    f = int(frames % FPS)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def build_fcpxml(slug: str, hook_path: Path, full_path: Path,
                 stock_clips: list[Path], meta: dict) -> Path:
    """Build a Final Cut Pro XML that DaVinci Resolve can import."""

    hook_dur = get_media_duration(hook_path)
    full_dur = get_media_duration(full_path)

    # Total duration = max(full narration, hook) + padding
    total_dur = max(hook_dur, full_dur) + 2.0  # 2s outro padding
    total_frames = seconds_to_frames(total_dur)

    # If no full narration, bail
    if full_dur <= 0:
        print(f"  ! No valid duration for {full_path.name}, skipping XML.")
        return None

    # ─── XML root ──────────────────────────────────────────────────
    fcpxml = Element("fcpxml", {"version": "1.9"})
    resources = SubElement(fcpxml, "resources")
    library = SubElement(fcpxml, "library")
    event = SubElement(library, "event", {"name": slug})
    project = SubElement(event, "project", {"name": slug})
    sequence = SubElement(project, "sequence",
        {"duration": f"{total_frames}/{FPS}s",
         "format": "r1",
         "tcStart": "0s",
         "tcFormat": "NDF",
         "audioLayout": "stereo",
         "audioRate": "48k"})
    spine = SubElement(sequence, "spine")

    # Video format resource
    fmt = SubElement(resources, "format",
        {"id": "r1", "name": "FFVideoFormat1080p24",
         "frameDuration": f"1/{FPS}s", "width": str(WIDTH), "height": str(HEIGHT)})

    # ─── Register stock clips as video resources ───────────────────
    stock_resources = {}
    for i, clip_path in enumerate(stock_clips):
        clip_dur = get_media_duration(clip_path)
        if clip_dur <= 0:
            continue
        rid = f"rv{i+1}"
        asset = SubElement(resources, "asset",
            {"id": rid,
             "name": clip_path.name,
             "uid": f"uid_{clip_path.stem}",
             "src": str(clip_path),
             "start": "0s",
             "duration": f"{seconds_to_frames(clip_dur)}/{FPS}s",
             "hasVideo": "1", "hasAudio": "0",
             "format": "r1"})
        stock_resources[rid] = (clip_path, clip_dur)

    # ─── Register audio resources ──────────────────────────────────
    rid_hook = "ra_hook"
    rid_full = "ra_full"
    for rid, path, dur in [(rid_hook, hook_path, hook_dur),
                            (rid_full, full_path, full_dur)]:
        if dur > 0:
            SubElement(resources, "asset",
                {"id": rid,
                 "name": path.name,
                 "uid": f"uid_{path.stem}",
                 "src": str(path),
                 "start": "0s",
                 "duration": f"{seconds_to_frames(dur)}/{FPS}s",
                 "hasVideo": "0", "hasAudio": "1"})

    # ─── Build video track: cycle stock clips to fill duration ─────
    current_frame = 0
    clip_cycle = list(stock_resources.keys())
    cycle_idx = 0

    while current_frame < total_frames and clip_cycle:
        rid = clip_cycle[cycle_idx % len(clip_cycle)]
        _, clip_dur = stock_resources[rid]
        clip_frames = seconds_to_frames(clip_dur)

        # Don't exceed total duration
        if current_frame + clip_frames > total_frames:
            clip_frames = total_frames - current_frame

        SubElement(spine, "video", {
            "name": stock_resources[rid][0].name,
            "ref": rid,
            "offset": f"{current_frame}/{FPS}s",
            "duration": f"{clip_frames}/{FPS}s",
            "start": "0s"
        })

        current_frame += clip_frames
        cycle_idx += 1

    # ─── Build audio track: full narration ─────────────────────────
    if full_dur > 0:
        SubElement(spine, "audio", {
            "name": full_path.name,
            "ref": rid_full,
            "offset": "0s",
            "duration": f"{seconds_to_frames(full_dur)}/{FPS}s",
            "start": "0s",
            "srcCh": "1,2"
        })

    # ─── Build audio track: hook (overlaps first 5s) ─────────────
    if hook_dur > 0:
        hook_frames = min(seconds_to_frames(hook_dur), 5 * FPS)
        SubElement(spine, "audio", {
            "name": hook_path.name,
            "ref": rid_hook,
            "offset": "0s",
            "duration": f"{hook_frames}/{FPS}s",
            "start": "0s",
            "srcCh": "1,2",
            "role": "dialogue"
        })

    # Pretty-print XML
    raw = tostring(fcpxml, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    # Strip blank lines
    pretty = os.linesep.join([s for s in pretty.splitlines() if s.strip()])

    out_path = OUT_DIR / f"{slug}.fcpxml"
    out_path.write_text(pretty, encoding="utf-8")
    print(f"    -> XML saved: {out_path.name} ({total_frames} frames @ {FPS}fps, ~{total_dur:.1f}s)")
    return out_path


def build_csv_manifest(slug: str, hook_path: Path, full_path: Path,
                       stock_clips: list[Path], meta: dict) -> Path:
    """Build a CSV import manifest for manual reference."""
    lines = ["type,filename,duration_seconds,notes"]

    hook_dur = get_media_duration(hook_path)
    full_dur = get_media_duration(full_path)

    lines.append(f"thumbnail,{slug}.png,-,YouTube thumbnail")
    lines.append(f"hook_audio,{hook_path.name},{hook_dur:.2f},First 5s hook")
    lines.append(f"full_audio,{full_path.name},{full_dur:.2f},Main narration")

    for clip in stock_clips:
        dur = get_media_duration(clip)
        lines.append(f"broll,{clip.name},{dur:.2f},Loop/cut to fit narration")

    lines.append(f"script,{slug}_script.md,-,Voiceover source text")
    lines.append(f"meta,{slug}_meta.json,-,Title/tags/description")

    out_path = OUT_DIR / f"{slug}_manifest.csv"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"    -> CSV saved: {out_path.name}")
    return out_path


def slug_from_filename(name: str) -> str:
    m = re.match(r"^(\d+)_", name)
    if m:
        return f"video_{m.group(1).zfill(2)}"
    m = re.match(r"^(video_\d+)", name)
    return m.group(1) if m else name.replace("_meta.json", "")


def main():
    meta_files = sorted(META_DIR.glob("*_meta.json"))
    if not meta_files:
        print("No meta files found.")
        sys.exit(1)

    print(f"Building timelines for {len(meta_files)} videos ...\n")

    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        print(f"[{slug}]")

        # Resolve paths
        idx = slug.split("_")[-1]
        hook_path = HOOK_DIR / f"hook_{idx.zfill(2)}.mp3"
        full_path = FULL_DIR / f"full_{idx.zfill(2)}.mp3"
        stock_dir = STOCK_DIR / slug
        stock_clips = sorted(stock_dir.glob("*.mp4")) if stock_dir.exists() else []

        if not full_path.exists():
            print(f"  ! Missing full audio: {full_path}")
            continue
        if not stock_clips:
            print(f"  ! No stock clips in {stock_dir}")
            continue

        meta = json.loads(mf.read_text())

        # Build both outputs
        build_fcpxml(slug, hook_path, full_path, stock_clips, meta)
        build_csv_manifest(slug, hook_path, full_path, stock_clips, meta)

    print(f"\nDone. Timelines + manifests saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
