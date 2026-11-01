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

## Thumbnail formula (1280×720 collage)

Match `character/thumb-reference.jpg`:

```text
{lock_prefix} YouTube thumbnail 1280x720 16:9, high-contrast feed design,
RIGHT side: large hero MCU of same 3D host [calm thoughtful pose],
LEFT/background: 3-4 vignette panels or thought-bubbles of the SAME character in different emotional beats
(phone stress with scribble bubble, crowded social anxiety, sad overwhelm, calm eyes-closed heart bubble),
BOLD readable title text on the free side: short punch line + one accent word on yellow paint stroke if needed,
thin subtitle optional, cinematic warm lighting, {lock_negatives}
```

Do not ship single empty-space thumbs without vignettes and bold title text.

## Checklist

- [ ] 3D Pixar lock (not flat 2D / not photoreal)
- [ ] 16:9 size correct
- [ ] Unique scene per still
- [ ] Thumb = hero + vignettes + bold text
