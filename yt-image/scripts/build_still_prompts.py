#!/usr/bin/env python3
"""Split a spoken YouTube script into one image prompt every N seconds (default 6).

    python build_still_prompts.py --file script.txt --out ./run
    python build_still_prompts.py --file script.txt --out ./run --every 6 --wpm 150

Writes:
  prompts.txt     name|prompt lines for generate_batch.py
  segments.json   timing + source text + prompt
  segments.md     human timeline

Still names (sort = play order):
  still_001_t0000-0006
  still_002_t0006-0012

Prompt grammar (mandatory layers):
  1) SCENE matching spoken beat (place + action)
  2) OTHER PEOPLE when the story is social
  3) OUTFIT + COLOR change vs previous still
  4) FACE emotion from expressions.json
  5) Atmosphere from atmospheres.json
  6) Character lock + negatives
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CHAR_DIR = Path(__file__).resolve().parents[1] / "character"
LOCK_PREFIX = (CHAR_DIR / "lock_prefix.txt").read_text(encoding="utf-8").strip()
LOCK_NEG = (CHAR_DIR / "lock_negatives.txt").read_text(encoding="utf-8").strip()
OUTFITS = json.loads((CHAR_DIR / "outfits.json").read_text(encoding="utf-8"))
EXPRESSIONS = json.loads((CHAR_DIR / "expressions.json").read_text(encoding="utf-8"))
SCENES = json.loads((CHAR_DIR / "scenes.json").read_text(encoding="utf-8"))
ATMOS = json.loads((CHAR_DIR / "atmospheres.json").read_text(encoding="utf-8"))

EXPR_MAP: dict[str, dict] = EXPRESSIONS.get("expressions") or {}
EXPR_DEFAULT = str(EXPRESSIONS.get("default") or "explaining")
WARDROBE: list[dict] = list(OUTFITS.get("wardrobe") or [])
BY_PLACE: dict = OUTFITS.get("by_place") or {}
PLACE_FALLBACKS: dict = SCENES.get("place_fallbacks") or {}
BEATS: list[dict] = list(SCENES.get("beats") or [])
ATMOS_BY_EXPR: dict = ATMOS.get("by_expression") or {}

CAMERAS = [
    "medium-wide shot showing the full location",
    "medium close-up with environment readable behind her",
    "over-the-shoulder shot including the other person",
    "close-up on face and hands with background people soft",
    "full-body wide shot of the place and cast",
    "low-angle dramatic shot in the real location",
    "high-angle looking down on the social space",
    "profile three-quarter shot with depth to the room",
]

# Prompt order: scene/people/outfit before face lock so the world is not ignored
TEMPLATE = (
    "SCENE FIRST (must match the spoken story beat): {environment}. "
    "ACTION: {action}. "
    "OTHER PEOPLE IN FRAME: {people}. "
    "WARDROBE CHANGE: she wears {outfit} (dominant clothing color: {color}) — different cut and color from adjacent stills. "
    "ATMOSPHERE: {atmosphere}. "
    "FACE EMOTION: {expression}. No cute default smile on distress beats. "
    "{lock}. Educational YouTube still 1920x1080 16:9, {camera} of the same host character in this exact place, "
    "{lighting}, high resolution, no text overlays, {neg}"
)


def expression_prompt(expr_id: str) -> str:
    entry = EXPR_MAP.get(expr_id) or EXPR_MAP.get(EXPR_DEFAULT) or {}
    return str(entry.get("prompt") or "clear teaching expression matching the beat")


def pick_expression_id(concept: str, spoken: str, recipe_hint: str = "") -> str:
    blob = f"{concept} {spoken} {recipe_hint}".lower()
    scored: list[tuple[int, int, str]] = []
    for expr_id, entry in EXPR_MAP.items():
        pri = int(entry.get("priority") or 0)
        for kw in entry.get("keywords") or []:
            kw_l = str(kw).lower()
            if kw_l and kw_l in blob:
                scored.append((pri, len(kw_l), expr_id))
    if scored:
        scored.sort(reverse=True)
        return scored[0][2]
    if re.search(r"\b(anxiety|anxious|fear|shame|embarrass|avoid|threat)\b", blob):
        return "anxiety"
    return EXPR_DEFAULT


def wardrobe_by_id(wid: str) -> dict:
    for item in WARDROBE:
        if item.get("id") == wid:
            return item
    return WARDROBE[0] if WARDROBE else {"id": "default", "color": "lavender", "outfit": "lavender sweater"}


def pick_outfit(place: str, seg_i: int, prev_color: str | None) -> dict:
    """Pick wardrobe for place; force a different dominant color than previous still."""
    preferred_ids = list(BY_PLACE.get(place) or [])
    pool_ids = preferred_ids or [w.get("id") for w in WARDROBE]
    # rotate through pool, skip same color as previous when possible
    for offset in range(len(pool_ids) or 1):
        wid = pool_ids[(seg_i + offset) % len(pool_ids)]
        item = wardrobe_by_id(str(wid))
        if prev_color and str(item.get("color") or "").lower() == prev_color.lower():
            continue
        return item
    # fall back to any wardrobe with different color
    for offset in range(len(WARDROBE)):
        item = WARDROBE[(seg_i + offset) % len(WARDROBE)]
        if prev_color and str(item.get("color") or "").lower() == prev_color.lower():
            continue
        return item
    return wardrobe_by_id(str(pool_ids[seg_i % len(pool_ids)])) if pool_ids else wardrobe_by_id("lavender_sweater")


def match_beat(blob: str) -> dict | None:
    """Longest keyword hit among scenes.json beats."""
    best: tuple[int, dict] | None = None
    for beat in BEATS:
        for key in beat.get("keys") or []:
            kw = str(key).lower()
            if kw and kw in blob:
                score = len(kw)
                if best is None or score > best[0]:
                    best = (score, beat)
    return best[1] if best else None


def infer_place(blob: str) -> str:
    heuristics = [
        (r"\b(party|crowd|invite|guests)\b", "party"),
        (r"\b(cafe|coffee|barista)\b", "cafe"),
        (r"\b(elevator)\b", "elevator"),
        (r"\b(hallway|corridor)\b", "hallway"),
        (r"\b(meeting|mixer|networking)\b", "meeting"),
        (r"\b(office|coworker|workplace)\b", "office"),
        (r"\b(bar|drink|buddy)\b", "bar"),
        (r"\b(bookstore|checkout)\b", "bookstore"),
        (r"\b(mirror|rehears)\b", "bathroom_mirror"),
        (r"\b(therap|clinician)\b", "therapy"),
        (r"\b(parking|car)\b", "parking"),
        (r"\b(bed|night|hangover)\b", "bed"),
        (r"\b(outdoor|street|sidewalk|commute)\b", "outdoor"),
        (r"\b(comment|education|teach)\b", "studio"),
        (r"\b(home|couch)\b", "home"),
    ]
    for pat, place in heuristics:
        if re.search(pat, blob, re.I):
            return place
    return "cafe"


def social_people_needed(blob: str, place: str) -> bool:
    if place in {"studio", "bed", "study"} and not re.search(
        r"\b(crowd|friend|people|conversation|coworker|barista|guest)\b", blob, re.I
    ):
        return False
    if re.search(
        r"\b(alone|by herself|empty room|direct to camera|disclaimer|comment)\b", blob, re.I
    ) and place in {"studio", "therapy", "home"}:
        return False
    return True


def compose_scene(
    concept: str,
    spoken: str,
    seg_i: int,
    prev_place: str | None,
    prev_color: str | None,
) -> dict:
    blob = f"{concept} {spoken}".lower()
    beat = match_beat(blob)
    if beat:
        place = str(beat.get("place") or infer_place(blob))
        environment = str(beat.get("environment") or "")
        people = str(beat.get("people") or "")
        action = str(beat.get("action") or "")
        lighting = str(beat.get("lighting") or "")
        recipe = "beat:" + ",".join((beat.get("keys") or ["?"])[:1])
    else:
        place = infer_place(blob)
        # avoid repeating the exact same place back-to-back when possible
        if prev_place and place == prev_place:
            alts = [p for p in ("cafe", "hallway", "office", "outdoor", "bookstore") if p != prev_place]
            place = alts[seg_i % len(alts)]
        fb = PLACE_FALLBACKS.get(place) or {}
        snippet = " ".join(re.findall(r"[A-Za-z']+", spoken)[:14]) or concept
        environment = str(fb.get("environment") or f"location matching spoken beat: {snippet}")
        people = str(fb.get("people") or "soft-focus background people when the beat is social")
        action = f"acting out the spoken beat: {snippet}"
        lighting = str(fb.get("lighting") or CAMERAS[seg_i % len(CAMERAS)])
        recipe = f"fallback:{place}"

    if prev_place and place == prev_place:
        # force a readable location shift while keeping story sense
        environment = environment + f", alternate corner/angle of the same story world (variation {seg_i + 1})"

    if not social_people_needed(blob, place):
        if "none" not in people.lower() and "alone" not in people.lower():
            people = "no crowd required — keep focus on host (beat is private/direct-to-camera)"
    elif "none" in people.lower() and social_people_needed(blob, place):
        people = "at least one other soft-focus person present so the social story reads"

    outfit_item = pick_outfit(place, seg_i, prev_color)
    expr_id = pick_expression_id(concept, spoken, recipe)
    atmosphere = str(ATMOS_BY_EXPR.get(expr_id) or ATMOS_BY_EXPR.get(EXPR_DEFAULT) or "readable story atmosphere")

    return {
        "place": place,
        "environment": environment,
        "people": people,
        "action": action,
        "lighting": lighting or "cinematic practical lighting matching the place",
        "recipe": recipe,
        "outfit": str(outfit_item.get("outfit")),
        "color": str(outfit_item.get("color")),
        "outfit_id": str(outfit_item.get("id")),
        "expression_id": expr_id,
        "expression": expression_prompt(expr_id),
        "atmosphere": atmosphere,
        "camera": CAMERAS[seg_i % len(CAMERAS)],
    }


def strip_directions_keep_map(text: str) -> tuple[str, list[tuple[int, str]]]:
    ons: list[tuple[int, str]] = []
    spoken_parts: list[str] = []
    pos = 0
    for m in re.finditer(r"\[ON SCREEN:\s*([^\]]*)\]", text, flags=re.I):
        spoken_parts.append(text[pos : m.start()])
        spoken_so_far = "".join(spoken_parts)
        cue = m.group(1).strip()
        if cue:
            ons.append((len(spoken_so_far), cue))
        pos = m.end()
    spoken_parts.append(text[pos:])
    spoken = "".join(spoken_parts)
    spoken = re.sub(r"\[(?:B-?ROLL|VISUAL|SHOT|CUT|SFX|MUSIC)[^\]]*\]", " ", spoken, flags=re.I)
    spoken = re.sub(r"[ \t]+", " ", spoken)
    spoken = re.sub(r"\n{3,}", "\n\n", spoken).strip()
    return spoken, ons


def words_of(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def concept_from_segment(seg_text: str, on_screen: str | None) -> str:
    if on_screen:
        concept = on_screen.strip().rstrip(".")
        return concept[0].lower() + concept[1:] if concept else "abstract idea as a simple visual metaphor"
    clean = re.sub(r"[^\w\s'-]", " ", seg_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    words = clean.split()
    snippet = " ".join(words[:18]) if words else "a clear visual metaphor for the spoken idea"
    return f"visual metaphor for: {snippet}"


def nearest_on_screen(char_start: int, ons: list[tuple[int, str]]) -> str | None:
    if not ons:
        return None
    before = [c for c in ons if c[0] <= char_start]
    if before:
        return before[-1][1]
    return min(ons, key=lambda c: abs(c[0] - char_start))[1]


def build_segments(spoken: str, ons: list[tuple[int, str]], every: float, wpm: float) -> list[dict]:
    words = words_of(spoken)
    if not words:
        return []
    words_per_seg = max(1, int(round(wpm * every / 60.0)))
    segments: list[dict] = []
    char_at_word: list[int] = []
    cursor = 0
    for w in words:
        idx = spoken.find(w, cursor)
        if idx < 0:
            idx = cursor
        char_at_word.append(idx)
        cursor = idx + len(w)

    i = 0
    seg_i = 0
    prev_place: str | None = None
    prev_color: str | None = None
    while i < len(words):
        chunk = words[i : i + words_per_seg]
        start_w = i
        t0 = seg_i * every
        t1 = t0 + every
        char_start = char_at_word[start_w] if start_w < len(char_at_word) else 0
        seg_text = " ".join(chunk)
        cue = nearest_on_screen(char_start, ons)
        concept = concept_from_segment(seg_text, cue)
        scene = compose_scene(concept, seg_text, seg_i, prev_place, prev_color)
        prompt = TEMPLATE.format(
            environment=scene["environment"],
            action=scene["action"],
            people=scene["people"],
            outfit=scene["outfit"],
            color=scene["color"],
            atmosphere=scene["atmosphere"],
            expression=scene["expression"],
            lock=LOCK_PREFIX,
            camera=scene["camera"],
            lighting=scene["lighting"],
            neg=LOCK_NEG,
        )
        seq = seg_i + 1
        name = f"still_{seq:03d}_t{int(t0):04d}-{int(t1):04d}"
        segments.append(
            {
                "index": seq,
                "name": name,
                "t_start_sec": round(t0, 2),
                "t_end_sec": round(t1, 2),
                "spoken": seg_text,
                "on_screen": cue,
                "concept": concept,
                "place": scene["place"],
                "scene": scene["place"],
                "environment": scene["environment"],
                "people": scene["people"],
                "action": scene["action"],
                "outfit": scene["outfit"],
                "color": scene["color"],
                "outfit_id": scene["outfit_id"],
                "camera": scene["camera"],
                "lighting": scene["lighting"],
                "atmosphere": scene["atmosphere"],
                "recipe": scene["recipe"],
                "expression_id": scene["expression_id"],
                "expression": scene["expression"],
                "prompt": prompt,
            }
        )
        prev_place = scene["place"]
        prev_color = scene["color"]
        i += words_per_seg
        seg_i += 1
    return segments


def main() -> int:
    p = argparse.ArgumentParser(description="Build 1 Pollinations prompt per N seconds of script")
    p.add_argument("--file", type=Path, required=True, help="Script file")
    p.add_argument("--out", type=Path, required=True, help="Output directory")
    p.add_argument("--every", type=float, default=6.0, help="Seconds per still (default 6)")
    p.add_argument("--wpm", type=float, default=150.0, help="Words per minute for timing")
    args = p.parse_args()

    raw = args.file.read_text(encoding="utf-8-sig")
    spoken, ons = strip_directions_keep_map(raw)
    if not spoken:
        print("empty spoken script", file=sys.stderr)
        return 1

    segments = build_segments(spoken, ons, args.every, args.wpm)
    word_count = len(words_of(spoken))
    duration_sec = word_count / args.wpm * 60.0

    args.out.mkdir(parents=True, exist_ok=True)
    prompts_path = args.out / "prompts.txt"
    lines = [f"{s['name']}|{s['prompt']}" for s in segments]
    prompts_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "source": str(args.file),
        "every_sec": args.every,
        "wpm": args.wpm,
        "word_count": word_count,
        "estimated_duration_sec": round(duration_sec, 1),
        "still_count": len(segments),
        "rule": f"1 image prompt every {args.every}s",
        "prompt_grammar": [
            "scene matching spoken beat",
            "other people when social",
            "outfit+color change vs previous",
            "face emotion",
            "atmosphere",
            "character lock",
        ],
        "segments": segments,
    }
    (args.out / "segments.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        f"# Still prompts every {args.every:g}s",
        "",
        f"Words: {word_count} · Est. duration: {duration_sec/60:.1f} min · Stills: {len(segments)}",
        "",
        "| # | file | time | place | color | face | people |",
        "|---|------|------|-------|-------|------|--------|",
    ]
    for s in segments:
        people_short = (s.get("people") or "")[:40].replace("|", "/")
        md.append(
            f"| {s['index']} | `{s['name']}` | {s['t_start_sec']:.0f}–{s['t_end_sec']:.0f}s | "
            f"{s.get('place')} | {s.get('color')} | `{s.get('expression_id')}` | {people_short} |"
        )
    md.append("")
    for s in segments:
        md.append(
            f"- **{s['index']:03d}** `{s['name']}` [{s.get('recipe')}]  \n"
            f"  place: {s.get('place')} · color: {s.get('color')} · face: `{s.get('expression_id')}`  \n"
            f"  env: {str(s.get('environment'))[:120]}  \n"
            f"  people: {str(s.get('people'))[:120]}  \n"
            f"  spoken: {s['spoken'][:100]}"
        )
    (args.out / "segments.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"stills={len(segments)} duration_sec={duration_sec:.1f} -> {prompts_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
