# YouTube agent config

## Pipeline
1. User topic
2. yt-viral — research + shared tags
3. yt-script — story with `[ON SCREEN]` ~every 6s
4. yt-tts — voiceover.mp3
5. yt-image — **1 still / 6s at 1920×1080** → Pollinations
6. yt-package + thumb **1280×720**
7. yt-seo — recommended_tags

## Image sizes (YouTube standard — mandatory)
- Video stills / B-roll: **1920×1080** (16:9, 1080p)
- Upload thumbnail: **1280×720** (16:9)
- No square/vertical for long-form unless user asks Shorts

## Character (mandatory)
- Reference: `~/.claude/skills/yt-image/character/model-sheet.jpg`
- Specs: `CHARACTER.md` + auto lock in `build_still_prompts.py`
- 2D host: face/hair locked (dark wavy half-up bun); **outfit changes by scene** (`outfits.json`); optional pink brain sidekick


## Image timing
- `build_still_prompts.py --every 6`
- `generate_batch.py --width 1920 --height 1080`
- Key: `yt-image/.env`
