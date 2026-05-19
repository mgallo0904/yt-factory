#!/usr/bin/env python3
"""
Voiceover Prep — Strip markdown from scripts into clean spoken text.
Reads all .md files in ./scripts/ and writes .txt versions for TTS.
"""

import re
from pathlib import Path

SCRIPT_DIR = Path("./scripts")
VOICE_DIR = Path("./voiceovers")

def strip_markdown(text: str) -> str:
    """Remove markdown formatting and return clean spoken text."""
    # Remove YAML frontmatter
    text = re.sub(r'^---\n.*?---\n+', '', text, flags=re.DOTALL)
    # Remove heading markers (# ###)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*\*|__', '', text)
    text = re.sub(r'\*|_', '', text)
    # Remove links — keep just the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove bare URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove horizontal rules
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    # Remove metadata labels like **Description:**
    text = re.sub(r'^\*\*[^*]+\*\*\s*', '', text, flags=re.MULTILINE)
    # Remove list bullet markers if they exist
    text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines into a single blank line
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# Lines that START a skip section — everything after is metadata/trash
SKIP_START_RE = re.compile(
    r'^(metadata|timestamps|tags|description|pinned\s+comment|links|related)'
    r'(\s*\(|\s*[:]|\s*$)',
    re.I
)

# Section headers to strip individually (line only, don't skip what follows)
SECTION_HEADER_RE = re.compile(
    r'^(hook|call\s+to\s+action|content)(\s*\(|\s*[:]|\s*$)',
    re.I
)

HEADING_RE = re.compile(r'^section\s+\d+\s*[:，,.]?\s*', re.I)

def extract_speaking_parts(text: str) -> str:
    """Only keep narration, strip headers and metadata."""
    lines = text.split('\n')
    output_lines = []
    skip_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            output_lines.append('')
            continue

        # Once we hit metadata/timestamps/links, skip to end of file
        if SKIP_START_RE.match(stripped):
            skip_section = True
            continue
        if skip_section:
            continue

        # Strip section heading lines (Hook, Call to Action, Content)
        if SECTION_HEADER_RE.match(stripped):
            continue

        # Strip sub-heading lines like "Section 1: The Title"
        if HEADING_RE.match(stripped):
            continue

        # Strip emoji-prefixed utility lines ⏱ 🔗 🎬 #
        if re.match(r'^(⏱|🔗|🎬|#)\s*', stripped):
            continue

        output_lines.append(line)

    # Clean up whitespace
    result = '\n'.join(output_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def process_file(md_path: Path):
    raw = md_path.read_text(encoding="utf-8")
    # First strip all markdown formatting
    clean = strip_markdown(raw)
    # Then extract only the speaking narraration parts
    spoken = extract_speaking_parts(clean)
    if not spoken:
        print(f"[WARN] No spoken text found in {md_path.name}")
        return
    # Write to voiceovers directory
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    out_name = md_path.stem + "_voiceover.txt"
    out_path = VOICE_DIR / out_name
    out_path.write_text(spoken, encoding="utf-8")
    word_count = len(spoken.split())
    print(f"[DONE] {out_name} — {word_count} words (~{word_count // 150} min read)")

def main():
    md_files = sorted(SCRIPT_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {SCRIPT_DIR.absolute()}")
        return
    print(f"Processing {len(md_files)} scripts for voiceover...")
    print("=" * 60)
    for md in md_files:
        process_file(md)
    print("=" * 60)
    print(f"All voiceover texts saved to {VOICE_DIR.absolute()}")
    print("\nNext step: copy any .txt into your TTS tool (Edge Read Aloud, etc.)")

if __name__ == "__main__":
    main()
