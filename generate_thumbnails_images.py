#!/usr/bin/env python3
"""Professional YouTube thumbnail generator using Pillow.
Creates clean dark-theme thumbnails with bold text — no random AI art.
saves to: assets/thumbnails/video_XX.png
"""

import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

META_DIR = Path("./scripts")
OUT_DIR = Path("./assets/thumbnails")
OUT_DIR.mkdir(parents=True, exist_ok=True)

THUMB_W, THUMB_H = 1280, 720

# Predefined color palettes per emotion
PALETTES = {
    "urgent":   {"bg_top": "#1a0500", "bg_bot": "#2d0b00", "accent": "#ff4d00", "text": "#ffffff"},
    "curious":  {"bg_top": "#0a0a1a", "bg_bot": "#12122e", "accent": "#00d4ff", "text": "#ffffff"},
    "shocking": {"bg_top": "#1a0000", "bg_bot": "#330000", "accent": "#ff0040", "text": "#ffffff"},
    "calm":     {"bg_top": "#0a1a0a", "bg_bot": "#0d2e12", "accent": "#4ade80", "text": "#ffffff"},
    "default":  {"bg_top": "#0f0f1a", "bg_bot": "#1a1a2e", "accent": "#ff0040", "text": "#ffffff"},
}


def get_font(size: int) -> ImageFont.FreeTypeFont | None:
    """Try to load a good bold font, fallbacks included."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    # Fallback to default
    return ImageFont.load_default()


def create_gradient(w: int, h: int, top_color: str, bot_color: str) -> Image.Image:
    """Draw vertical gradient."""
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    tc = tuple(int(top_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    bc = tuple(int(bot_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for y in range(h):
        r = int(tc[0] + (bc[0] - tc[0]) * y / h)
        g = int(tc[1] + (bc[1] - tc[1]) * y / h)
        b = int(tc[2] + (bc[2] - tc[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def draw_wrapped_text(draw, text: str, x: int, y: int, w: int, font: ImageFont.FreeTypeFont,
                       fill: str, outline: str | None = None, outline_width: int = 3) -> int:
    """Draw text word-wrapped to width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        test = cur + " " + word if cur else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= x + w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    line_h = font.size + 6
    for i, line in enumerate(lines):
        ly = y + i * line_h
        if outline:
            for ox in range(-outline_width, outline_width + 1):
                for oy in range(-outline_width, outline_width + 1):
                    draw.text((x + ox, ly + oy), line, font=font, fill=outline)
        draw.text((x, ly), line, font=font, fill=fill)
    return y + len(lines) * line_h


def generate_thumbnail(meta: dict, slug: str) -> Path:
    """Generate a clean thumbnail image."""
    out_path = OUT_DIR / f"{slug}.png"
    if out_path.exists():
        print(f"  [{slug}] exists, skip.")
        return out_path

    # Determine palette
    emotion = meta.get("emotional_trigger", "").lower()
    if "urgent" in emotion or "scary" in emotion:
        pal = PALETTES["urgent"]
    elif "curious" in emotion or "mystery" in emotion:
        pal = PALETTES["curious"]
    elif "shocking" in emotion or "surprising" in emotion:
        pal = PALETTES["shocking"]
    elif "calm" in emotion:
        pal = PALETTES["calm"]
    else:
        pal = PALETTES["default"]

    # Build headline from thumbnail_text or fallback to title
    texts = meta.get("thumbnail_text", [])
    if texts:
        headline = texts[0].upper()
        subline = texts[1].upper() if len(texts) > 1 else ""
    else:
        headline = meta.get("title", meta.get("topic", slug)).upper()
        subline = ""

    # Clean up headline for display: remove tool names that clutter
    headline = re.sub(r'\b(USING|WITH|YOUR?|THE)\b', '', headline).strip()
    headline = re.sub(r'\s+', ' ', headline)

    # Create canvas
    canvas = create_gradient(THUMB_W, THUMB_H, pal["bg_top"], pal["bg_bot"])
    draw = ImageDraw.Draw(canvas)

    # Draw accent bars / shapes for visual interest
    accent_rgb = tuple(int(pal["accent"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    draw.rectangle([(0, THUMB_H - 12), (THUMB_W, THUMB_H)], fill=pal["accent"])

    # Title font
    title_font = get_font(110)
    if title_font is None:
        title_font = ImageFont.load_default()

    # Draw headline centered
    # First measure
    words = headline.split(" ")
    lines = []
    cur = ""
    max_w = THUMB_W - 160  # margins
    for word in words:
        test = cur + " " + word if cur else word
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    # Adjust font size if too many lines
    font_size = 110
    while len(lines) > 3 and font_size > 60:
        font_size -= 10
        title_font = get_font(font_size)
        cur = ""
        lines = []
        for word in words:
            test = cur + " " + word if cur else word
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)

        # One more pass: try breaking by comma/colon
        flat = " ".join(lines)
        flat = flat.replace(",", "\n").replace(":", "\n")
        if "\n" in flat:
            lines = flat.split("\n")
            lines = [l.strip() for l in lines if l.strip()]

    line_h = title_font.size + 10
    total_h = len(lines) * line_h
    start_y = (THUMB_H - total_h) // 2 - 40

    for i, line in enumerate(lines):
        ly = start_y + i * line_h
        # Shadow
        draw.text((82, ly + 4), line, font=title_font, fill="black")
        # Accent highlight for first line
        color = pal["accent"] if i == 0 else pal["text"]
        draw.text((80, ly), line, font=title_font, fill=color)

    # Subline
    if subline:
        sub_font = get_font(48) or ImageFont.load_default()
        sb = draw.textbbox((0, 0), subline, font=sub_font)
        sw = sb[2] - sb[0]
        if sw < max_w:
            sx = (THUMB_W - sw) // 2
            sy = start_y + total_h + 30
            draw.text((sx + 2, sy + 2), subline, font=sub_font, fill="black")
            draw.text((sx, sy), subline, font=sub_font, fill=pal["text"])

    # Save
    canvas.save(out_path, "PNG", optimize=True)
    print(f"  [{slug}] saved {out_path.name}")
    return out_path


def slug_from_filename(name: str) -> str:
    m = re.match(r"^(\d+)", name)
    return f"video_{m.group(1).zfill(2)}" if m else name.replace("_meta.json", "")


def main():
    meta_files = sorted(META_DIR.glob("*_meta.json"))
    if not meta_files:
        print("No meta files found.")
        return

    print(f"Generating {len(meta_files)} thumbnails ...\n")
    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        meta = json.loads(mf.read_text())
        generate_thumbnail(meta, slug)

    print(f"\nDone. Thumbnails saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
