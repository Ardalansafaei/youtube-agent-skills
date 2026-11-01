---
name: yt-image
description: >-
  Build one Pollinations image prompt every 6 seconds of the YouTube script,
  then generate stills at standard YouTube 16:9 video size 1920×1080; thumbnails
  at 1280×720. Default image backend for yt-agent.
---

# yt-image (Pollinations) — YouTube-standard sizes + locked character

## Character (mandatory)

Canonical host: `character/model-sheet.jpg` (+ `model-sheet-alt.jpg`) + `character/CHARACTER.md`

**Art style (locked):** 3D CGI Pixar/Disney — smooth stylized render, soft subsurface skin, cinematic depth of field.  
**Not** flat 2D, **not** anime, **not** photoreal / live-action.

Face + hair locked (messy dark-brown half-up bun, freckles, large brown eyes).  
**Outfit and environment change every beat** via `outfits.json` + scene library in `build_still_prompts.py`.

Approved look reference: party/exit sample quality (`sample-preview` style) — unique environment per beat, same face.

## Anti-repetition (mandatory for stills)

Every still must change **at least two** of: environment, action/pose, camera angle, lighting.  
Never chain the same desk-laptop pose. Social beats may use soft out-of-focus background people; no competing sharp faces.

## Size rules (mandatory)

| Asset | Size | Aspect | Notes |
|-------|------|--------|-------|
| **Timeline stills / B-roll** (every 6s) | **1920×1080** | 16:9 | Matches standard YouTube video (1080p) |
| **Upload thumbnail** | **1280×720** | 16:9 | YouTube recommended thumbnail |

**Always 16:9.** Do not use square/vertical for long-form unless user asks Shorts.

Names starting with `thumb` in `prompts.txt` auto-render at **1280×720**.

## Thumbnail formula (mandatory — collage style)

Match `character/thumb-reference.jpg` (psychology / emotional-control collage):

1. **Hero:** same locked 3D host, large on the right (or left), MCU/close, chin-on-hand or strong emotional pose, cinematic warm light.
2. **Vignettes:** 3–4 smaller frames / thought-bubbles of the **same** character in different emotional beats (phone stress, crowd anxiety, calm/peace, etc.).
3. **Text:** bold readable YouTube title words on the opposite side — short punch line + one yellow/paint accent word if needed; optional thin subtitle.
4. Size **1280×720**. High feed contrast. Same face in every panel.

Do **not** ship plain single-pose thumbs with empty text space only.

## Timing rule

One educational-still prompt **every 6 seconds** of spoken runtime (150 WPM) → **1920×1080**.

## API

- Keys: `POLLINATIONS_KEYS.md` — on `402` / empty pollen, rotate via `.pollinations_key_index`
- Fallback: `.env` → `POLLINATIONS_API_KEY`
- Model: **flux**

## Required flow

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-images\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$run\script.txt" --out $run --every 6
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$run\prompts.txt" --out $run --width 1920 --height 1080
```

Thumbnails: append `thumb_*|…` lines (collage formula above) then generate — auto **1280×720**.

## Checklist

```
yt-image:
- [ ] 3D Pixar lock (not flat 2D)
- [ ] stills every 6s at 1920×1080, unique scene each beat
- [ ] thumbs 1280×720 collage (hero + vignettes + bold text)
- [ ] generate_batch done / pollen errors reported honestly
```

## Failure

402 / empty pollen → next key in `POLLINATIONS_KEYS.md`; if all fail, keep prompts + finished files; never Arena; never wrong aspect for YouTube long-form.
