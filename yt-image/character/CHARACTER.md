# Channel character lock — Psychiatry Learning Companion

**Canonical reference:** `model-sheet.jpg` (+ `model-sheet-alt.jpg`)  
Face, hair, and **3D Pixar-style** art stay fixed.  
**Place, other people, outfit cut/color, atmosphere, and facial emotion change every beat.**

## Fixed identity
- Young woman host, clean modern **3D CGI / Pixar-Disney** look (not flat 2D, not photoreal)
- Long voluminous dark brown wavy hair, messy half-up top bun, loose waves framing face
- Large expressive brown eyes, light freckles, soft friendly face
- Optional sidekick: cute pink brain (teaching/explaining beats only)

## Wardrobe (must change cut + color)

Source of truth: `outfits.json` → `wardrobe` + `by_place`.

Face/hair never change. Clothing **cut and dominant color** should change between adjacent stills  
(lavender, sage, cream, teal, dusty rose, soft blue, olive, coral, charcoal, mauve, mint, wine, …).

Do **not** keep the same lavender sweater in every frame.

## Scenes + other people

Source of truth: `scenes.json`.

- Environment must match the **spoken story beat** (cafe silence, party exit, elevator, hallway hello, bar-with-buddy, therapy disclaimer, …).
- When the beat is social, **other people must be in frame** (soft-focus is OK; total empty rooms are not).
- Private / direct-to-camera / disclaimer beats may be alone.

## Shot rules (anti-repetition)
1. Unique **place + action + camera** every still.
2. Change wardrobe **color** vs the previous still when possible.
3. Background people as soft out-of-focus figures — never extra sharp faces competing with the host.
4. Prompt order: scene → people → outfit/color → atmosphere → face → lock → negatives (`prompts.md`).

## Expressions (mandatory)

Canonical grammar: `expressions.json` (+ mood space in `atmospheres.json`).

Never keep a calm/default smile on fear, shame, embarrassment, or anxiety beats.  
Each still prompt must include the **full facial prompt string**, not just a one-word label.
