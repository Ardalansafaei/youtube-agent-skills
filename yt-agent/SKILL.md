---
name: yt-agent
description: >-
  YouTube agent: topic → viral research → script → Edge-TTS audio → one
  Pollinations image prompt every 6 seconds of runtime then full still render →
  packaging/SEO. Use for "ایجنت یوتیوب", stills timeline, story + audio + images.
---

# YouTube Agent

## Language (mandatory)

**English only** for script, VO, titles, SEO, on-screen text, thumbs — even if the user chats in another language. Do not ask which language. TTS: `en-US-AndrewNeural`. See `youtube-config/agent.md`.

## Order (mandatory)

```text
1. Topic from user
2. yt-viral     → viral videos, why views, shared tags
3. yt-script    → story/script with [ON SCREEN] cues (~every 6s)
4. yt-tts       → voiceover.mp3
5. yt-image     → build_still_prompts every 6s → Pollinations batch
6. yt-package   → title + thumb → extra thumb prompts/render
7. yt-seo       → description + recommended_tags
8. chapters / shorts / edit as needed
```

## Image rule — 1 prompt / 6 seconds

After the spoken script is ready (unless user says no-stills):

1. Copy script into the image run folder as `script.txt`.
2. Build prompts:

```powershell
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$imgRun\script.txt" --out $imgRun --every 6
```

3. Optionally tighten each line with `yt-image/prompts.md` (keep the same row count).
4. Generate all stills:

```powershell
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$imgRun\prompts.txt" --out $imgRun --width 1920 --height 1080
```

**Size (mandatory):** timeline stills = **1920×1080** (standard YouTube 16:9 / 1080p).  
Upload thumbnails = **1280×720**. Never square/vertical for long-form unless user asks Shorts.

**Character (mandatory):** locked host in `yt-image/character/` — **3D Pixar/Disney** face/hair from model sheet (not flat 2D, not photoreal).  
**Prompt grammar:** follow `yt-image/prompts.md` — scene matching the spoken beat, other people when social, outfit **color** change, atmosphere, face emotion (`scenes.json` / `outfits.json` / `expressions.json` / `atmospheres.json`).  
**Thumbnails:** Pollinations **1280×720** via `generate_batch.py` (`thumb_*` lines); collage + ≤3-word punch text.  
**Stills + thumbs API:** `yt-image/POLLINATIONS_KEYS.md` / `.env` (rotate on 402).

Example: ~60s script → ~10 stills; ~10 min → ~100 stills.  
On pollen `402`, stop and report how many finished — keep `prompts.txt`.

## Other pipelines

**Research**

```powershell
python "$env:USERPROFILE\.claude\skills\yt-viral\research_topic.py" "TOPIC" --out "$researchRun\research.json"
```

**Audio** (unless text-only)

```powershell
python "$env:USERPROFILE\.claude\skills\yt-tts\scripts\generate.py" --file "$ttsRun\script.txt" --out $ttsRun --name voiceover --voice en-US-AndrewNeural
```

**SEO:** use `recommended_tags` from research (≤15).

## Skill map

| Need | Skill |
|------|--------|
| Viral + tags | `yt-viral` |
| Script / story | `yt-script` |
| VO MP3 | `yt-tts` |
| Stills every 6s + thumbs | `yt-image` |
| Title / thumb brief | `yt-package` |
| Description / tags | `yt-seo` |

## Gate

**ship it, or change it?**
