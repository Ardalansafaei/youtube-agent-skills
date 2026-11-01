---
name: yt-image
description: >-
  Build one Pollinations image prompt every 6 seconds of the YouTube script,
  then generate stills at 1920×1080; thumbnails at 1280×720 via Puter.js
  (free OpenAI GPT Image) with optional direct-OpenAI fallback.
---

# yt-image — stills (Pollinations) + thumbs (Puter → OpenAI)

## Character (mandatory)

Canonical host: `character/model-sheet.jpg` (+ `model-sheet-alt.jpg`) + `character/CHARACTER.md`

**Art style (locked):** 3D CGI Pixar/Disney — smooth stylized render, soft subsurface skin, cinematic depth of field.  
**Not** flat 2D, **not** anime, **not** photoreal / live-action.

Face + hair locked (messy dark-brown half-up bun, freckles, large brown eyes).  
**Outfit and environment change every beat** via `outfits.json` + scene library in `build_still_prompts.py`.

## Anti-repetition (mandatory for stills)

Every still must change **at least two** of: environment, action/pose, camera angle, lighting.  
Never chain the same desk-laptop pose.

## Size rules (mandatory)

| Asset | Size | Aspect | Backend |
|-------|------|--------|---------|
| **Timeline stills** (every 6s) | **1920×1080** | 16:9 | Pollinations (`generate.py`) |
| **Upload thumbnail** | **1280×720** | 16:9 | **Puter.js** `puter.ai.txt2img` → GPT Image (`generate_thumb_puter.mjs`) |

**Always 16:9.** `thumb_*` lines in `generate_batch.py` route to Puter when `PUTER_AUTH_TOKEN` is set; otherwise fall back to direct OpenAI.

## Thumbnails via Puter (preferred — free OpenAI GPT Image)

Docs: https://developer.puter.com/tutorials/free-unlimited-openai-api/

No OpenAI billing key required. User-Pays via Puter account.

```powershell
# one-time: npm install inside yt-image/scripts (uses @heyputer/puter.js)
# token from https://puter.com/dashboard#account → yt-image/.env as PUTER_AUTH_TOKEN=

node "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_thumb_puter.mjs" `
  --file "$thumb\prompts.txt" --out $thumb `
  --model gpt-image-2.5-flare --width 1280 --height 720
```

Models: `gpt-image-2.5-flare` (default) · `gpt-image-2.5-sunburst` · `gpt-image-2` · `gpt-image-1.5`  
Optional: `--browser-auth` once if no token yet.

### Thumbnail formula (mandatory)

Match `character/thumb-reference.jpg`:

1. Scroll-stop hero MCU on one third; text on the other.
2. 2–3 soft thought-bubble vignettes of the **same** character — vignettes must show **real beats from this video**, not random mood shots.
3. **On-image text must name the actual topic accurately** (e.g. `SOCIAL ANXIETY`, not vague `7 SIGNS` alone). State the deliverable: signs / vs shyness / skills. Yellow paint stroke on the power phrase. Short enough for phone feed, but never misleading or incomplete.
4. Prompt = accurate topic + exact on-image text + layout + emotion. Do not invent claims the script does not make.

## Stills API (Pollinations)

- Keys: `POLLINATIONS_KEYS.md` — rotate on `402`
- Model: **flux** · size **1920×1080**

## Fallback (direct OpenAI)

Only if Puter token missing: `generate_thumb_openai.py` + `OPENAI_KEYS.md` / `OPENAI_API_KEY`.

## Required flow

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-images\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$run\script.txt" --out $run --every 6
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$run\prompts.txt" --out $run --width 1920 --height 1080
node "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_thumb_puter.mjs" --file "$run\thumb_prompts.txt" --out $run --model gpt-image-2.5-flare
```

## Checklist

```
yt-image:
- [ ] stills: Pollinations 1920×1080
- [ ] thumbs: Puter GPT Image 1280×720 collage + ≤3-word text
- [ ] PUTER_AUTH_TOKEN in .env (not committed)
```

## Optional thumb backend — Cloudflare Workers AI

User API token prefix `cfut_` plus a separate **Account ID** (email alone is not enough).  
Model: `@cf/black-forest-labs/flux-1-schnell`.  
Do **not** send `width`/`height` (API returns 400). Output is square **1024×1024**, not 1280×720.  
On-image text still must name the real topic; long sentences garble — keep the exact short phrase (`7 SIGNS OF SOCIAL ANXIETY`, `SOCIAL ANXIETY VS SHYNESS`, `3 SKILLS FOR SOCIAL ANXIETY`).  
Store `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` only in local `.env`. Never commit them.

## Failure

Pollinations 402 → next pollen key.  
Puter auth missing → ask for token / `--browser-auth`.  
Do **not** silently fall thumbs back to Pollinations.
