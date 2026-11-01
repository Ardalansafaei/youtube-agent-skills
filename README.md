# YouTube Agent Skills

Cursor/Claude agent skills for end-to-end YouTube production.

## Pipeline

1. **Topic** → `yt-viral` (find working videos, why views, shared tags)
2. **Script** → `yt-script` (hooks + story + `[ON SCREEN]` ~every 6s)
3. **Audio** → `yt-tts` (Edge-TTS → `voiceover.mp3`)
4. **Stills** → `yt-image` (1 prompt / 6s → Pollinations, **1920×1080**)
5. **Packaging** → `yt-package` + thumbnails **1280×720**
6. **SEO** → `yt-seo` (uses `recommended_tags` from research)

## Install

Copy skill folders into:

```text
%USERPROFILE%\.claude\skills\
```

Optional config:

```text
%USERPROFILE%\.claude\youtube\agent.md
```

(from `youtube-config/agent.md`)

### Secrets (not in git)

Create `yt-image/.env`:

```env
POLLINATIONS_API_KEY=sk_...
```

### Dependencies

```powershell
pip install edge-tts yt-dlp
```

## Character

Locked 2D host in `yt-image/character/` (model sheet). Face/hair fixed; **outfit changes by scene** (`outfits.json`).

## Defaults

| Asset | Backend | Size / notes |
|-------|---------|----------------|
| Stills | Pollinations / flux | 1920×1080, every 6s |
| Thumbnail | Pollinations | 1280×720 |
| Voiceover | Edge-TTS `en-US-AndrewNeural` | free, chunked |
| Research | `yt-dlp` | public data only |

Arena / Gemini TTS only if requested by name.
