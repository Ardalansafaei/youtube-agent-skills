#!/usr/bin/env python3
"""Generate many YouTube images from a prompts file via Pollinations."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

GENERATE = Path(__file__).resolve().with_name("generate.py")
GENERATE_THUMB_PUTER = Path(__file__).resolve().with_name("generate_thumb_puter.mjs")
GENERATE_THUMB_OPENAI = Path(__file__).resolve().with_name("generate_thumb_openai.py")


def _has_puter_token() -> bool:
    if (os.environ.get("PUTER_AUTH_TOKEN") or "").strip():
        return True
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return False
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("PUTER_AUTH_TOKEN=") and line.split("=", 1)[1].strip().strip('"').strip("'"):
            return True
    return False


def load_prompts(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")  # strip BOM from Windows editors
    items: list[dict] = []
    if path.suffix.lower() == ".jsonl":
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            prompt = (obj.get("prompt") or obj.get("text") or "").strip()
            if not prompt:
                continue
            name = str(obj.get("name") or f"img_{i:02d}").strip().lstrip("\ufeff")
            items.append(
                {
                    "name": name,
                    "prompt": prompt,
                    "seed": obj.get("seed"),
                    "width": obj.get("width"),
                    "height": obj.get("height"),
                }
            )
        return items

    # Plain text: one prompt per non-empty line; optional "name|prompt"
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, _, prompt = line.partition("|")
            name, prompt = name.strip().lstrip("\ufeff"), prompt.strip()
        else:
            name, prompt = f"img_{i:02d}", line
        if prompt:
            items.append({"name": name, "prompt": prompt, "seed": None, "width": None, "height": None})
    return items


def main() -> int:
    p = argparse.ArgumentParser(description="Batch Pollinations image generation for yt-agent")
    p.add_argument("prompts_file", help="prompts.txt (one per line) or .jsonl")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Default still size (YouTube 16:9 video = 1920). Thumbs auto 1280 if name starts with thumb_",
    )
    p.add_argument("--height", type=int, default=1080, help="Default 1080 for video stills")
    p.add_argument("--model", default="flux")
    p.add_argument("--wait", type=float, default=0, help="Seconds between requests")
    p.add_argument("--stop-on-fail", action="store_true")
    args = p.parse_args()

    src = Path(args.prompts_file)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = load_prompts(src)
    if not items:
        print("no prompts found", file=sys.stderr)
        return 1

    results = []
    ok = fail = 0
    for i, item in enumerate(items, 1):
        name = item["name"]
        prompt = item["prompt"]
        # YouTube standards: video stills 1920×1080 (16:9); upload thumbnails 1280×720
        if item.get("width") is not None and item.get("height") is not None:
            width, height = int(item["width"]), int(item["height"])
        elif str(name).lower().startswith("thumb"):
            width, height = 1280, 720
        else:
            width, height = int(args.width), int(args.height)
        # Thumbnails → Puter (free OpenAI GPT Image) preferred; OpenAI direct fallback
        # Stills → Pollinations
        if str(name).lower().startswith("thumb"):
            if _has_puter_token() and GENERATE_THUMB_PUTER.is_file():
                cmd = [
                    "node",
                    str(GENERATE_THUMB_PUTER),
                    "--prompt",
                    prompt,
                    "--out",
                    str(out),
                    "--name",
                    name,
                    "--width",
                    str(width),
                    "--height",
                    str(height),
                    "--model",
                    "gpt-image-2.5-flare",
                ]
                print(f"[{i}/{len(items)}] {name} (puter thumb)", flush=True)
            else:
                cmd = [
                    sys.executable,
                    str(GENERATE_THUMB_OPENAI),
                    prompt,
                    "--out",
                    str(out),
                    "--name",
                    name,
                    "--size",
                    f"{width}x{height}",
                ]
                print(f"[{i}/{len(items)}] {name} (openai thumb)", flush=True)
        else:
            cmd = [
                sys.executable,
                str(GENERATE),
                prompt,
                "--out",
                str(out),
                "--name",
                name,
                "--width",
                str(width),
                "--height",
                str(height),
                "--model",
                args.model,
            ]
            if item.get("seed") is not None:
                cmd.extend(["--seed", str(item["seed"])])
            print(f"[{i}/{len(items)}] {name}", flush=True)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        entry = {
            "name": name,
            "prompt": prompt,
            "exit": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "time": datetime.now().isoformat(timespec="seconds"),
        }
        results.append(entry)
        if proc.returncode == 0:
            ok += 1
            print(entry["stdout"], flush=True)
        else:
            fail += 1
            print(entry["stderr"] or f"fail exit={proc.returncode}", file=sys.stderr, flush=True)
            if args.stop_on_fail:
                break
        if args.wait > 0 and i < len(items):
            time.sleep(args.wait)

    manifest = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "prompts_file": str(src),
        "out": str(out),
        "ok": ok,
        "fail": fail,
        "total": len(items),
        "model": args.model,
        "size": [args.width, args.height],
        "results": results,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# yt-image batch {datetime.now().isoformat(timespec='seconds')}",
        f"ok={ok} fail={fail} total={len(items)}",
        "",
    ]
    for r in results:
        status = "OK" if r["exit"] == 0 else "FAIL"
        lines.append(f"- {status} `{r['name']}` — {r['prompt'][:120]}")
    (out / "manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SUMMARY ok={ok} fail={fail} out={out}", flush=True)
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
