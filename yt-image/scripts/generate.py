#!/usr/bin/env python3
"""Download a Pollinations-generated image for YouTube stills/thumbnails."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


CLASSIC = "https://image.pollinations.ai/prompt/{prompt}"
ENTER = "https://gen.pollinations.ai/image/{prompt}"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


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
    if status == 402 or b"FREE_LIMIT" in body[:500]:
        raise RuntimeError("rate limited (402 / FREE_LIMIT)")
    if "json" in content_type or body.lstrip().startswith((b"{", b"<")):
        raise RuntimeError(f"non-image response ({content_type or 'unknown'}): {body[:200]!r}")
    if len(body) < 10_000:
        raise RuntimeError(f"file too small ({len(body)} bytes); likely an error card")
    dest.write_bytes(body)
    return status, body


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

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    api_key = (os.environ.get("POLLINATIONS_API_KEY") or "").strip() or None
    use_enter = api_key is not None
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
        status, body = download(url, dest, api_key, args.timeout)
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
