#!/usr/bin/env python3
"""Recovery script — only generates missing scripts and meta files."""

import os, time, json, requests
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "https://ollama.com/v1/chat/completions"
MODEL_NAME = "kimi-k2.6:cloud"
API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OUTPUT_DIR = Path("./scripts")

TOPICS = [
    ("05", "ChatGPT vs Claude vs DeepSeek vs Kimi — The Brutal Truth", True, True),
    ("06", "Build a Second Brain with Obsidian and AI (Completely Free)", True, True),
    ("07", "Why Productivity Gurus Don't Want You to Know About These 7 Tools", True, True),
    ("08", "I Used Only Free AI for 30 Days — This Is What Happened", True, True),
    ("02", "I Replaced 5 Paid Apps with Open Source — Here's My Exact Stack", False, True),
    ("04", "How I Automate 80% of My Workday with Free Local LLMs", False, True),
    ("09", "The $0 Setup for a Fully Automated Content Pipeline", False, True),
]

SCRIPT_SYSTEM = """You are an expert YouTube scriptwriter for a faceless channel in the AI tools and productivity niche.
Rules:
- Hook must be a bold claim or curiosity gap in the first 30 seconds.
- Each section must include a story, analogy, or concrete example.
- Tone is conversational but authoritative. Never use "in this video" or "let's get started".
- Output MUST be valid JSON only. No markdown code blocks. No extra text.

JSON schema:
{
  "title": "string (clickbait but accurate)",
  "hook": "string (0-30 second spoken script)",
  "sections": [{"heading": "string", "content": "string (spoken script, 150-250 words)"}],
  "cta": "string (final 30 seconds, soft CTA)",
  "description": "string (YouTube description with timestamps and links)",
  "tags": ["string"],
  "pinned_comment": "string (engagement question + affiliate link tease)"
}"""

META_SYSTEM = """You are a YouTube thumbnail copywriter and CTR expert.
For the given topic, produce exactly this JSON:
{
  "title_options": ["string x 5 — clickbait but accurate, max 6 words each"],
  "thumbnail_text": ["string x 3 — short punchy text overlays, 1-4 words each"],
  "color_scheme": {"bg": "hex", "text": "hex", "accent": "hex"},
  "thumbnail_concept": "string — describe the visual scene",
  "emotional_trigger": "string — what feeling drives the click"
}
Rules: use power words (Destroyed, Exposed, Secret, Brutal, Hack, Dark, Free, Replace, Nobody, Revealed). Create curiosity gaps. No scammy clickbait. Output ONLY valid JSON. No markdown."""

def call_ollama(system: str, user: str, timeout: int = 240):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "temperature": 0.85,
        "response_format": {"type": "json_object"}
    }
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    for attempt in range(1, 4):
        try:
            r = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=timeout)
            if r.status_code == 503:
                print(f"    [503] retry in {attempt*5}s...")
                time.sleep(attempt*5); continue
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"): raw = raw.split("\n", 1)[1]
            if raw.endswith("```"): raw = raw.rsplit("\n", 1)[0]
            return json.loads(raw.strip())
        except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
            print(f"    [Timeout] retry in {attempt*10}s...")
            time.sleep(attempt*10)
        except requests.exceptions.HTTPError as e:
            print(f"    [HTTP {e.response.status_code}] retry in {attempt*5}s...")
            time.sleep(attempt*5)
    return None

def save_script(idx, topic, data):
    slug = topic.replace(" ", "_").replace("/", "-")[:50]
    path = OUTPUT_DIR / f"{idx}_{slug}.md"
    content = f"""---
title: "{data.get('title', topic)}"
topic: "{topic}"
generated_at: "{datetime.now().isoformat()}"
model: "{MODEL_NAME}"
niche: "AI Tools and Productivity"
status: draft
---

# {data.get('title', topic)}

## Hook (0:00–0:30)
{data.get('hook', 'N/A')}

## Content
"""
    for i, sec in enumerate(data.get("sections", []), 1):
        content += f"""
### Section {i}: {sec.get('heading', 'Untitled')}
{sec.get('content', 'N/A')}
"""
    content += f"""
## Call to Action (Final 30s)
{data.get('cta', 'N/A')}

---

## Metadata

**Description:**
{data.get('description', 'N/A')}

**Tags:** {', '.join(data.get('tags', []))}

**Pinned Comment:**
{data.get('pinned_comment', 'N/A')}
"""
    path.write_text(content, encoding="utf-8")
    print(f"  [SAVED SCRIPT] {path}")

def save_meta(idx, topic, data):
    slug = topic.replace(" ", "_").replace("/", "-")[:50]
    path = OUTPUT_DIR / f"{idx}_{slug}_meta.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [SAVED META] {path}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for idx, topic, need_script, need_meta in TOPICS:
        slug = topic.replace(" ", "_").replace("/", "-")[:50]
        md_path = OUTPUT_DIR / f"{idx}_{slug}.md"
        json_path = OUTPUT_DIR / f"{idx}_{slug}_meta.json"

        if need_script and not md_path.exists():
            print(f"[{idx}] Generating script: {topic}")
            data = call_ollama(SCRIPT_SYSTEM, f"Write a 1200-1500 word YouTube script for: {topic}")
            if data:
                save_script(idx, topic, data)
            else:
                print(f"  [FAIL] script {idx}")
        if need_meta and not json_path.exists():
            print(f"[{idx}] Generating meta: {topic}")
            data = call_ollama(META_SYSTEM, f"Topic: {topic}")
            if data:
                save_meta(idx, topic, data)
            else:
                print(f"  [FAIL] meta {idx}")
    print("\nRecovery complete.")

if __name__ == "__main__":
    main()
