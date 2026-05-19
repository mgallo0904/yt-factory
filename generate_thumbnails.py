#!/usr/bin/env python3
"""
Thumbnail Text Generator + Title Variation Engine.
Calls Ollama OpenAI-compatible endpoint to produce high-CTR titles and thumbnail text overlays.
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "https://ollama.com/v1/chat/completions"
MODEL_NAME = "kimi-k2.6:cloud"
API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OUTPUT_DIR = Path("./scripts")

VIDEO_TOPICS = [
    "10 Free AI Tools That Will Replace Your Assistant in 2026",
    "I Replaced 5 Paid Apps with Open Source — Here's My Exact Stack",
    "The Dark Side of AI Productivity Nobody Talks About",
    "How I Automate 80% of My Workday with Free Local LLMs",
    "ChatGPT vs Claude vs DeepSeek vs Kimi — The Brutal Truth",
    "Build a Second Brain with Obsidian and AI (Completely Free)",
    "Why Productivity Gurus Don't Want You to Know About These 7 Tools",
    "I Used Only Free AI for 30 Days — This Is What Happened",
    "The $0 Setup for a Fully Automated Content Pipeline",
    "Local AI vs Cloud AI: The Real Cost Breakdown for Creators"
]

THUMBNAIL_PROMPT = """You are a YouTube thumbnail copywriter and CTR expert for a faceless channel.

For the given video topic, produce exactly this JSON:
{
  "title_options": ["string x 5 — clickbait but accurate, max 6 words each"],
  "thumbnail_text": ["string x 3 — short punchy text overlays for the thumbnail, 1-4 words each"],
  "color_scheme": {"bg": "hex", "text": "hex", "accent": "hex"},
  "thumbnail_concept": "string — describe the visual scene",
  "emotional_trigger": "string — what feeling drives the click"
}

Rules:
- Use power words: Destroyed, Exposed, Secret, Brutal, Hack, Dark, Free, Replace, Nobody, Revealed.
- Create curiosity gaps — promise something the viewer feels they are missing.
- No clickbait that feels scammy; must deliver on the promise.
- Output ONLY valid JSON. No markdown, no extra text.
"""

def run_ollama(user_prompt: str, system: str = "", max_retries: int = 3, timeout: int = 240) -> dict:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "temperature": 0.9,
        "response_format": {"type": "json_object"}
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=timeout)
            if r.status_code == 503:
                print(f"    [503] Server busy, retrying in {attempt * 5}s... (attempt {attempt}/{max_retries})")
                time.sleep(attempt * 5)
                continue
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0]
            return json.loads(cleaned.strip())
        except (requests.exceptions.HTTPError) as e:
            status = getattr(e.response, 'status_code', None)
            if status == 401:
                print(f"    [401] Unauthorized — check your OLLAMA_API_KEY.")
                return {}
            if attempt < max_retries:
                print(f"    [HTTP {status}] {e}, retrying in {attempt * 5}s...")
                time.sleep(attempt * 5)
                continue
            print(f"Error: {e}")
            return {}
        except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                print(f"    [Timeout] Read timed out, retrying in {attempt * 10}s...")
                time.sleep(attempt * 10)
                continue
            print(f"Error: {e}")
            return {}
        except Exception as e:
            print(f"Error: {e}")
            return {}
    print(f"[SKIP] All retries exhausted.")
    return {}

def save_meta(index: int, topic: str, data: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = topic.replace(" ", "_").replace("/", "-")[:50]
    path = OUTPUT_DIR / f"{index:02d}_{slug}_meta.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[META] {path}")

def main():
    print("Generating thumbnail + title variations...")
    for i, topic in enumerate(VIDEO_TOPICS, 1):
        print(f"[{i}/10] {topic}")
        data = run_ollama(f"Topic: {topic}", THUMBNAIL_PROMPT)
        if data:
            save_meta(i, topic, data)
            for t in data.get("title_options", []):
                print(f"  -> {t}")
            for tt in data.get("thumbnail_text", []):
                print(f"  THUMB -> {tt}")
    print(f"\nDone. Metadata saved to {OUTPUT_DIR.absolute()}")

if __name__ == "__main__":
    main()
