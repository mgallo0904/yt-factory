<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-19 | Updated: 2026-05-19 -->

# voiceovers

## Purpose
Contains all voiceover-related outputs: prepared text files for TTS, generated hook audio clips, and full-length narrated audio tracks. Organized by video number to match the scripts pipeline.

## Key Files

| File | Description |
|------|-------------|
| `01_10_Free_AI_Tools_That_Will_Replace_Your_Assistant__voiceover.txt` | Prepared voiceover text for Video 1 |
| `01_hook_demo.mp3` | Demo hook audio for Video 1 |
| `01_hook_demo.ogg` | OGG version of Video 1 hook demo |
| `02_I_Replaced_5_Paid_Apps_with_Open_Source_—_Here's_M_voiceover.txt` | Voiceover text for Video 2 |
| `03_The_Dark_Side_of_AI_Productivity_Nobody_Talks_Abou_voiceover.txt` | Voiceover text for Video 3 |
| `04_How_I_Automate_80%_of_My_Workday_with_Free_Local_L_voiceover.txt` | Voiceover text for Video 4 |
| `05_ChatGPT_vs_Claude_vs_DeepSeek_vs_Kimi_—_The_Brutal_Truth_voiceover.txt` | Voiceover text for Video 5 |
| `06_Build_a_Second_Brain_with_Obsidian_and_AI_(Completely_Free)_voiceover.txt` | Voiceover text for Video 6 |
| `07_Why_Productivity_Gurus_Don't_Want_You_to_Know_About_These_7_Tools_voiceover.txt` | Voiceover text for Video 7 |
| `08_I_Used_Only_Free_AI_for_30_Days_—_This_Is_What_Happened_voiceover.txt` | Voiceover text for Video 8 |
| `09_The_$0_Setup_for_a_Fully_Automated_Content_Pipelin_voiceover.txt` | Voiceover text for Video 9 |
| `10_Local_AI_vs_Cloud_AI:_The_Real_Cost_Breakdown_for__voiceover.txt` | Voiceover text for Video 10 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `full/` | Full-length narrated audio tracks (MP3) per video (see `full/AGENTS.md`) |
| `hooks/` | Short hook audio clips (MP3) for video intros (see `hooks/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Voiceover text files are produced by `prep_voiceover.py` from the markdown scripts
- Audio files are produced by `generate_full_audio.py` and `generate_hooks.py`
- Do not delete `.txt` files until the corresponding `.mp3` is confirmed generated
- Hook demo files in the root are temporary/deprecated — prefer `hooks/hook_NN.mp3`

### Testing Requirements
- Verify that every script in `../scripts/` has a matching `*_voiceover.txt` before audio generation
- Check that `full/` contains 10 MP3s for a complete batch
- Check that `hooks/` contains 10 MP3s for a complete batch

### Common Patterns
- Naming: `<NN>_<sanitized_title>_voiceover.txt` for text, `full_<NN>.mp3` / `hook_<NN>.mp3` for audio
- Audio files are numbered 01–10 to match the scripts index

## Dependencies

### Internal
- `../scripts/` — source markdown scripts converted to voiceover text
- `../prep_voiceover.py` — writes `*_voiceover.txt` files here
- `../generate_full_audio.py` — writes MP3s to `full/`
- `../generate_hooks.py` — writes MP3s to `hooks/`

### External
- TTS engine or cloud API used by the audio generation scripts

<!-- MANUAL: -->
