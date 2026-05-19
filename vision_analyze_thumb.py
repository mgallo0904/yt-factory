#!/usr/bin/env python3
"""
Thumbnail Analyzer — Uses kimi-k2.6:cloud vision to critique and score thumbnails.
Can analyze local image files or competitor thumbnail URLs.
"""

import requests
import json
import os
import base64
import sys
from pathlib import Path

OLLAMA_URL = "https://ollama.com/v1/chat/completions"
MODEL_NAME = "kimi-k2.6:cloud"
API_KEY = os.environ.get("OLLAMA_API_KEY", "")

VISION_PROMPT = """You are a YouTube CTR expert analyzing a thumbnail image.

Provide a JSON critique with these exact keys:
{
  "score": "integer 0-100",
  "strengths": ["string x 3"],
  "weaknesses": ["string x 3"],
  "text_readability": "string — is the main text legible at small size?",
  "emotional_trigger": "string — what emotion drives the click?",
  "improvements": ["string x 3 — actionable redesign suggestions"],
  "color_analysis": "string — does the palette pop on dark/white YouTube backgrounds?"
}

Scoring criteria (be strict):
- Text must be readable on mobile (max 3-5 words, big bold font).
- One focal point (face, object, or bold text).
- High contrast against YouTube's dark theme.
- Curiosity gap or emotional hook visible.
- No cluttered details.

Output ONLY valid JSON. No markdown, no extra text."""

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_image(image_path: str) -> dict:
    b64 = encode_image(image_path)
    # Determine MIME type from extension
    ext = Path(image_path).suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }
        ],
        "stream": False,
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    resp = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0]
    return json.loads(cleaned.strip())

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 vision_analyze_thumb.py <image_path>")
        print("Example: python3 vision_analyze_thumb.py ./thumbnails/thumb_01.png")
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"File not found: {image_path}")
        sys.exit(1)

    print(f"Analyzing: {image_path}")
    result = analyze_image(image_path)
    print(json.dumps(result, indent=2))

    # Save to sidecar JSON
    sidecar = Path(image_path).with_suffix(".json")
    sidecar.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved critique to: {sidecar}")

if __name__ == "__main__":
    main()
