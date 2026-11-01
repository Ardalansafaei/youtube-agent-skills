# yt-image prompt optimizer (Pollinations)

**Canonical character:** `character/CHARACTER.md` + `character/model-sheet.jpg`  
Face + hair + 2D style are locked. **Outfit changes with the environment** (`character/outfits.json`).

Rewrite concepts in English unless the user requires Persian. Always **prepend** `lock_prefix.txt`, add matching **outfit**, **append** `lock_negatives.txt`.

## Formula (order matters)

1. **Character lock prefix** (face/hair/style — required)
2. **Outfit for this scene** (from `outfits.json` — required)
3. **Shot type** — educational still 1920×1080 / thumbnail 1280×720
4. **Beat concept** — from `[ON SCREEN]` or spoken window
5. **Expression** — neutral, happy, thinking, surprised, curious, concerned, sad, explaining, confident, calm
6. **Scene** — desk / whiteboard / therapy / study / brain / cafe / outdoor / …
7. **Optional pink brain sidekick** — teaching/explaining only
8. **Negatives** — lock_negatives (do not forbid outfit change)

## Thumbnail template

```text
{lock_prefix} YouTube thumbnail frame 1280x720 16:9, same host character close-up or MCU, [expression], high contrast for feed, [optional bold text "WORD WORD"], {lock_negatives}
```

## Educational still template (every 6s)

```text
{lock_prefix} Educational YouTube still 1920x1080 16:9, [concept from ON SCREEN], half-body or full-body, [expression], [allowed scene], soft even lighting, {lock_negatives}
```

## Timeline stills

Use `scripts/build_still_prompts.py` (already injects the character lock). You may tighten the **concept** words only — do not remove the character lock or change outfit/hair.

## Rewrite checklist

- [ ] Character lock present (lavender sweatshirt + dark half-up bun + 2D)
- [ ] 16:9 size correct (1920×1080 still / 1280×720 thumb)
- [ ] One expression + one scene
- [ ] Not photoreal / not a different person
