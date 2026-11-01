---
name: yt-image
description: >-
  Build one Pollinations image prompt every 6 seconds of the YouTube script,
  then generate stills at standard YouTube 16:9 video size 1920×1080; thumbnails
  at 1280×720. Default image backend for yt-agent.
---

# yt-image (Pollinations) — YouTube-standard sizes + locked character

## Character (mandatory)

Canonical host: `character/model-sheet.jpg` + `character/CHARACTER.md`  
Face/hair/2D style locked; **clothes follow the scene** via `outfits.json`.  
`build_still_prompts.py` injects lock + scene outfit. Optional pink brain sidekick when teaching.  
Do **not** invent a new face/hairstyle or go photoreal.

## Size rules (mandatory)

| Asset | Size | Aspect | Notes |
|-------|------|--------|-------|
| **Timeline stills / B-roll** (every 6s) | **1920×1080** | 16:9 | Matches standard YouTube video (1080p) |
| **Upload thumbnail** | **1280×720** | 16:9 | YouTube recommended thumbnail |

**Always 16:9.** Do not use square (1:1), vertical (9:16), or odd sizes for long-form YouTube stills/thumbs unless the user explicitly asks for Shorts.

Names starting with `thumb` in `prompts.txt` auto-render at **1280×720**; all other stills default to **1920×1080**.

## Timing rule

One educational-still prompt **every 6 seconds** of spoken runtime (150 WPM).  
`still_0000_0006`, `still_0006_0012`, … → each file **1920×1080**.

## API

`~/.claude/skills/yt-image/.env` → `POLLINATIONS_API_KEY` · model **flux**

## Required flow

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-images\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$run\script.txt" --out $run --every 6
# stills = 1920×1080 (YouTube video frame)
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$run\prompts.txt" --out $run --width 1920 --height 1080
```

Thumbnails (optional extra lines): `thumb_A|YouTube thumbnail frame, …` → **1280×720** automatically.

## Checklist

```
yt-image:
- [ ] stills every 6s at 1920×1080 (16:9)
- [ ] thumbs at 1280×720 if any
- [ ] generate_batch done / pollen error reported honestly
```

## Failure

402 pollen → keep prompts + finished files; never Arena; never wrong aspect for YouTube long-form.
