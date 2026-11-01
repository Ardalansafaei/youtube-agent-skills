#!/usr/bin/env python3
"""research_topic.py — find working YouTube videos for a topic, why they pull views, shared tags.

    python research_topic.py "social anxiety" --out research.json
    python research_topic.py "social anxiety" --max 15 --out ./run/research.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMULAS_PATH = HERE.parent / "yt-script" / "hooks.json"


def load_formulas() -> list[dict]:
    data = json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))
    return data.get("hooks", [])


def classify_title(title: str, formulas: list[dict]) -> str:
    scored = []
    for f in formulas:
        n = sum(1 for p in f.get("match", []) if re.search(p, title, re.I))
        if n:
            scored.append((n, f.get("name", "?")))
    scored.sort(reverse=True)
    return scored[0][1] if scored else "Unclassified"


def yt_dlp_json(url: str, extra: list[str] | None = None) -> dict | list:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-J",
        "--no-warnings",
        "--flat-playlist",
        "--skip-download",
        *(extra or []),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"yt-dlp failed ({proc.returncode})")
    return json.loads(proc.stdout)


def yt_dlp_video(url: str) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-J",
        "--no-warnings",
        "--skip-download",
        "--no-playlist",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"yt-dlp video failed ({proc.returncode})")
    return json.loads(proc.stdout)


def normalize_tag(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())


def why_views(v: dict) -> list[str]:
    reasons: list[str] = []
    title = v.get("title") or ""
    formula = v.get("formula") or "Unclassified"
    if formula != "Unclassified":
        reasons.append(f"title formula: {formula}")
    views = int(v.get("views") or 0)
    ch_med = v.get("channel_median_views")
    if ch_med and ch_med > 0 and views >= 2 * ch_med:
        reasons.append(f"outlier vs channel median ({views:,} vs ~{int(ch_med):,})")
    elif views >= 100_000:
        reasons.append("high absolute views (100k+)")
    elif views >= 20_000:
        reasons.append("solid absolute views (20k+)")
    dur = v.get("duration") or 0
    if 60 <= dur <= 900:
        reasons.append("runtime in common retention band (~1–15 min)")
    tags = v.get("tags") or []
    if len(tags) >= 5:
        reasons.append(f"{len(tags)} tags present for disambiguation/search")
    if re.search(r"\b(how|why|stop|fix|secret|vs|before|after|\d+)\b", title, re.I):
        reasons.append("title has concrete promise words (how/why/stop/number)")
    if not reasons:
        reasons.append("packaging + niche demand (inspect title/thumb manually)")
    return reasons


def main() -> int:
    p = argparse.ArgumentParser(description="Research viral-ish YouTube videos for a topic")
    p.add_argument("topic", help="Topic / search query")
    p.add_argument("--max", type=int, default=12, help="Search result count (default 12)")
    p.add_argument("--out", type=Path, required=True, help="Output JSON path")
    p.add_argument("--enrich", type=int, default=8, help="How many top videos to fetch full tags for")
    args = p.parse_args()

    formulas = load_formulas()
    query = args.topic.strip()
    search_url = f"ytsearch{args.max}:{query}"

    print(f"searching: {search_url}", flush=True)
    raw = yt_dlp_json(search_url)
    entries = raw.get("entries") if isinstance(raw, dict) else raw
    entries = [e for e in (entries or []) if e]

    videos: list[dict] = []
    for e in entries:
        vid = e.get("id") or ""
        url = e.get("url") or e.get("webpage_url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        title = e.get("title") or ""
        videos.append(
            {
                "id": vid,
                "title": title,
                "url": url,
                "channel": e.get("channel") or e.get("uploader") or "?",
                "channel_id": e.get("channel_id") or e.get("uploader_id") or "",
                "views": int(e.get("view_count") or e.get("views") or 0),
                "duration": int(e.get("duration") or 0),
                "formula": classify_title(title, formulas),
                "tags": [],
                "description_head": "",
            }
        )

    # Rank by views for enrichment order
    videos.sort(key=lambda v: -v["views"])
    enrich_n = min(args.enrich, len(videos))
    tag_counter: Counter[str] = Counter()

    for i, v in enumerate(videos[:enrich_n]):
        if not v["url"]:
            continue
        print(f"enrich {i+1}/{enrich_n}: {v['title'][:60]}", flush=True)
        try:
            full = yt_dlp_video(v["url"])
        except Exception as err:
            v["enrich_error"] = str(err)[:200]
            continue
        tags = [normalize_tag(t) for t in (full.get("tags") or []) if t and normalize_tag(t)]
        v["tags"] = tags
        v["views"] = int(full.get("view_count") or v["views"] or 0)
        v["duration"] = int(full.get("duration") or v["duration"] or 0)
        v["channel"] = full.get("channel") or full.get("uploader") or v["channel"]
        desc = (full.get("description") or "").strip()
        v["description_head"] = "\n".join(desc.splitlines()[:3])[:400]
        for t in tags:
            tag_counter[t] += 1

    # Optional: channel median for top few channels (flat playlist of uploads)
    by_channel: dict[str, list[int]] = {}
    channel_ids = []
    for v in videos[:enrich_n]:
        cid = v.get("channel_id") or ""
        if cid and cid not in channel_ids:
            channel_ids.append(cid)
    for cid in channel_ids[:4]:
        try:
            ch = yt_dlp_json(f"https://www.youtube.com/channel/{cid}/videos", ["--playlist-end", "8"])
            ents = ch.get("entries") if isinstance(ch, dict) else ch
            views = [int(x.get("view_count") or 0) for x in (ents or []) if x]
            views = [x for x in views if x > 0]
            if len(views) >= 4:
                by_channel[cid] = views
                print(f"channel sample {cid}: median {int(statistics.median(views)):,}", flush=True)
        except Exception as err:
            print(f"channel skip {cid}: {err}", flush=True)

    for v in videos:
        cid = v.get("channel_id") or ""
        if cid in by_channel:
            med = statistics.median(by_channel[cid])
            v["channel_median_views"] = int(med)
            v["multiple"] = round(v["views"] / med, 2) if med else None
        v["why_views"] = why_views(v)

    shared_tags = [
        {"tag": t, "count": c, "among_enriched": enrich_n, "source": "video_tags"}
        for t, c in tag_counter.most_common(40)
        if c >= 2
    ]

    # Fallback: shared title/description keywords (YouTube often hides tags)
    stop = {
        "the", "and", "for", "with", "you", "your", "this", "that", "from", "have",
        "what", "when", "how", "why", "are", "was", "were", "will", "can", "not",
        "into", "about", "just", "like", "from", "they", "them", "their", "been",
        "video", "watch", "youtube", "official", "full", "episode",
    }
    phrase_counter: Counter[str] = Counter()
    word_counter: Counter[str] = Counter()
    for v in videos[: max(enrich_n, 8)]:
        blob = f"{v.get('title') or ''} {v.get('description_head') or ''}".lower()
        words = re.findall(r"[a-z0-9']+", blob)
        words = [w for w in words if len(w) > 2 and w not in stop]
        for w in words:
            word_counter[w] += 1
        # bigrams
        for a, b in zip(words, words[1:]):
            if a in stop or b in stop:
                continue
            phrase_counter[f"{a} {b}"] += 1

    topic_words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2}
    for phrase, c in phrase_counter.most_common(30):
        if c >= 2:
            shared_tags.append(
                {"tag": phrase, "count": c, "among_enriched": enrich_n, "source": "title_desc"}
            )
    for w, c in word_counter.most_common(30):
        if c >= 3 and (w in topic_words or any(tw in w or w in tw for tw in topic_words)):
            shared_tags.append(
                {"tag": w, "count": c, "among_enriched": enrich_n, "source": "title_desc"}
            )

    recommended = []
    seen = set()
    # Prefer official tags first, then shared phrases
    for item in sorted(
        shared_tags,
        key=lambda x: (0 if x.get("source") == "video_tags" else 1, -x["count"]),
    ):
        t = item["tag"]
        if t not in seen:
            recommended.append(t)
            seen.add(t)
        if len(recommended) >= 15:
            break
    for t, c in tag_counter.most_common(60):
        if t in seen:
            continue
        if any(w in t for w in topic_words) or c >= 2:
            recommended.append(t)
            seen.add(t)
        if len(recommended) >= 15:
            break
    # Always include the topic itself
    topic_tag = normalize_tag(query)
    if topic_tag and topic_tag not in seen:
        recommended.insert(0, topic_tag)
        recommended = recommended[:15]

    # Structural commonalities among top by views
    top = videos[: min(8, len(videos))]
    formula_counts = Counter(v["formula"] for v in top)
    shared_structure = []
    if formula_counts:
        top_f, n = formula_counts.most_common(1)[0]
        shared_structure.append(f"most common title formula among top: {top_f} ({n}/{len(top)})")
    avg_dur = statistics.mean([v["duration"] for v in top if v["duration"]]) if any(v["duration"] for v in top) else 0
    if avg_dur:
        shared_structure.append(f"avg duration among top ≈ {int(avg_dur)}s")

    report = {
        "topic": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "search": search_url,
        "video_count": len(videos),
        "enriched": enrich_n,
        "videos": videos,
        "shared_tags": shared_tags,
        "recommended_tags": recommended[:15],
        "shared_structure": shared_structure,
        "top_takeaways": [
            "Rank by views for this search; prefer outliers vs channel median when available.",
            "Reuse recommended_tags in yt-seo (disambiguation only, ≤15).",
            "Mirror winning title formulas in yt-package / yt-script — do not copy titles verbatim.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Human summary
    md = [
        f"# Viral research: {query}",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Top videos",
    ]
    for v in videos[:10]:
        md.append(
            f"- **{v['views']:,}** — {v['title']}  \n  {v['channel']} | {v['formula']} | {v['url']}"
        )
        md.append(f"  - why: {'; '.join(v.get('why_views') or [])}")
    md.extend(["", "## Shared / recommended tags", ""])
    md.append(", ".join(recommended[:15]) or "(none found — enrich more videos)")
    md.extend(["", "## Structure", ""])
    md.extend(f"- {s}" for s in shared_structure) if shared_structure else md.append("- (n/a)")
    md_path = args.out.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"wrote {args.out}", flush=True)
    print(f"wrote {md_path}", flush=True)
    print("recommended_tags:", ", ".join(recommended[:15]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
