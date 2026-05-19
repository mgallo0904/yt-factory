<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-19 | Updated: 2026-05-19 -->

# assets

## Purpose
Container directory for all media assets used in video production: stock footage clips and generated thumbnail images. Assets are organized by video number to keep the pipeline stage outputs aligned.

## Key Files

_None — this directory contains only subdirectories._

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `stock/` | Downloaded stock video clips per video topic (see `stock/AGENTS.md`) |
| `thumbnails/` | Generated thumbnail PNG images and video-numbered thumbs (see `thumbnails/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Do not add loose files here; use `stock/` or `thumbnails/` subdirectories
- The `download_stock.py` script auto-creates `stock/video_NN/` directories as needed
- Thumbnail generators save directly to `thumbnails/`

### Testing Requirements
- Verify `stock/` and `thumbnails/` exist before running generators
- Check that video-numbered subdirectories in `stock/` contain at least one clip before video assembly

### Common Patterns
- `stock/video_NN/` directories are numbered 01–10 to match scripts
- Thumbnail filenames include the video title slug for easy identification

## Dependencies

### Internal
- `../scripts/` — metadata drives which stock clips and thumbnails to generate
- `../generate_thumbnails*.py` — write images to `thumbnails/`
- `../download_stock.py` — writes clips to `stock/video_NN/`

### External
- Coverr API (no key) and Pexels API (optional key) for stock footage
- Pillow/Imagemagick for thumbnail rendering

<!-- MANUAL: -->
