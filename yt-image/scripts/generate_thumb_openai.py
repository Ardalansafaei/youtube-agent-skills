#!/usr/bin/env python3
"""Generate YouTube thumbnails via OpenAI Images API (ChatGPT image models).

Stills stay on Pollinations. Thumbnails ONLY use this script.

    python generate_thumb_openai.py "prompt..." --out ./thumbs --name thumb_A
    python generate_thumb_openai.py --file prompts.txt --out ./thumbs

prompts.txt lines: name|prompt  (names should start with thumb)

On 401/429/insufficient_quota, shifts to the next key in OPENAI_KEYS.md.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = SKILL_DIR / ".env"
KEYS_FILE = SKILL_DIR / "OPENAI_KEYS.md"
INDEX_FILE = SKILL_DIR / ".openai_key_index"
API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2.5-sunburst"
KEY_RE = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b")

# Obvious placeholder patterns — never treat as live credentials
PLACEHOLDER_MARKERS = (
    "abcdef",
    "1234567890abcdef",
    "efgh",
    "ijkl",
    "mnop",
    "qrst",
    "uvwx",
)

ROTATE_MARKERS = (
    "insufficient_quota",
    "credit_balance_exhausted",
    "You have no credits remaining",
    "Rate limit",
    "rate_limit",
    "invalid_api_key",
    "Incorrect API key",
    "invalid_request_error",
)


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def looks_placeholder(key: str) -> bool:
    low = key.lower()
    if low.count("abcd") >= 2:
        return True
    return any(m in low for m in PLACEHOLDER_MARKERS)


def load_openai_keys() -> list[str]:
    """Ordered unique real-looking keys from env + OPENAI_KEYS.md."""
    load_dotenv(ENV_FILE)
    found: list[str] = []
    seen: set[str] = set()
    skipped = 0

    def add(raw: str | None) -> None:
        nonlocal skipped
        k = (raw or "").strip()
        if not k or k in seen:
            return
        if looks_placeholder(k):
            skipped += 1
            return
        seen.add(k)
        found.append(k)

    add(os.environ.get("OPENAI_API_KEY"))
    multi = (os.environ.get("OPENAI_API_KEYS") or "").strip()
    if multi:
        for part in re.split(r"[,;\s]+", multi):
            add(part)
    if KEYS_FILE.is_file():
        for match in KEY_RE.findall(KEYS_FILE.read_text(encoding="utf-8")):
            add(match)

    if skipped:
        print(f"skipped {skipped} placeholder-looking OpenAI key(s)", file=sys.stderr, flush=True)
    if not found:
        raise RuntimeError(
            "No usable OpenAI keys. Add real sk-proj-… keys to yt-image/OPENAI_KEYS.md "
            "or set OPENAI_API_KEY (placeholder abcd/efgh keys are ignored)."
        )
    return found


def read_key_index(n: int) -> int:
    if n <= 0:
        return 0
    if not INDEX_FILE.is_file():
        return 0
    try:
        idx = int(INDEX_FILE.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0
    return max(0, min(idx, n - 1))


def write_key_index(idx: int) -> None:
    INDEX_FILE.write_text(str(idx) + "\n", encoding="utf-8")


def should_rotate(err_text: str, code: int | None) -> bool:
    if code in (401, 403, 429):
        return True
    return any(m.lower() in err_text.lower() for m in ROTATE_MARKERS)


def load_prompts(path: Path) -> list[dict]:
    items: list[dict] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, _, prompt = line.partition("|")
            name, prompt = name.strip(), prompt.strip()
        else:
            name, prompt = f"thumb_{i:02d}", line
        if prompt:
            items.append({"name": name, "prompt": prompt})
    return items


def generate_one(
    prompt: str,
    *,
    out: Path,
    name: str,
    model: str,
    size: str,
    quality: str,
    api_key: str,
) -> Path:
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "yt-image-openai-thumb/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"OpenAI HTTP {e.code}: {err}") from e

    images = data.get("data") or []
    if not images:
        raise RuntimeError(f"empty OpenAI response: {data!r}"[:500])
    item = images[0]
    dest = out / f"{name}.png"
    if item.get("b64_json"):
        dest.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=180) as img_resp:
            dest.write_bytes(img_resp.read())
    else:
        raise RuntimeError(f"no image payload: {item.keys()}")

    meta = {
        "saved": str(dest),
        "bytes": dest.stat().st_size,
        "provider": "openai",
        "model": model,
        "size": size,
        "quality": quality,
        "prompt": prompt,
        "time": datetime.now().isoformat(timespec="seconds"),
        "usage": data.get("usage"),
        "key_suffix": api_key[-6:],
    }
    (out / f"{name}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return dest


def generate_with_rotation(
    prompt: str,
    *,
    out: Path,
    name: str,
    model: str,
    size: str,
    quality: str,
    keys: list[str],
) -> Path:
    start = read_key_index(len(keys))
    last_err: Exception | None = None
    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        key = keys[idx]
        write_key_index(idx)
        try:
            return generate_one(
                prompt,
                out=out,
                name=name,
                model=model,
                size=size,
                quality=quality,
                api_key=key,
            )
        except Exception as e:
            msg = str(e)
            code = None
            m = re.search(r"OpenAI HTTP (\d+)", msg)
            if m:
                code = int(m.group(1))
            if should_rotate(msg, code):
                print(
                    f"key[{idx + 1}/{len(keys)}] failed ({code or 'err'}) — shifting to next",
                    file=sys.stderr,
                    flush=True,
                )
                last_err = e
                continue
            raise
    raise RuntimeError(f"all {len(keys)} OpenAI keys failed for thumbnails") from last_err


def main() -> int:
    p = argparse.ArgumentParser(description="YouTube thumbnails via OpenAI Images API")
    p.add_argument("prompt", nargs="?", help="Single prompt")
    p.add_argument("--file", type=Path, help="prompts.txt with name|prompt lines")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--name", default="thumb_A", help="Filename stem for single prompt")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--size", default="1280x720", help="YouTube thumb 1280x720")
    p.add_argument("--quality", default="high")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = load_openai_keys()

    if args.file:
        items = load_prompts(args.file)
    elif args.prompt:
        items = [{"name": args.name, "prompt": args.prompt}]
    else:
        print("provide a prompt or --file", file=sys.stderr)
        return 1

    ok = fail = 0
    for i, item in enumerate(items, 1):
        name = item["name"]
        print(f"[{i}/{len(items)}] {name} (openai)", flush=True)
        try:
            dest = generate_with_rotation(
                item["prompt"],
                out=out,
                name=name,
                model=args.model,
                size=args.size,
                quality=args.quality,
                keys=keys,
            )
            print(dest, flush=True)
            ok += 1
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr, flush=True)
            fail += 1

    print(f"SUMMARY ok={ok} fail={fail} out={out}", flush=True)
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
