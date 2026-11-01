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

CAMERAS = [
    "medium-wide shot",
    "medium close-up",
    "over-the-shoulder shot",
    "close-up on face and hands",
    "full-body wide shot",
    "low-angle dramatic shot",
    "high-angle looking down",
    "profile three-quarter shot",
]

LIGHTS = [
    "soft warm window light, cinematic depth of field",
    "cool evening blue light with warm practical lamps",
    "harsh fluorescent office lighting",
    "golden hour outdoor rim light",
    "dim bedroom night lamp glow",
    "party bokeh string lights behind subject",
    "overcast soft daylight",
    "moody side key light with gentle fill",
]

# Rich unique environments keyed by cue keywords (longest match wins via scan order)
SCENE_RECIPES: list[tuple[str, str, str, str]] = [
    # (keyword, scene_key, environment_action, expression)
    ("escape planning", "door", "standing near a glowing EXIT door in a crowded house party, soft out-of-focus guest silhouettes, clutching a small bag, body angled to leave", "anxious and restless"),
    ("door highlighted", "door", "in a packed living-room party, EXIT sign lit above double doors, she glances at the door while guests blur behind her", "tense, planning escape"),
    ("crowded room", "crowd", "edge of a busy social gathering, blurred people chatting, she stands alone gripping her sleeve", "overwhelmed"),
    ("post-event rumination", "home", "alone on a couch at night replaying a conversation, translucent thought bubbles of earlier talk float above her", "worried rumination"),
    ("looping thought", "home", "sitting on her bed hugging knees, looping translucent speech bubbles circling her head", "anxious looping thoughts"),
    ("anticipatory anxiety", "parking", "in a car in a parking lot before an event, hands on steering wheel, calendar notification glow on phone", "dreading what's ahead"),
    ("calendar marked", "desk", "at a kitchen table staring at a wall calendar circled for a party, stress icons as soft floating shapes", "anticipatory dread"),
    ("wanted but avoided", "study", "standing outside a classroom or office doorway she wants to enter but cannot step through, opportunity posters crossed out softly in background", "conflicted longing"),
    ("crossed-out opportunities", "office", "looking at a corkboard of crossed-out class friendship and promotion sticky notes, hand hovering undecided", "sad avoidance"),
    ("mind reading", "cafe", "in a cafe, a stranger glances over; jagged thought bubble invents a negative story above her head", "paranoid self-conscious"),
    ("stranger glance", "cafe", "medium shot in a cafe aisle as someone looks her way, she freezes mid-step with a negative thought bubble", "startled shame"),
    ("over-rehearsing", "home", "in a hallway mirror practicing a casual hello with sticky-note scripts stuck around the mirror frame", "over-prepared nervous"),
    ("script notes", "home", "sitting on floor with handwritten small-talk scripts spread out, rehearsing lines under her breath", "anxious overthinking"),
    ("social hangover", "bed", "collapsed on bed after a social event, battery-low icon metaphor floating near her, drained posture", "exhausted"),
    ("battery drained", "night", "dim bedroom, she lies half under covers phone face-down, drained after socializing", "social hangover fatigue"),
    ("predict and test", "outdoor", "outside a small cafe door preparing a tiny exposure step, notebook open with one written prediction", "determined nervous"),
    ("tiny test", "cafe", "inside a quiet cafe saying a brief hello to a barista, soft courage in posture", "brave and tense"),
    ("attention outward", "cafe", "in conversation collecting three concrete details about the other person, focus arrows pointing outward not inward", "focused curious"),
    ("spotlight", "brain", "metaphor scene: harsh spotlight on her then shifting onto the other person, pink brain sidekick coaching", "learning"),
    ("stop the autopsy", "desk", "at a desk with a five-minute timer and a kinder rewrite notebook, closing the laptop after review", "relieved discipline"),
    ("5-minute timer", "desk", "close-up of host and a kitchen timer at 5:00 with kinder rewrite sticky notes", "calm practice"),
    ("this week plan", "study", "whiteboard week plan with three small exposure loops drawn as simple icons, host pointing", "explaining confident"),
    ("professional help", "therapy", "calm therapy room armchair, soft sage tones, host gesturing that reaching out is strategy", "warm supportive"),
    ("nervous system", "brain", "stylized inside-feeling scene, pink brain sidekick showing danger-to-connection rewiring", "hopeful explaining"),
    ("fear of judgment", "meeting", "silent in a glass meeting room while others talk, she stares at notes avoiding eye contact", "fearful self-monitoring"),
    ("avoidance", "home", "canceling plans on her phone on the couch, invite notification dismissed", "guilty relief"),
    ("shyness vs", "talking", "split composition: left warming up at a small gathering, right frozen avoiding eye contact in the same room", "contrast explaining"),
    ("7 signs", "whiteboard", "teaching beat at a soft whiteboard with seven simple icons, host gesturing", "explaining"),
    ("disclaimer", "talking", "direct-to-camera medium shot in a calm cream room, serious but kind", "sincere"),
    ("title card", "talking", "hero portrait in soft cream studio, subtle social-anxiety vs shyness visual motif behind her", "calm inviting"),
    ("recap", "whiteboard", "recap teaching still with 7 signs and 3 skills icons arranged cleanly, host half-body", "confident wrap-up"),
    ("comment prompt", "talking", "friendly close-up inviting a comment, soft pastel backdrop", "warm inviting"),
    ("party", "party", "crowded house party warm lights, host near the wall observing not mingling", "socially anxious"),
    ("meeting", "meeting", "corporate meeting table, she stays silent while others blur talking", "self-conscious"),
    ("group chat", "phone", "close-up holding phone with group chat open, heart racing metaphor soft red pulse near chest", "phone anxiety"),
    ("text", "texting", "rewriting a message on her phone ten times, deleted drafts floating as translucent ghosts", "perfectionist anxiety"),
]


