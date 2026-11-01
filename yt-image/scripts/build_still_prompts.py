#!/usr/bin/env python3
"""Split a spoken YouTube script into one image prompt every N seconds (default 6).

    python build_still_prompts.py --file script.txt --out ./run
    python build_still_prompts.py --file script.txt --out ./run --every 6 --wpm 150

Writes:
  prompts.txt     name|prompt lines for generate_batch.py
  segments.json   timing + source text + prompt
  segments.md     human timeline
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

TEMPLATE = (
    "{lock} wearing {outfit}, Educational YouTube still 1920x1080 16:9, {concept}, "
    "scene/environment: {scene}, same host character half-body or full-body as fits the beat, "
    "expression matching the moment, outfit matches this environment, "
    "soft even lighting, clean composition for YouTube video frame, high resolution, "
    "no text overlays, {neg}"
)


def pick_scene_and_outfit(concept: str, spoken: str) -> tuple[str, str]:
    blob = f"{concept} {spoken}".lower()
    by_scene: dict = OUTFITS.get("by_scene") or {}
    # longer keys first for better match (e.g. "therapy room" before "therapy")
    keys = sorted(by_scene.keys(), key=len, reverse=True)
    for key in keys:
        if key.lower() in blob:
            return key, by_scene[key]
    # heuristic fallbacks
    heuristics = [
        (r"\b(whiteboard|teach|explain|lecture)\b", "whiteboard"),
        (r"\b(therap|couch|armchair|session)\b", "therapy"),
        (r"\b(notebook|study|notes|homework)\b", "study"),
        (r"\b(brain|neuron|neural)\b", "brain"),
        (r"\b(cafe|coffee)\b", "cafe"),
        (r"\b(outdoor|outside|street|park)\b", "outdoor"),
        (r"\b(sleep|night|bed|insomnia)\b", "sleep"),
        (r"\b(run|gym|exercise|workout)\b", "exercise"),
        (r"\b(desk|laptop|computer)\b", "desk"),
    ]
    for pat, scene in heuristics:
        if re.search(pat, blob, re.I) and scene in by_scene:
            return scene, by_scene[scene]
    return "default", OUTFITS.get("default") or by_scene.get("desk", "cozy lavender outfit")


def strip_directions_keep_map(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Return spoken text and list of (char_index_in_spoken, on_screen_text)."""
    ons: list[tuple[int, str]] = []
    spoken_parts: list[str] = []
    pos = 0
    for m in re.finditer(r"\[ON SCREEN:\s*([^\]]*)\]", text, flags=re.I):
        spoken_parts.append(text[pos : m.start()])
        # index in upcoming spoken string
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
    # fallback: compress spoken words into a visualizable phrase
    clean = re.sub(r"[^\w\s'-]", " ", seg_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    words = clean.split()
    snippet = " ".join(words[:18]) if words else "a clear visual metaphor for the spoken idea"
    return f"visual metaphor for: {snippet}"


def nearest_on_screen(char_start: int, ons: list[tuple[int, str]]) -> str | None:
    if not ons:
        return None
    # last cue at or before this segment start, else closest
    before = [c for c in ons if c[0] <= char_start]
    if before:
        return before[-1][1]
    return min(ons, key=lambda c: abs(c[0] - char_start))[1]


def build_segments(spoken: str, ons: list[tuple[int, str]], every: float, wpm: float) -> list[dict]:
    words = words_of(spoken)
    if not words:
        return []
    words_per_seg = max(1, int(round(wpm * every / 60.0)))  # 150 wpm * 6/60 = 15
    segments: list[dict] = []
    # map word index → char index approx
    char_at_word: list[int] = []
    cursor = 0
    for i, w in enumerate(words):
        idx = spoken.find(w, cursor)
        if idx < 0:
            idx = cursor
        char_at_word.append(idx)
        cursor = idx + len(w)

    i = 0
    seg_i = 0
    while i < len(words):
        chunk = words[i : i + words_per_seg]
        start_w = i
        end_w = i + len(chunk) - 1
        t0 = seg_i * every
        t1 = t0 + every
        char_start = char_at_word[start_w] if start_w < len(char_at_word) else 0
        seg_text = " ".join(chunk)
        cue = nearest_on_screen(char_start, ons)
        concept = concept_from_segment(seg_text, cue)
        scene, outfit = pick_scene_and_outfit(concept, seg_text)
        prompt = TEMPLATE.format(
            lock=LOCK_PREFIX,
            outfit=outfit,
            concept=concept,
            scene=scene,
            neg=LOCK_NEG,
        )
        name = f"still_{int(t0):04d}_{int(t1):04d}"
        segments.append(
            {
                "index": seg_i + 1,
                "name": name,
                "t_start_sec": round(t0, 2),
                "t_end_sec": round(t1, 2),
                "spoken": seg_text,
                "on_screen": cue,
                "concept": concept,
                "scene": scene,
                "outfit": outfit,
                "prompt": prompt,
            }
        )
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
    ]
    for s in segments:
        md.append(
            f"- `{s['name']}` ({s['t_start_sec']:.0f}–{s['t_end_sec']:.0f}s)  \n"
            f"  spoken: {s['spoken'][:100]}  \n"
            f"  prompt: {s['prompt'][:140]}…"
        )
    (args.out / "segments.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"stills={len(segments)} duration_sec={duration_sec:.1f} -> {prompts_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
