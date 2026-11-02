---
name: yt-image
description: >-
  Build one Pollinations image prompt every 6 seconds of the YouTube script,
  then generate stills at 1920×1080 and thumbnails at 1280×720 via Pollinations
  (optional OpenAI / Cloudflare fallbacks for thumbs only). Prompts must stage
  story-matched places, other people when social, changing outfit colors, and
  facial emotion — see prompts.md.
---

# yt-image — stills + thumbs (Pollinations)

## Prompt writing (mandatory)

Read and follow **`prompts.md`** before building or hand-editing prompts.

Each still prompt must include, in order:

1. **Scene** matching the spoken beat (`scenes.json`)
2. **Other people** when the story is social
3. **Outfit + color change** vs previous still (`outfits.json` wardrobe)
4. **Atmosphere** (`atmospheres.json`)
5. **Face emotion** (`expressions.json`)
6. Character lock + negatives

Do **not** ship empty pretty rooms, the same lavender outfit every frame, or calm smiles on fear/shame/anxiety beats.  
Do **not** regenerate a full batch unless the user asks — fixing grammar/docs first is enough when they say so.

## Character (mandatory)

Canonical host: `character/model-sheet.jpg` (+ `model-sheet-alt.jpg`) + `character/CHARACTER.md`

**Art style (locked):** 3D CGI Pixar/Disney — smooth stylized render, soft subsurface skin, cinematic depth of field.  
**Not** flat 2D, **not** anime, **not** photoreal / live-action.

Face + hair locked (messy dark-brown half-up bun, freckles, large brown eyes).  
**Place, people, outfit color, and face emotion change every beat** via:

- `character/scenes.json`
- `character/outfits.json`
- `character/expressions.json`
- `character/atmospheres.json`
- `scripts/build_still_prompts.py`

## Anti-repetition (mandatory for stills)

Every still must change **at least two** of: place, wardrobe color, people setup, camera, lighting.  
Never chain the same desk-laptop pose or the same empty living room.

## Still file naming (mandatory)

Sort order = timeline order. Use a **zero-padded sequence first**:

```text
still_001_t0000-0006.jpg
still_002_t0006-0012.jpg
still_003_t0012-0018.jpg
```

Pattern: `still_{NNN}_t{start}-{end}` where `NNN` is 001…N.

## Size rules (mandatory)

| Asset | Size | Aspect | Backend |
|-------|------|--------|---------|
| **Timeline stills** (every 6s) | **1920×1080** | 16:9 | Pollinations (`generate.py`) |
| **Upload thumbnail** | **1280×720** | 16:9 | Pollinations (`generate.py` / `generate_batch.py` `thumb_*`) |

**Always 16:9.** `thumb_*` lines use **1280×720**. Optional OpenAI / Cloudflare fallbacks only if those keys are set and needed.

### Thumbnail formula (mandatory)

Match `character/thumb-reference.jpg`:

1. Scroll-stop hero MCU on one third; text on the other.
2. 2–3 soft thought-bubble vignettes of the **same** character — real beats from this video (places/people too).
3. On-image text names the actual topic accurately. Yellow paint stroke on the power phrase.
4. Do not invent claims the script does not make.

## Stills + thumbs API (Pollinations)

- Keys: `POLLINATIONS_KEYS.md` / `yt-image/.env` — rotate on `402`
- Model: **flux**
- Stills: **1920×1080** · Thumbs: **1280×720**

## Required flow

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-images\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$run\script.txt" --out $run --every 6
# Inspect segments.md: place / color / people / face must vary and match the story
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$run\prompts.txt" --out $run --width 1920 --height 1080
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$run\thumb_prompts.txt" --out $run --width 1280 --height 720
```

## Checklist

```
yt-image:
- [ ] prompts follow prompts.md (scene, people, color, face)
- [ ] segments.md shows changing place + color + people
- [ ] stills: Pollinations 1920×1080 (only if user wants render)
- [ ] thumbs: Pollinations 1280×720 collage + ≤3-word punch text
- [ ] POLLINATIONS keys in .env / POLLINATIONS_KEYS.md (not committed)
```

## Failure

Pollinations 402 → next pollen key; if all exhausted, stop and report how many finished — keep `prompts.txt`.