TEMPLATE = (
    "{lock} wearing {outfit}, Educational YouTube still 1920x1080 16:9, {camera} of the same host character, "
    "{environment}, expression: {expression}, {lighting}, "
    "unique environment for this beat, outfit matches the scene, high resolution, no text overlays, {neg}"
)


def pick_scene_and_outfit(concept: str, spoken: str) -> tuple[str, str]:
    blob = f"{concept} {spoken}".lower()
    by_scene: dict = OUTFITS.get("by_scene") or {}
    keys = sorted(by_scene.keys(), key=len, reverse=True)
    for key in keys:
        if key.lower() in blob:
            return key, by_scene[key]
    heuristics = [
        (r"\b(whiteboard|teach|explain|lecture|signs|recap)\b", "whiteboard"),
        (r"\b(therap|couch|armchair|session|clinician)\b", "therapy"),
        (r"\b(notebook|study|notes|homework|plan)\b", "study"),
        (r"\b(brain|neuron|neural|nervous system)\b", "brain"),
        (r"\b(cafe|coffee)\b", "cafe"),
        (r"\b(outdoor|outside|street|park)\b", "outdoor"),
        (r"\b(sleep|night|bed|insomnia|hangover)\b", "bed"),
        (r"\b(party|crowd|invite)\b", "party"),
        (r"\b(meeting|office|presentation)\b", "meeting"),
        (r"\b(phone|text|chat|message)\b", "phone"),
        (r"\b(door|exit|escape)\b", "door"),
        (r"\b(parking|car)\b", "parking"),
        (r"\b(run|gym|exercise|workout)\b", "exercise"),
        (r"\b(desk|laptop|computer|timer)\b", "desk"),
    ]
    for pat, scene in heuristics:
        if re.search(pat, blob, re.I) and scene in by_scene:
            return scene, by_scene[scene]
    return "default", OUTFITS.get("default") or by_scene.get("desk", "lavender outfit")


def recipe_from_cue(concept: str, spoken: str, seg_i: int) -> tuple[str, str, str]:
    blob = f"{concept} {spoken}".lower()
    for key, _scene, env, expr in SCENE_RECIPES:
        if key in blob:
            return env, expr, key
    # fallback: unique-ish from spoken words + rotating camera flavor
    clean = re.sub(r"[^\w\s'-]", " ", spoken)
    words = clean.split()
    snippet = " ".join(words[:12]) if words else "the spoken idea"
    env = (
        f"visual storytelling beat for '{snippet}', distinct location appropriate to the topic, "
        f"not the same desk-laptop pose as other stills, beat index {seg_i + 1}"
    )
    return env, "expression matching the moment", "fallback"


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
    last_recipe_key = ""
    while i < len(words):
        chunk = words[i : i + words_per_seg]
        start_w = i
        t0 = seg_i * every
        t1 = t0 + every
        char_start = char_at_word[start_w] if start_w < len(char_at_word) else 0
        seg_text = " ".join(chunk)
        cue = nearest_on_screen(char_start, ons)
        concept = concept_from_segment(seg_text, cue)
        scene, outfit = pick_scene_and_outfit(concept, seg_text)
        env, expression, recipe_key = recipe_from_cue(concept, seg_text, seg_i)
        camera = CAMERAS[seg_i % len(CAMERAS)]
        lighting = LIGHTS[seg_i % len(LIGHTS)]
        # force camera/light shift if same recipe as previous still
        if recipe_key == last_recipe_key:
            camera = CAMERAS[(seg_i + 3) % len(CAMERAS)]
            lighting = LIGHTS[(seg_i + 5) % len(LIGHTS)]
            env = env + f", alternate angle variation {seg_i + 1}"
        last_recipe_key = recipe_key
        prompt = TEMPLATE.format(
            lock=LOCK_PREFIX,
            outfit=outfit,
            camera=camera,
            environment=env,
            expression=expression,
            lighting=lighting,
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
                "camera": camera,
                "lighting": lighting,
                "recipe": recipe_key,
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
            f"- `{s['name']}` ({s['t_start_sec']:.0f}–{s['t_end_sec']:.0f}s) [{s.get('recipe')}]  \n"
            f"  camera: {s.get('camera')} · scene: {s.get('scene')}  \n"
            f"  spoken: {s['spoken'][:100]}"
        )
    (args.out / "segments.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"stills={len(segments)} duration_sec={duration_sec:.1f} -> {prompts_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
