#!/usr/bin/env python3
"""Download a Pollinations-generated image for YouTube stills/thumbnails."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


CLASSIC = "https://image.pollinations.ai/prompt/{prompt}"
ENTER = "https://gen.pollinations.ai/image/{prompt}"
SKILL_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = SKILL_DIR / ".env"
KEYS_FILE = SKILL_DIR / "POLLINATIONS_KEYS.md"
INDEX_FILE = SKILL_DIR / ".pollinations_key_index"

KEY_RE = re.compile(r"\bsk_[A-Za-z0-9]+\b")
BALANCE_MARKERS = (
    b"INSUFFICIENT_BALANCE",
    b"Insufficient balance",
    b"FREE_LIMIT",
    b"available balance is 0",
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


def load_keys() -> list[str]:
    """Ordered unique keys: POLLINATIONS_KEYS.md, then .env / env fallbacks."""
    found: list[str] = []
    seen: set[str] = set()

    def add(key: str | None) -> None:
        k = (key or "").strip()
        if not k or k in seen:
            return
        seen.add(k)
        found.append(k)

    if KEYS_FILE.is_file():
        for match in KEY_RE.findall(KEYS_FILE.read_text(encoding="utf-8")):
            add(match)

    add(os.environ.get("POLLINATIONS_API_KEY"))
    multi = (os.environ.get("POLLINATIONS_API_KEYS") or "").strip()
    if multi:
        for part in re.split(r"[,;\s]+", multi):
            add(part)

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


def is_balance_error(status: int | None, body: bytes) -> bool:
    if status == 402:
        return True
    head = body[:800] if body else b""
    return any(marker in head for marker in BALANCE_MARKERS)


def build_url(prompt: str, *, width: int, height: int, seed: int | None, model: str | None, use_enter: bool) -> str:
    encoded = urllib.parse.quote(prompt, safe="")
    base = (ENTER if use_enter else CLASSIC).format(prompt=encoded)
    params: dict[str, str] = {
        "width": str(width),
        "height": str(height),
        "nologo": "true",
        "nofeed": "true",
    }
    if seed is not None:
        params["seed"] = str(seed)
    if use_enter and model:
        params["model"] = model
    return f"{base}?{urllib.parse.urlencode(params)}"


def download(url: str, dest: Path, api_key: str | None, timeout: int) -> tuple[int, bytes]:
    headers = {
        "User-Agent": "yt-image-pollinations/1.0",
        "Accept": "image/*,application/json;q=0.1,*/*;q=0.05",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        status = getattr(resp, "status", 200) or 200
        content_type = (resp.headers.get("Content-Type") or "").lower()
    if is_balance_error(status, body):
        raise RuntimeError("rate limited (402 / FREE_LIMIT)")
    if "json" in content_type or body.lstrip().startswith((b"{", b"<")):
        raise RuntimeError(f"non-image response ({content_type or 'unknown'}): {body[:200]!r}")
    if len(body) < 10_000:
        raise RuntimeError(f"file too small ({len(body)} bytes); likely an error card")
    dest.write_bytes(body)
    return status, body


def download_with_rotation(
    url: str,
    dest: Path,
    keys: list[str],
    timeout: int,
) -> tuple[int, bytes, str | None, int]:
    """Try keys from persisted index; on balance errors shift and retry."""
    if not keys:
        status, body = download(url, dest, None, timeout)
        return status, body, None, -1

    start = read_key_index(len(keys))
    last_err: Exception | None = None

    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        key = keys[idx]
        write_key_index(idx)
        try:
            status, body = download(url, dest, key, timeout)
            return status, body, key, idx
        except urllib.error.HTTPError as e:
            body = e.read() if hasattr(e, "read") else b""
            if is_balance_error(e.code, body):
                print(
                    f"key[{idx + 1}/{len(keys)}] balance/402 — shifting to next",
                    file=sys.stderr,
                    flush=True,
                )
                last_err = e
                continue
            raise
        except RuntimeError as e:
            if "402" in str(e) or "FREE_LIMIT" in str(e):
                print(
                    f"key[{idx + 1}/{len(keys)}] balance/402 — shifting to next",
                    file=sys.stderr,
                    flush=True,
                )
                last_err = e
                continue
            raise

    if last_err is not None:
        raise RuntimeError(f"all {len(keys)} Pollinations keys exhausted (402/balance)") from last_err
    raise RuntimeError("no Pollinations keys available")


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a YouTube image via Pollinations")
    p.add_argument("prompt", help="Image prompt (English preferred)")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--name", default="image", help="Filename stem")
    p.add_argument("--width", type=int, default=1920, help="YouTube video frame default 1920")
    p.add_argument("--height", type=int, default=1080, help="YouTube video frame default 1080")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--model", default="flux", help="Enter-tier model (ignored on classic)")
    p.add_argument("--wait", type=float, default=0, help="Seconds to sleep before request")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--ext", default=".jpg")
    args = p.parse_args()

    load_dotenv(ENV_FILE)
    keys = load_keys()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    use_enter = bool(keys)
    if args.wait > 0:
        time.sleep(args.wait)

    url = build_url(
        args.prompt,
        width=args.width,
        height=args.height,
        seed=args.seed,
        model=args.model,
        use_enter=use_enter,
    )
    dest = out / f"{args.name}{args.ext if args.ext.startswith('.') else '.' + args.ext}"

    try:
        status, body, used_key, key_idx = download_with_rotation(url, dest, keys, args.timeout)
    except urllib.error.HTTPError as e:
        retry = e.headers.get("Retry-After") if e.headers else None
        msg = e.read()[:300]
        print(f"HTTP {e.code}: {msg!r}", file=sys.stderr)
        if e.code == 402 and retry:
            print(f"Retry-After: {retry}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    meta = {
        "saved": str(dest),
        "bytes": len(body),
        "status": status,
        "mode": "enter" if use_enter else "classic",
        "model": args.model if use_enter else "classic-default",
        "width": args.width,
        "height": args.height,
        "seed": args.seed,
        "prompt": args.prompt,
        "key_index": key_idx,
        "key_suffix": (used_key[-6:] if used_key else None),
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    (out / f"{args.name}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
