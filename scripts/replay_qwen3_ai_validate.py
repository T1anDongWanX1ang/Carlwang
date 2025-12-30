#!/usr/bin/env python3
"""Replay the Qwen3 AI validation step for a specific KOL crawl run.

Why:
- During the crawl, tweet_enricher._ai_validate_content() calls chatgpt_client._make_request()
  and only logs the length of the model output, not the output itself.
- This script re-runs the same prompt against the same model (Qwen3) so you can inspect
  the raw responses and see why it may be returning all 'false'.

It DOES NOT write to DB.

Usage:
  python3 scripts/replay_qwen3_ai_validate.py \
    --log daily_kol_tweet_crawler/service_kol_tweet.log \
    --run-offset 1 \
    --hours-limit 12 \
    --max-pages 140 \
    --limit 20

Notes:
- Requires network access and consumes model/API quota.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser

RUN_MARK_RE = re.compile(r"推文增强完成，处理\s+(\d+)\s+条推文")
START_ENRICH_RE = re.compile(r"开始增强推文\s+(\d+)")
REQ_PARAMS_RE = re.compile(r"请求参数:\s+(\{.*\})\s*$")


@dataclass
class AiValidationResult:
    tweet_id: str
    tweet_url: Optional[str]
    text_preview: str

    raw_response: Optional[str]
    cleaned_response: Optional[str]
    parsed_bool: Optional[bool]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _get_run_marker(log_text: str, run_offset: int) -> re.Match:
    matches = list(RUN_MARK_RE.finditer(log_text))
    if not matches:
        raise RuntimeError("No run marker found: '推文增强完成，处理 N 条推文'")
    if run_offset < 0 or run_offset >= len(matches):
        raise ValueError(f"run_offset out of range: {run_offset}, total markers={len(matches)}")
    return matches[-1 - run_offset]


def _extract_list_id_near_marker(log_text: str, marker_pos: int) -> Optional[str]:
    prefix = log_text[:marker_pos]
    lines = prefix.splitlines()
    for line in reversed(lines):
        m = REQ_PARAMS_RE.search(line)
        if not m:
            continue
        raw = m.group(1)
        try:
            params = ast.literal_eval(raw)
        except Exception:
            continue
        if not isinstance(params, dict):
            continue
        for key in ("list_id", "listId"):
            value = params.get(key)
            if value:
                return str(value)
    return None


def _extract_run_tweet_ids(log_text: str, marker_pos: int, n: int) -> List[str]:
    prefix = log_text[:marker_pos]
    ids: List[str] = []
    for m in reversed(list(START_ENRICH_RE.finditer(prefix))):
        ids.append(m.group(1))
        if len(ids) >= n:
            break
    ids.reverse()
    if len(ids) != n:
        raise RuntimeError(f"Expected {n} tweet ids, found {len(ids)}")
    return ids


def _shorten(text: str, n: int = 160) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _fetch_until_ids_found_twitterapi(
    list_id: str,
    target_ids: List[str],
    hours_limit: float,
    max_pages: int,
) -> Dict[str, Dict[str, Any]]:
    # Import lazily after sys.path fix
    from src.api.twitter_api_twitterapi import twitter_api

    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    targets = set(str(x) for x in target_ids)
    found: Dict[str, Dict[str, Any]] = {}

    cursor: Optional[str] = None
    page = 1
    while page <= max_pages and len(found) < len(targets):
        tweets, next_cursor = twitter_api.fetch_tweets(list_id=list_id, cursor=cursor)
        if not tweets:
            break

        oldest_time: Optional[datetime] = None
        for tw in tweets:
            tid = tw.get("id_str") or tw.get("id") or tw.get("tweet_id")
            if tid is not None and tid != "":
                tid_str = str(tid)
                if tid_str in targets and tid_str not in found:
                    found[tid_str] = tw

            created_at_str = tw.get("created_at")
            if created_at_str:
                try:
                    t = date_parser.parse(created_at_str)
                    if t.tzinfo:
                        t = t.astimezone().replace(tzinfo=None)
                    if oldest_time is None or t < oldest_time:
                        oldest_time = t
                except Exception:
                    pass

        if oldest_time and oldest_time < time_cutoff:
            break

        if not next_cursor:
            break
        cursor = next_cursor
        page += 1

    return found


def _ai_validate_raw(text: str) -> AiValidationResult:
    from src.api.chatgpt_client import chatgpt_client

    prompt = f"""/no_think
