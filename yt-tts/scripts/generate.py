#!/usr/bin/env python3
"""YouTube voiceover via Microsoft Edge TTS (edge-tts) — free, no API key."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "en-US-AndrewNeural"
# Soft chunking for long scripts (Edge can choke on huge single payloads)
MAX_CHUNK = 1800


def read_text(path: Path | None, inline: str | None) -> str:
    if inline is not None:
        return inline.strip()
    if path is None:
        raise SystemExit("provide --text or --file")
    return path.read_text(encoding="utf-8-sig").strip()


def to_spoken_only(text: str) -> str:
    """Strip stage directions so TTS reads narration only."""
    text = re.sub(r"\[ON SCREEN:[^\]]*\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[B-?ROLL:[^\]]*\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(?:VISUAL|SHOT|CUT|SFX|MUSIC)[^\]]*\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?im)^\s*(hook|beat|turn|payoff|close|section)\s*\d*\s*[:.-]\s*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_len: int = MAX_CHUNK) -> list[str]:
    text = re.sub(r"\r\n?", "\n", text).strip()
    if len(text) <= max_len:
        return [text]
    parts: list[str] = []
    buf = ""
    # Prefer paragraph, then sentence breaks
    blocks = re.split(r"\n\s*\n+", text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(buf) + len(block) + 2 <= max_len:
            buf = f"{buf}\n\n{block}".strip() if buf else block
            continue
        if buf:
            parts.append(buf)
            buf = ""
        if len(block) <= max_len:
            buf = block
            continue
        sentences = re.split(r"(?<=[.!?])\s+", block)
        for sent in sentences:
            if not sent:
                continue
            if len(buf) + len(sent) + 1 <= max_len:
                buf = f"{buf} {sent}".strip() if buf else sent
            else:
                if buf:
                    parts.append(buf)
                if len(sent) <= max_len:
                    buf = sent
                else:
                    for i in range(0, len(sent), max_len):
                        parts.append(sent[i : i + max_len])
                    buf = ""
    if buf:
        parts.append(buf)
    return parts or [text]


async def synth_chunk(text: str, voice: str, rate: str, pitch: str, dest: Path) -> None:
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(str(dest))
            return
        except Exception as e:
            last_err = e
            await asyncio.sleep(2 * attempt)
    assert last_err is not None
    raise last_err


async def run(text: str, voice: str, rate: str, pitch: str, out_mp3: Path, keep_parts: bool) -> dict:
    chunks = chunk_text(text)
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    part_paths: list[Path] = []
    for i, chunk in enumerate(chunks, 1):
        part = out_mp3.with_name(f"{out_mp3.stem}_part{i:02d}.mp3")
        await synth_chunk(chunk, voice, rate, pitch, part)
        part_paths.append(part)

    if len(part_paths) == 1:
        part_paths[0].replace(out_mp3)
        used = [out_mp3]
    else:
        # Concatenate MP3s by simple byte join (same codec/bitrate from edge-tts)
        data = b"".join(p.read_bytes() for p in part_paths)
        out_mp3.write_bytes(data)
        used = part_paths
        if not keep_parts:
            for p in part_paths:
                p.unlink(missing_ok=True)
            used = [out_mp3]

    meta = {
        "saved": str(out_mp3),
        "bytes": out_mp3.stat().st_size,
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "chunks": len(chunks),
        "chars": len(text),
        "time": datetime.now().isoformat(timespec="seconds"),
        "parts_kept": [str(p) for p in used] if keep_parts and len(chunks) > 1 else [],
    }
    out_mp3.with_suffix(".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description="Generate YouTube VO with edge-tts")
    p.add_argument("--text", help="Inline script text")
    p.add_argument("--file", type=Path, help="UTF-8 script file")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--name", default="voiceover", help="Filename stem")
    p.add_argument("--voice", default=DEFAULT_VOICE)
    p.add_argument("--rate", default="+0%", help='e.g. +10% or -5%')
    p.add_argument("--pitch", default="+0Hz", help="e.g. +0Hz")
    p.add_argument("--keep-parts", action="store_true")
    p.add_argument(
        "--spoken-only",
        action="store_true",
        default=True,
        help="Strip [ON SCREEN]/ stage directions (default on)",
    )
    p.add_argument(
        "--keep-directions",
        action="store_true",
        help="Do not strip stage directions",
    )
    p.add_argument("--list-voices", action="store_true", help="Print en-US voices and exit")
    args = p.parse_args()

    if args.list_voices:
        async def _list() -> None:
            vs = await edge_tts.list_voices()
            for v in vs:
                if v["Locale"].startswith("en-"):
                    print(f"{v['ShortName']}\t{v.get('Gender')}\t{v['Locale']}")

        asyncio.run(_list())
        return 0

    text = read_text(args.file, args.text)
    if not text:
        print("empty script", file=sys.stderr)
        return 1
    if args.spoken_only and not args.keep_directions:
        text = to_spoken_only(text)
    if not text:
        print("empty script after stripping directions", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    spoken_path = out_dir / "script_spoken.txt"
    spoken_path.write_text(text + "\n", encoding="utf-8")
    dest = out_dir / f"{args.name}.mp3"
    meta = asyncio.run(run(text, args.voice, args.rate, args.pitch, dest, args.keep_parts))
    print(meta["saved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
