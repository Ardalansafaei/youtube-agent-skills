# yt-image prompt writing (mandatory)

**Canonical character:** `character/CHARACTER.md` + `character/model-sheet.jpg`  
Face + hair + **3D Pixar/Disney** style are locked.  
**World, wardrobe color, other people, and face emotion change every beat** and must match the spoken story.

Rewrite concepts in English unless the user requires Persian.  
Builder: `scripts/build_still_prompts.py` loads:

| File | Role |
|------|------|
| `lock_prefix.txt` | Face/hair/style lock |
| `outfits.json` | Wardrobe cuts + **colors** (must change vs previous still) |
| `scenes.json` | Place / environment / action / **other people** from story keywords |
| `expressions.json` | Facial acting for psychology |
| `atmospheres.json` | Lighting/space mood tied to emotion |
| `lock_negatives.txt` | Hard bans |

## Correct still-prompt order (do not reorder)

1. **SCENE FIRST** — concrete place + props matching the spoken beat / `[ON SCREEN]`
2. **ACTION** — what the host is doing in that beat
3. **OTHER PEOPLE** — when the story is social (cafe, party, meeting, elevator, hello, conversation…), put real soft-focus others in frame. Private/direct-to-camera beats may be alone.
4. **WARDROBE + COLOR** — different cut **and** dominant color from the previous still (`outfits.json` wardrobe)
5. **ATMOSPHERE** — from `atmospheres.json` for the chosen emotion
6. **FACE EMOTION** — full string from `expressions.json` (not a one-word label)
7. **Character lock** (`lock_prefix.txt`)
8. Shot size + camera + lighting for that place
9. **Negatives** (`lock_negatives.txt`)

### Bad vs good

Bad: same lavender sweater, empty pretty room, calm smile, “visual metaphor for the line”.  
Good: cafe silence with a person across the table, dusty-rose sweater, phone-escape face, soft patrons behind her.

## Story match rules

- Environment must be **readable and different** across adjacent stills (party wall ≠ cafe table ≠ elevator ≠ hallway ≠ therapy room).
- If the line mentions conversation, silence, hello, crowd, coworker, barista, buddy, meeting → **other people must appear**.
- Outfit **color** must change when possible between stills (lavender → sage → cream → teal → dusty rose → …).
- Face must match psychology (fear / shame / embarrassment / phone_escape / fake_confidence / …).
- Never default cute smile on distress beats.

## Emotion grammar (shortcut)

- Threat / dangerous room → `fear` / `anxiety` + crowded or exposing place + people
- Phone in silence → `phone_escape` + person waiting across from her
- Rehearsal → `rehearsing` + mirror / lounge people beyond the door
- Fake confidence → `fake_confidence` + mixer/meeting circle of colleagues
- Buddy armor → `avoidant` / anxiety + bar buddy as shield + patrons
- Tiny hello / nod → `brave_tense` + visible other person receiving the hello
- Disclaimer → `concerned` + therapy-like room

## Anti-repetition

Every still must change **at least two** of: place, wardrobe color, people setup, camera, lighting.  
Never chain the same desk-laptop pose.  
Never reuse the same empty cream living room for every beat.

## File naming (sort = timeline)

```text
still_001_t0000-0006.jpg
still_002_t0006-0012.jpg
still_003_t0012-0018.jpg
```

## Thumbnail formula (Pollinations — 1280×720)

Lead with **accurate topic + exact on-image text + layout + emotion**. Match `thumb-reference.jpg`.

```text
YouTube thumbnail 1280x720 about [exact topic from the video].
RIGHT/LEFT: giant MCU of 3D Pixar young woman (dark messy half-up bun, freckles, big brown eyes) [emotion/pose], cinematic warm light.
Opposite side: exact bold text "[ACCURATE CONTENT PHRASE]" — power words on bright yellow paint stroke, perfect spelling, phone-readable.
2 soft circular thought-bubbles of the SAME girl showing [real script beats with matching places/people].
High contrast, no tiny subtitle paragraphs, not photoreal, not flat 2D.
```

## Checklist

- [ ] Scene matches spoken beat (not generic room)
- [ ] Other people present when social
- [ ] Outfit **and color** changed vs previous still
- [ ] Face emotion + atmosphere match psychology
- [ ] 3D Pixar lock (not flat 2D / not photoreal)
- [ ] 16:9 size correct · sorted `still_NNN_t…` names
