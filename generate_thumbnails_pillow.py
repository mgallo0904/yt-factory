#!/usr/bin/env python3
"""
generate_thumbnails_pillow.py
Batch-generate YouTube thumbnail images (1280x720) from meta JSON files.

Pure Python/Pillow implementation — zero external API calls, zero cost.
Uses system fonts + gradient backgrounds + bold text with drop-shadow.

Saves to: assets/thumbnails/{slug}.png
"""

import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─── paths ──────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.resolve()
META_DIR = BASE / "scripts"
OUT_DIR  = BASE / "assets" / "thumbnails"
OUT_DIR.mkdir(parents=True, exist_ok=True)

THUMB_W, THUMB_H = 1280, 720

# macOS system font candidates (fallback chain)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",  # Linux
    "/Windows/Fonts/arialbd.ttf",  # Windows
]


def find_font() -> str:
    """Return first existing system font path."""
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    # Last resort: ask PIL for a default
    try:
        return ImageFont.load_default().path
    except Exception:
        return None


def hex_to_rgb(hex_color: str) -> tuple:
    """#RRGGBB → (R, G, B)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def interpolate_color(c1: tuple, c2: tuple, factor: float) -> tuple:
    """Blend two RGB tuples by factor 0.0→1.0."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3))


def draw_gradient_bg(draw: ImageDraw.ImageDraw, width: int, height: int,
                     color_top: tuple, color_bottom: tuple) -> None:
    """Vertical linear gradient."""
    for y in range(height):
        factor = y / height
        color = interpolate_color(color_top, color_bottom, factor)
        draw.line([(0, y), (width, y)], fill=color)


def draw_text_with_shadow(img_draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                          font: ImageFont.FreeTypeFont, fill: tuple,
                          shadow_color: tuple = (0, 0, 0), shadow_offset: int = 6) -> None:
    """Draw text with a thick drop-shadow for readability."""
    # Shadow layers (thicker)
    for dx in range(-shadow_offset, shadow_offset + 1, 2):
        for dy in range(-shadow_offset, shadow_offset + 1, 2):
            img_draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)
    # Main text
    img_draw.text((x, y), text, font=font, fill=fill)


def generate_thumbnail(meta: dict, slug: str, font_path: str) -> Path:
    """Build a 1280x720 thumbnail PNG from meta JSON data."""
    texts   = meta.get("thumbnail_text", [])
    colors  = meta.get("color_scheme", {})
    bg_hex  = colors.get("bg", "#1A1A2E")
    txt_hex = colors.get("text", "#E94560")
    acc_hex = colors.get("accent", "#FFD700")

    bg_color   = hex_to_rgb(bg_hex)
    txt_color  = hex_to_rgb(txt_hex)
    acc_color  = hex_to_rgb(acc_hex)

    # Create canvas with gradient background
    img = Image.new("RGB", (THUMB_W, THUMB_H), bg_color)
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(draw, THUMB_W, THUMB_H, bg_color, txt_color)

    # Load fonts at different sizes
    try:
        font_large = ImageFont.truetype(font_path, 110)
        font_medium = ImageFont.truetype(font_path, 90)
        font_small = ImageFont.truetype(font_path, 70)
    except Exception:
        font_large = font_medium = font_small = ImageFont.load_default()

    # Draw up to 3 lines of thumbnail text, centered
    lines = [line.upper() for line in texts[:3]]
    if not lines:
        lines = ["FREE AI", "TOOLS", "TUTORIAL"]

    font_sizes = [font_large, font_medium, font_small]
    y_positions = [180, 340, 500]

    for i, line in enumerate(lines):
        font = font_sizes[i] if i < len(font_sizes) else font_small
        y = y_positions[i] if i < len(y_positions) else 500

        # Measure text width for centering
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (THUMB_W - text_w) // 2

        # Accent color for first line, text color for rest
        fill = acc_color if i == 0 else (255, 255, 255)  # white for contrast

        draw_text_with_shadow(draw, line, x, y, font, fill)

    # Optional: draw a subtle border
    border_w = 8
    draw.rectangle([0, 0, THUMB_W - 1, THUMB_H - 1], outline=acc_color, width=border_w)

    # Save
    out_path = OUT_DIR / f"{slug}.png"
    img.save(out_path, "PNG")
    print(f"  -> saved {out_path.name}")
    return out_path


def slug_from_filename(name: str) -> str:
    """video_01_How_I..._meta.json → video_01"""
    m = re.match(r"^(\d+)_", name)
    if m:
        return f"video_{m.group(1).zfill(2)}"
    m = re.match(r"^(video_\d+)", name)
    return m.group(1) if m else name.replace("_meta.json", "")


def main():
    font_path = find_font()
    if not font_path:
        print("ERROR: No suitable system font found. Install fonts or run on a desktop OS.")
        sys.exit(1)
    print(f"Using font: {font_path}\n")

    meta_files = sorted(META_DIR.glob("*_meta.json"))
    if not meta_files:
        print("No *_meta.json files found in", META_DIR)
        sys.exit(1)

    print(f"Found {len(meta_files)} meta files. Generating thumbnails ...\n")

    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        final_path = OUT_DIR / f"{slug}.png"
        if final_path.exists():
            print(f"[{slug}] already exists, skipping.")
            continue

        print(f"[{slug}]")
        try:
            meta = json.loads(mf.read_text())
            generate_thumbnail(meta, slug, font_path)
        except Exception as e:
            print(f"  ! FAILED: {e}")

    print(f"\nDone. Thumbnails saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
