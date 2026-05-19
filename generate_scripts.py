#!/usr/bin/env python3
"""
YouTube Faceless Channel — Script Factory
Calls an Ollama OpenAI-compatible endpoint to batch-generate video scripts + metadata.
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
OLLAMA_URL = os.environ.get("OLLAMA_ENDPOINT", "https://ollama.com/v1/chat/completions")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "kimi-k2.6:cloud")
API_KEY = os.environ.get("OLLAMA_API_KEY", "")
NICHE = "AI Tools and Productivity"
OUTPUT_DIR = Path("./scripts")
BATCH_SIZE = 10
# ---------------------

SYSTEM_PROMPT = """You are an expert YouTube scriptwriter for a faceless channel in the AI tools and productivity niche.
Your goal is to write scripts that maximize watch time and CTR.

Rules:
- Hook must be a bold claim or curiosity gap in the first 30 seconds.
- Each section must include a story, analogy, or concrete example.
- Tone is conversational but authoritative.
- Never use "in this video" or "let's get started" — waste no time.
- Output MUST be valid JSON only. No markdown code blocks. No extra text.

JSON schema:
{
  "title": "string (clickbait but accurate)",
  "hook": "string (0-30 second spoken script)",
  "sections": [
    {"heading": "string", "content": "string (spoken script, 150-250 words)"}
  ],
  "cta": "string (final 30 seconds, soft CTA)",
  "description": "string (YouTube description with timestamps and links)",
  "tags": ["string"],
  "pinned_comment": "string (engagement question + affiliate link tease)"
}
"""

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

def generate_script(topic: str, max_retries: int = 3) -> dict:
    user_prompt = f"Write a 1200-1500 word YouTube script for this topic: {topic}. Follow the system rules exactly."
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "temperature": 0.85,
        "response_format": {"type": "json_object"}
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=240)
            if resp.status_code == 503:
                print(f"    [503] Server busy, retrying in {attempt * 5}s... (attempt {attempt}/{max_retries})")
                time.sleep(attempt * 5)
                continue
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"]
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', None)
            if status == 401:
                print(f"    [401] Unauthorized — check your OLLAMA_API_KEY.")
                return {}
            if attempt < max_retries:
                print(f"    [HTTP {status}] {e}, retrying in {attempt * 5}s...")
                time.sleep(attempt * 5)
                continue
            print(f"[ERROR] Failed on topic '{topic}': {e}")
            return {}
        except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                print(f"    [Timeout] Read timed out, retrying in {attempt * 10}s...")
                time.sleep(attempt * 10)
                continue
            print(f"[ERROR] Failed on topic '{topic}': {e}")
            return {}
        except Exception as e:
            print(f"[ERROR] Failed on topic '{topic}': {e}")
            return {}
    print(f"[SKIP] {topic} — all retries exhausted.")
    return {}

def save_script(index: int, topic: str, script: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_slug = topic.replace(" ", "_").replace("/", "-")[:50]
    filename = OUTPUT_DIR / f"{index:02d}_{safe_slug}.md"
    now = datetime.now().isoformat()

    content = f"""---
title: "{script.get('title', topic)}"
topic: "{topic}"
generated_at: "{now}"
model: "{MODEL_NAME}"
niche: "{NICHE}"
status: draft
---

# {script.get('title', topic)}

## Hook (0:00–0:30)
{script.get('hook', 'N/A')}

## Content
"""
    for i, sec in enumerate(script.get("sections", []), 1):
        content += f"""
### Section {i}: {sec.get('heading', 'Untitled')}
{sec.get('content', 'N/A')}
"""

    content += f"""
## Call to Action (Final 30s)
{script.get('cta', 'N/A')}

---

## Metadata

**Description:**
{script.get('description', 'N/A')}

**Tags:** {', '.join(script.get('tags', []))}

**Pinned Comment:**
{script.get('pinned_comment', 'N/A')}
"""

    filename.write_text(content, encoding="utf-8")
    print(f"[SAVED] {filename}")

def main():
    print(f"Batch generating {BATCH_SIZE} scripts via {MODEL_NAME} at {OLLAMA_URL}")
    print("=" * 60)
    for i, topic in enumerate(VIDEO_TOPICS[:BATCH_SIZE], 1):
        print(f"[{i}/{BATCH_SIZE}] Generating: {topic} ...")
        script = generate_script(topic)
        if script:
            save_script(i, topic, script)
        else:
            print(f"[SKIP] {topic} — generation failed.")
    print("=" * 60)
    print(f"Done. Scripts saved to {OUTPUT_DIR.absolute()}")

if __name__ == "__main__":
    main()
