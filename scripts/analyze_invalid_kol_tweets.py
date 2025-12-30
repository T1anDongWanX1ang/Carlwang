#!/usr/bin/env python3
"""Analyze the last KOL crawl run where tweets were filtered by is_valid=0.

What this script does:
1) Parse the KOL service log and extract the last run's tweet IDs ("开始增强推文 <id>")
   based on the most recent "推文增强完成，处理 N 条推文" marker.
2) Re-fetch tweet texts from TwitterAPI list endpoint (same backend as the crawler) using the
   most recent list_id found in the log.
3) Re-evaluate the keyword-based content validation logic and emit a per-tweet diagnostic.

Notes:
- The production pipeline may also use AI validation; this script focuses on the deterministic
  keyword validation to explain why tweets often become invalid.
- It does NOT write to DB.

Usage:
  python3 scripts/analyze_invalid_kol_tweets.py \
    --log daily_kol_tweet_crawler/service_kol_tweet.log \
    --hours-limit 6 \
    --max-pages 15 \
    --page-size 100

Output:
- Prints a concise report to stdout
- Writes a JSON report under reports/invalid_kol_tweets_<timestamp>.json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


RUN_MARK_RE = re.compile(r"推文增强完成，处理\s+(\d+)\s+条推文")
START_ENRICH_RE = re.compile(r"开始增强推文\s+(\d+)")
INVALID_RE = re.compile(r"推文\s+(\d+)\s+标记为无效")
REQ_PARAMS_RE = re.compile(r"请求参数:\s+(\{.*\})\s*$")


@dataclass
class ValidationDiagnostics:
    tweet_id: str
    url: Optional[str]
    text_preview: str

    # Signals
    length: int
    has_crypto_keywords: bool
    high_spam_hits: List[str]
    medium_spam_hits: List[str]
    low_spam_hits: List[str]
    total_spam_score: float
    url_count_in_text: int
    is_low_quality_text: bool
    has_valuable_content: bool

    # Verdict
    keyword_verdict: bool


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_last_run_size(log_text: str) -> int:
    matches = list(RUN_MARK_RE.finditer(log_text))
    if not matches:
        raise RuntimeError("No run marker found: '推文增强完成，处理 N 条推文'")
    return int(matches[-1].group(1))


def _get_run_marker(log_text: str, run_offset: int = 0) -> re.Match:
    """Get a specific run marker.

    Args:
        run_offset: 0 means the latest run, 1 means the previous run, etc.
    """
    matches = list(RUN_MARK_RE.finditer(log_text))
    if not matches:
        raise RuntimeError("No run marker found: '推文增强完成，处理 N 条推文'")
    if run_offset < 0 or run_offset >= len(matches):
        raise ValueError(f"run_offset out of range: {run_offset}, total markers={len(matches)}")
    return matches[-1 - run_offset]


def _extract_run_tweet_ids(log_text: str, marker_pos: int, n: int) -> List[str]:
    # Scan backwards from a specific run marker for '开始增强推文 <id>'
    prefix = log_text[:marker_pos]

    ids: List[str] = []
    for m in reversed(list(START_ENRICH_RE.finditer(prefix))):
        ids.append(m.group(1))
        if len(ids) >= n:
            break

    ids.reverse()
    if len(ids) != n:
        raise RuntimeError(f"Expected {n} tweet ids, found {len(ids)} in log")
    return ids


def _extract_list_id_near_marker(log_text: str, marker_pos: int) -> Optional[str]:
    """Extract the most relevant list_id by scanning backwards from a marker position."""
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


def _shorten(text: str, n: int = 140) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[: n - 1] + "…"


def _is_low_quality_text(text_lower: str) -> bool:
    if re.search(r"(.)\1{4,}", text_lower):
        return True
    if text_lower.count("!") > 5 or text_lower.count("?") > 3:
        return True
    emoji_count = len(re.findall(r"[🚀💰💎🔥⚡️📈📉🎯🌙💯🎉✅❌]", text_lower))
    if emoji_count > 8:
        return True
    return False


def _has_valuable_content(text_lower: str) -> bool:
    valuable_keywords = [
        "analysis", "分析", "chart", "图表", "technical", "技术",
        "support", "支撑", "resistance", "阻力", "breakout", "突破",
        "pattern", "形态", "trend", "趋势", "forecast", "预测",
        "market cap", "市值", "volume", "成交量", "fundamentals", "基本面",
        "adoption", "采用", "regulation", "监管", "news", "新闻",
        "development", "开发", "upgrade", "升级", "partnership", "合作",
    ]
    return any(k in text_lower for k in valuable_keywords)


def _keyword_validation_diagnostics(text: str) -> Tuple[bool, Dict[str, Any]]:
    if not text or len(text.strip()) < 10:
        return False, {
            "length": len(text.strip()) if text else 0,
            "has_crypto_keywords": False,
            "high_spam_hits": [],
            "medium_spam_hits": [],
            "low_spam_hits": [],
            "total_spam_score": 0.0,
            "url_count_in_text": 0,
            "is_low_quality_text": False,
            "has_valuable_content": False,
        }

    text_lower = text.lower()

    crypto_keywords = [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "blockchain", "defi", "nft", "dao", "web3", "altcoin",
        "doge", "ada", "sol", "matic", "avax", "dot", "link", "usdt", "usdc",
        "binance", "coinbase", "trading", "market", "price", "bull", "bear",
        "hodl", "satoshi", "mining", "wallet", "exchange", "token",
        "比特币", "以太坊", "加密货币", "区块链", "数字货币", "币", "代币",
    ]

    high_spam_keywords = [
        "airdrop", "空投", "giveaway", "赠送", "free tokens", "免费代币",
        "click here", "点击这里", "link in bio", "dm me", "私信我",
        "follow for free", "关注获得免费", "join telegram", "加入电报群",
        "presale", "预售", "ido", "ico", "首发", "listing soon", "即将上市",
    ]

    medium_spam_keywords = [
        "promotion", "推广", "sponsored", "赞助", "partnership", "合作",
        "exclusive", "独家", "limited offer", "限时优惠", "special deal", "特价",
        "buy now", "立即购买", "get rich", "暴富", "easy money", "轻松赚钱",
        "guaranteed profit", "保证盈利", "100x", "1000x", "moon mission", "登月",
    ]

    low_spam_keywords = [
        "pump", "dump", "diamond hands", "ape in", "lambo", "fomo",
        "degen", "alpha", "gem", "rocket", "fire", "bullish af",
    ]

    has_crypto_keywords = any(k in text_lower for k in crypto_keywords)
    high_hits = [k for k in high_spam_keywords if k in text_lower]
    medium_hits = [k for k in medium_spam_keywords if k in text_lower]
    low_hits = [k for k in low_spam_keywords if k in text_lower]

    high_spam_score = 2 * len(high_hits)
    medium_spam_score = 1 * len(medium_hits)
    low_spam_score = 0.5 * len(low_hits)
    total_spam_score = float(high_spam_score + medium_spam_score + low_spam_score)

    url_count = len(re.findall(r"http[s]?://\S+", text_lower))

    low_quality = _is_low_quality_text(text_lower)
    valuable = _has_valuable_content(text_lower)

    # Replicate verdict logic from tweet_enricher._keyword_validate_content
    if not has_crypto_keywords:
        verdict = False
    elif high_spam_score > 0:
        verdict = False
    elif total_spam_score >= 3:
        verdict = False
    elif url_count > 1:
        verdict = False
    elif low_quality:
        verdict = False
    elif valuable:
        verdict = True
    else:
        verdict = total_spam_score <= 1

    details = {
        "length": len(text.strip()),
        "has_crypto_keywords": has_crypto_keywords,
        "high_spam_hits": high_hits,
        "medium_spam_hits": medium_hits,
        "low_spam_hits": low_hits,
        "total_spam_score": total_spam_score,
        "url_count_in_text": url_count,
        "is_low_quality_text": low_quality,
        "has_valuable_content": valuable,
    }

    return verdict, details


def _fetch_recent_list_tweets(list_id: str, hours_limit: float, max_pages: int, page_size: int) -> List[Dict[str, Any]]:
    """Fetch list tweets with a hard page cap.

    Note: The built-in client has a protective 15-page cap in fetch_all_tweets(); for analysis,
    we implement our own pagination loop and allow a higher max_pages, with early-stop when
    tweets are older than the time window.
    """
    from datetime import timedelta

    from dateutil import parser as date_parser
    from src.api.twitter_api_twitterapi import twitter_api

    time_cutoff = datetime.now() - timedelta(hours=hours_limit)

    all_tweets: List[Dict[str, Any]] = []
    pagination_token: Optional[str] = None
    page = 1

    while page <= max_pages:
        params: Dict[str, Any] = {"max_results": min(page_size, 100)}
        if pagination_token:
            params["pagination_token"] = pagination_token

        tweets, next_token = twitter_api.fetch_tweets(list_id=list_id, **params)
        if not tweets:
            break

        all_tweets.extend(tweets)

        # Early stop if this page is already older than cutoff.
        oldest_time: Optional[datetime] = None
        for tw in tweets:
            created_at_str = tw.get("created_at")
            if not created_at_str:
                continue
            try:
                t = date_parser.parse(created_at_str)
                if t.tzinfo:
                    t = t.astimezone().replace(tzinfo=None)
                if oldest_time is None or t < oldest_time:
                    oldest_time = t
            except Exception:
                continue

        if oldest_time and oldest_time < time_cutoff:
            break

        if not next_token:
            break
        pagination_token = next_token
        page += 1

    return all_tweets


def _fetch_until_ids_found(
    backend: str,
    list_id: str,
    target_ids: List[str],
    hours_limit: float,
    max_pages: int,
    page_size: int,
) -> Dict[str, Dict[str, Any]]:
    """Fetch list tweets until all target tweet IDs are found or limits reached."""
    from datetime import timedelta

    from dateutil import parser as date_parser

    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    targets = set(str(x) for x in target_ids)
    found: Dict[str, Dict[str, Any]] = {}

    page = 1

    if backend == "tweetscout":
        from src.api.twitter_api import twitter_api as client

        cursor: Optional[str] = None
        while page <= max_pages and len(found) < len(targets):
            params: Dict[str, Any] = {"count": page_size}
            if cursor:
                params["cursor"] = cursor

            tweets, next_cursor = client.fetch_tweets(list_id=list_id, **params)
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

    # default: twitterapi.io backend
    from src.api.twitter_api_twitterapi import twitter_api as client

    pagination_token: Optional[str] = None
    while page <= max_pages and len(found) < len(targets):
        params = {"max_results": min(page_size, 100)}
        if pagination_token:
            params["pagination_token"] = pagination_token

        tweets, next_token = client.fetch_tweets(list_id=list_id, **params)
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
        if not next_token:
            break
        pagination_token = next_token
        page += 1

    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=str, default="daily_kol_tweet_crawler/service_kol_tweet.log")
    parser.add_argument("--backend", type=str, default="tweetscout", choices=["tweetscout", "twitterapi"])
    parser.add_argument("--run-offset", type=int, default=0, help="0=latest run, 1=previous run, ...")
    parser.add_argument("--hours-limit", type=float, default=6.0)
    parser.add_argument("--max-pages", type=int, default=15)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--output-dir", type=str, default="reports")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    # Ensure imports like `from src...` work when running this script directly.
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    log_path = (project_root / args.log).resolve()
    if not log_path.exists():
        raise FileNotFoundError(f"Log not found: {log_path}")

    log_text = _read_text(log_path)

    marker = _get_run_marker(log_text, run_offset=args.run_offset)
    n = int(marker.group(1))
    tweet_ids = _extract_run_tweet_ids(log_text, marker.start(), n)
    list_id = _extract_list_id_near_marker(log_text, marker.start())

    if not list_id:
        raise RuntimeError("Could not find list_id in log. Try increasing log retention or pass a newer log file.")

    # For diagnostics, fetch until all ids are found (or until limits reached).
    by_id = _fetch_until_ids_found(
        backend=args.backend,
        list_id=list_id,
        target_ids=tweet_ids,
        hours_limit=args.hours_limit,
        max_pages=args.max_pages,
        page_size=args.page_size,
    )

    results: List[ValidationDiagnostics] = []
    missing: List[str] = []

    for tid in tweet_ids:
        item = by_id.get(tid)
        if not item:
            missing.append(tid)
            continue

        text = str(item.get("full_text") or "")
        url = item.get("tweet_url")

        keyword_verdict, details = _keyword_validation_diagnostics(text)

        results.append(
            ValidationDiagnostics(
                tweet_id=tid,
                url=str(url) if url else None,
                text_preview=_shorten(text, 160),
                keyword_verdict=keyword_verdict,
                **details,
            )
        )

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (project_root / args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"invalid_kol_tweets_{now}.json"

    payload = {
        "log_path": str(log_path),
        "run_size": n,
        "list_id": list_id,
        "hours_limit": args.hours_limit,
        "max_pages": args.max_pages,
        "page_size": args.page_size,
        "tweet_ids": tweet_ids,
        "found": len(results),
        "missing": missing,
        "results": [asdict(r) for r in results],
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    print("=" * 80)
    print(f"Log: {log_path}")
    print(f"Last run tweet count: {n}")
    print(f"List ID (from log): {list_id}")
    print(f"Fetched+matched tweets: {len(by_id)}")
    print(f"Matched tweets: {len(results)} / {n}")
    if missing:
        print(f"Missing (not found in fetched window): {len(missing)}")
    print(f"Report JSON: {out_path}")
    print("=" * 80)

    # Print a compact per-tweet line
    for r in results:
        reason_bits: List[str] = []
        if not r.has_crypto_keywords:
            reason_bits.append("no_crypto_keywords")
        if r.high_spam_hits:
            reason_bits.append("high_spam")
        if r.total_spam_score >= 3:
            reason_bits.append("spam_score>=3")
        if r.url_count_in_text > 1:
            reason_bits.append("too_many_urls")
        if r.is_low_quality_text:
            reason_bits.append("low_quality")
        if r.has_valuable_content:
            reason_bits.append("valuable_content")

        reasons = ",".join(reason_bits) if reason_bits else "(none)"
        print(f"{r.tweet_id} | keyword_verdict={r.keyword_verdict} | spam={r.total_spam_score} | reasons={reasons} | {r.text_preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
