# Channel character lock — Psychiatry Learning Companion

**Canonical reference:** `model-sheet.jpg`  
Face, hair, art style stay fixed. **Outfit changes with the environment.**

## Fixed identity
- Young woman host, clean modern **2D** illustration
- Long wavy dark brown hair, half-up messy bun
- Large expressive dark eyes, soft friendly face
- Palette family: lavender `#7B6CF6`, pink `#E8A5C4`, sage `#A8C5A0`, cream `#F2E5D3`, charcoal `#333333`
- Optional sidekick: cute pink brain (teaching/explaining beats)

## Outfit by environment (required)

| Scene / environment | Outfit |
|---------------------|--------|
| Desk / talking at home | Cozy lavender knit or lilac crewneck, dark pants |
| Whiteboard / teaching | Lilac or cream blouse + soft purple cardigan, dark tailored pants |
| Therapy room | Sage or cream cardigan over light top, charcoal pants |
| Study / notes | Oversized lavender hoodie/sweatshirt, dark pants, white sneakers |
| Inside-the-brain metaphor | Fitted lavender top, dark pants; pink brain sidekick OK |
| Cafe | Cream top + lilac cardigan, dark pants, sneakers |
| Outdoor | Lavender jacket/cardigan over cream tee, dark jeans |
| Formal / interview energy | Lilac blouse ± soft blazer, charcoal trousers |
| Sleep / night anxiety | Soft lavender loungewear |
| Exercise / body cues | Light athletic lavender + charcoal |

Always stay in the pastel lavender/sage/cream/charcoal family — change the **cut**, not the brand identity.

## Expressions
neutral · happy · thinking · surprised · curious · concerned · sad · explaining · confident · calm

## Prompt rules
1. Prepend `lock_prefix.txt` (face/hair/style only — no fixed outfit).
2. Add the outfit line that matches the scene.
3. Append `lock_negatives.txt`.
4. `build_still_prompts.py` picks outfit from `outfits.json` using ON SCREEN / concept keywords.
