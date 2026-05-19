#!/usr/bin/env python3
"""
Auto-download free stock footage for each video topic.
Tries Coverr (no API key needed), then Pexels (API key optional).
Saves to ./assets/stock/ organized by video number.
"""

import os
import re
import json
import time
import requests
from pathlib import Path
from urllib.parse import quote_plus

OUTPUT_DIR = Path("./assets/stock")
MAX_PER_TOPIC = 5
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# Map each video to search queries
TOPICS = {
    "01": ["artificial intelligence technology futuristic", "AI tools digital workspace"],
    "02": ["laptop computer software open source", "app icons screen close up"],
    "03": ["dark technology cyberpunk moody", "shadowy figure computer screen"],
    "04": ["automation robot hands typing", "workflow efficiency time lapse"],
    "05": ["artificial intelligence brain neural", "chatbot interface comparison"],
    "06": ["brain neurons knowledge network", "digital notes connections glowing"],
    "07": ["time management clock productivity", "businessman working focused desk"],
    "08": ["artificial intelligence experiment", "person testing technology lab"],
    "09": ["content creation camera filming", "video editing screen timeline"],
    "10": ["server cloud computing data center", "local computer vs cloud"],
}

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

def sanitize(filename: str) -> str:
    return re.sub(r'[^\w\-_.]', '_', filename)[:60]

def download_file(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    [DL FAIL] {e}")
        return False

def fetch_pexels(query: str, count: int = 5) -> list[dict]:
    if not PEXELS_API_KEY:
        return []
    url = f"https://api.pexels.com/videos/search?query={quote_plus(query)}&per_page={count}&orientation=landscape"
    try:
        r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("videos", [])
        results = []
        for v in data:
            files = v.get("video_files", [])
            # Pick HD or SD file
            best = None
            for f in files:
                if f.get("quality") in ("hd", "sd"):
                    best = f
                    break
            if not best and files:
                best = files[0]
            if best:
                results.append({
                    "url": best["link"],
                    "width": best.get("width", 0),
                    "height": best.get("height", 0),
                    "duration": v.get("duration", 0),
                    "source": "pexels"
                })
        return results
    except Exception as e:
        print(f"    [Pexels error] {e}")
        return []

def fetch_coverr(query: str, count: int = 5) -> list[dict]:
    """Scrape Coverr search page for free video links."""
    url = f"https://coverr.co/s?q={quote_plus(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text
        # Extract video page URLs from search results
        links = re.findall(r'href="(/v/[^"]+)"', html)
        results = []
        for link in links[:count]:
            video_url = f"https://coverr.co{link}"
            try:
                v = requests.get(video_url, headers=HEADERS, timeout=TIMEOUT)
                v_html = v.text
                # Try to find direct MP4 link in the page
                mp4_match = re.search(r'(https://[^\'"\s]+\.mp4)', v_html)
                if mp4_match:
                    results.append({
                        "url": mp4_match.group(1),
                        "width": 1920,
                        "height": 1080,
                        "duration": 0,
                        "source": "coverr"
                    })
            except Exception:
                continue
        return results
    except Exception as e:
        print(f"    [Coverr error] {e}")
        return []

def fallback_search_links(idx: str, queries: list[str]) -> str:
    """Generate manual search URLs if auto-download fails."""
    lines = [f"\n[{idx}] Manual stock footage search links:"]
    for q in queries:
        lines.append(f"  Pexels:    https://www.pexels.com/search/videos/{quote_plus(q)}/")
        lines.append(f"  Pixabay:   https://pixabay.com/videos/search/{quote_plus(q)}/")
        lines.append(f"  Coverr:    https://coverr.co/s?q={quote_plus(q)}")
    return "\n".join(lines)

def download_topic(idx: str, queries: list[str]):
    topic_dir = OUTPUT_DIR / f"video_{idx}"
    topic_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[{idx}] Searching stock footage for: {queries}")

    all_videos = []

    # Try Pexels first if key available
    if PEXELS_API_KEY:
        for q in queries:
            vids = fetch_pexels(q, count=3)
            all_videos.extend(vids)
            if len(all_videos) >= MAX_PER_TOPIC:
                break

    # Fallback to Coverr scraping
    if len(all_videos) < MAX_PER_TOPIC:
        for q in queries:
            vids = fetch_coverr(q, count=3)
            all_videos.extend(vids)
            if len(all_videos) >= MAX_PER_TOPIC:
                break

    if not all_videos:
        print(f"  [INFO] No auto-downloads found. Manual links:")
        print(fallback_search_links(idx, queries))
        return

    downloaded = 0
    for i, vid in enumerate(all_videos[:MAX_PER_TOPIC], 1):
        ext = ".mp4" if ".mp4" in vid["url"] else ".mov"
        filename = f"clip_{i:02d}_{vid['source']}{ext}"
        dest = topic_dir / filename
        if dest.exists():
            print(f"  [SKIP] Already exists: {filename}")
            downloaded += 1
            continue
        print(f"  Downloading {filename} ({vid.get('width','?')}x{vid.get('height','?')}) from {vid['source']}...")
        if download_file(vid["url"], dest):
            print(f"    [OK] Saved {dest.name}")
            downloaded += 1
        else:
            print(f"    [FAIL] Could not download {filename}")
        time.sleep(1)

    print(f"  [{idx}] Done: {downloaded}/{MAX_PER_TOPIC} clips saved to {topic_dir}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Auto-downloading free stock footage...")
    if not PEXELS_API_KEY:
        print("[NOTE] No PEXELS_API_KEY found. Using Coverr scraping fallback.")
        print("       For faster results, get a free key at https://www.pexels.com/api/")
    print("=" * 60)

    for idx, queries in TOPICS.items():
        download_topic(idx, queries)

    print("\n" + "=" * 60)
    print("Stock footage download complete.")
    print(f"Files saved to: {OUTPUT_DIR.absolute()}")
    print("\nNext: import clips into DaVinci Resolve and sync with your voiceover audio.")

if __name__ == "__main__":
    main()
