---
name: yt-viral
description: >-
  After the user gives a YouTube topic, search YouTube for working/viral videos,
  explain why they pull views, extract shared tags, and feed packaging/SEO.
  Use for niche research, "what's working", competitor swipe, viral tags, or as
  step 1 of yt-agent before writing the script.
---

# yt-viral

**Step 1 of yt-agent:** topic → YouTube research → formulas + shared tags → then script/SEO.

Raw view counts rank channel size. Prefer **multiple over each channel's median** when enough
uploads are sampled. Tags are for disambiguation in `yt-seo`, not a growth strategy alone.

## Topic research (required for yt-agent)

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-research\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
python "$env:USERPROFILE\.claude\skills\yt-viral\research_topic.py" "TOPIC HERE" --out "$run\research.json" --max 12 --enrich 8
```

Needs: `pip install yt-dlp` (uses `python -m yt_dlp`).

**Public data only** — no logged-in scrape, no user credentials.

### What it produces

| File | Contents |
|------|----------|
| `research.json` | videos, why_views, shared_tags, recommended_tags |
| `research.md` | human summary |

### Hand back to the user / next skills

1. Top 5–8 videos with views, URL, title formula, and **why_views** bullets  
2. **ONE structural pattern** they share (from `shared_structure`)  
3. **`recommended_tags`** (≤15) → pass into `yt-seo`  
4. Winning title formulas → inform `yt-package` / `yt-script` (do **not** copy titles verbatim)  
5. Which angle the user can actually ship this week in their voice  

## Channel swipe (optional deeper pass)

Collect ≥4 videos per channel, then:

```bash
python swipe.py collected.json --min 2.0
```

```json
[{"channel":"...","title":"...","views":412000,"url":"...","duration":613}]
```

## The gate

Nothing publishes. End with research paths + tags list and: **ship the angle, or change it?**
