# YouTube agent config

## Language (mandatory)
- **All video output is English** — script, voiceover, titles, description, tags, on-screen text, thumb punch text.
- User may chat in any language; do **not** ask language unless they explicitly request non-English.
- TTS default: `en-US-AndrewNeural`
- Research may include non-English markets for ideas; ship content in English.

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
- Specs: `CHARACTER.md` + `prompts.md` + auto lock in `build_still_prompts.py`
- 3D Pixar host: face/hair locked; **scene + other people + outfit color + face emotion** change every beat (`scenes.json`, `outfits.json`, `expressions.json`, `atmospheres.json`)


## Image timing
- `build_still_prompts.py --every 6`
- `generate_batch.py --width 1920 --height 1080`
- Key: `yt-image/.env`