分析推文是否为有价值的加密货币相关内容（非广告）。
推文: {text}

直接回答true或false，不要解释："""

    raw = chatgpt_client._make_request(
        [
            {"role": "system", "content": "You are a content validator. Reply ONLY with 'true' or 'false', nothing else."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=20,
    )

    cleaned: Optional[str] = None
    parsed: Optional[bool] = None
    if raw is not None:
        cleaned = raw.strip().lower()
        if cleaned == "true":
            parsed = True
        elif cleaned == "false":
            parsed = False
        else:
            parsed = None

    return raw, cleaned, parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=str, default="daily_kol_tweet_crawler/service_kol_tweet.log")
    parser.add_argument("--run-offset", type=int, default=1, help="0=latest run, 1=previous run (e.g. 14:24 run)")
    parser.add_argument("--hours-limit", type=float, default=12.0)
    parser.add_argument("--max-pages", type=int, default=140)
    parser.add_argument("--limit", type=int, default=20, help="Only replay AI validation for first N tweets")
    parser.add_argument("--output-dir", type=str, default="reports")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    log_path = (project_root / args.log).resolve()
    log_text = _read_text(log_path)

    marker = _get_run_marker(log_text, run_offset=args.run_offset)
    n = int(marker.group(1))
    list_id = _extract_list_id_near_marker(log_text, marker.start())
    if not list_id:
        raise RuntimeError("Could not find list_id near run marker")

    tweet_ids = _extract_run_tweet_ids(log_text, marker.start(), n)

    by_id = _fetch_until_ids_found_twitterapi(
        list_id=list_id,
        target_ids=tweet_ids,
        hours_limit=args.hours_limit,
        max_pages=args.max_pages,
    )

    to_process = [tid for tid in tweet_ids if tid in by_id][: args.limit]

    results: List[AiValidationResult] = []
    stats = {"true": 0, "false": 0, "other": 0, "none": 0}

    for tid in to_process:
        tw = by_id[tid]
        text = str(tw.get("full_text") or "")
        url = tw.get("tweet_url")

        raw, cleaned, parsed = _ai_validate_raw(text)

        if raw is None:
            stats["none"] += 1
        elif parsed is True:
            stats["true"] += 1
        elif parsed is False:
            stats["false"] += 1
        else:
            stats["other"] += 1

        results.append(
            AiValidationResult(
                tweet_id=tid,
                tweet_url=str(url) if url else None,
                text_preview=_shorten(text),
                raw_response=raw,
                cleaned_response=cleaned,
                parsed_bool=parsed,
            )
        )

    out_dir = (project_root / args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"qwen3_ai_validate_runoffset{args.run_offset}_{now}.json"

    payload = {
        "log_path": str(log_path),
        "run_offset": args.run_offset,
        "run_size": n,
        "list_id": list_id,
        "hours_limit": args.hours_limit,
        "max_pages": args.max_pages,
        "limit": args.limit,
        "matched_in_list": len(by_id),
        "processed": len(results),
        "stats": stats,
        "results": [asdict(r) for r in results],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 80)
    print(f"Log: {log_path}")
    print(f"Run size (marker): {n}")
    print(f"List ID: {list_id}")
    print(f"Matched tweets in list: {len(by_id)}")
    print(f"Processed: {len(results)}")
    print(f"Stats: {stats}")
    print(f"Report JSON: {out_path}")
    print("=" * 80)

    for r in results:
        print(f"{r.tweet_id} | parsed={r.parsed_bool} | raw={repr(r.raw_response)} | {r.text_preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
