# yt-image prompt optimizer (Pollinations)

**Canonical character:** `character/CHARACTER.md` + `character/model-sheet.jpg`  
Face + hair + **3D Pixar/Disney** style are locked. **Outfit and environment change every beat.**

Rewrite concepts in English unless the user requires Persian. Always **prepend** `lock_prefix.txt`, add matching **outfit**, **append** `lock_negatives.txt`.

## Formula — timeline stills (order matters)

1. Character lock prefix (3D face/hair/style)
2. Outfit for this scene (`outfits.json`)
3. Shot size: Educational YouTube still 1920×1080 16:9
4. **Unique** camera + environment + action from the beat / `[ON SCREEN]`
5. Expression matching the emotion
6. Lighting that fits the place (not always soft even desk light)
7. Negatives

## Anti-repetition

- Change environment **or** action every still; prefer both.
- Never reuse the exact desk-laptop pose for adjacent beats.
- Background people only as soft silhouettes when needed.

## Thumbnail formula (OpenAI only — 1280×720)

**Backend:** `generate_thumb_openai.py` (never Pollinations for thumbs).

Lead with **accurate topic + exact on-image text + layout + emotion**. Match `thumb-reference.jpg`.

**Accuracy rule:** on-image words must name the real subject (`SOCIAL ANXIETY`, etc.) and the real deliverable (signs / vs shyness / skills). Never ship vague text like only `7 SIGNS` with no topic. Vignettes must match beats that exist in the script.

```text
YouTube thumbnail 1280x720 about [exact topic from the video].
RIGHT/LEFT: giant MCU of 3D Pixar young woman (dark messy half-up bun, freckles, big brown eyes) [emotion/pose], cinematic warm light.
Opposite side: exact bold text "[ACCURATE CONTENT PHRASE]" — power words on bright yellow paint stroke, perfect spelling, phone-readable.
2 soft circular thought-bubbles of the SAME girl showing [real script beats].
High contrast, no tiny subtitle paragraphs, not photoreal, not flat 2D.
```

## Checklist

- [ ] 3D Pixar lock (not flat 2D / not photoreal)
- [ ] 16:9 size correct
- [ ] Unique scene per still
- [ ] Thumb = hero + vignettes + bold text
