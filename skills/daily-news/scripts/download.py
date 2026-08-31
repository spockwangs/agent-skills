#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源新闻下载器：读取 YAML 配置的 RSS / Hacker News / Reddit / Twitter 数据源，
并行抓取，按统一 schema 以 JSONL 输出，每行一条新闻。

输出每行字段：
  title, url, content, author, publish_time, source, metadata
  - publish_time: ISO 8601 UTC 字符串（如 2026-07-10T12:34:56Z），解析不出时为空串
  - metadata:    源相关附加信息（score、tags、discussion_url 等）

用法:
  python3 download.py --config sources.yaml --output out.jsonl
                      [--errors errors.jsonl] [--no-filter] [--list-sources]

参数:
  --config       配置文件路径（YAML）
  --output       输出 JSONL 文件路径；缺省输出到 stdout
  --errors       失败条目 JSONL 文件路径（可选）
  --no-filter    不过滤时间窗口（默认仅保留最近 time_window_hours 小时内的条目）
  --list-sources 仅解析并打印配置的源后退出，不抓取（离线校验配置）

退出码:
  0  正常完成
  1  无任何成功条目（全部失败或为空）
  2  参数错误 / 配置加载失败

参考实现：Horizon/src/scrapers/{rss,hackernews,reddit,twitter}.py
"""

import argparse
import asyncio
import calendar
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Optional

import feedparser
import httpx
from dateutil.parser import isoparse

logger = logging.getLogger("download")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)

# Hacker News Firebase API
HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_TOP_COMMENTS = 10

# Reddit
REDDIT_BASE = "https://www.reddit.com"
REDDIT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{REDDIT_BASE}/",
}
REDDIT_COMMENT_CONCURRENCY = 2

# Twitter via Apify
APIFY_BASE = "https://api.apify.com/v2"
APIFY_POLL_INTERVAL = 3.0
APIFY_MAX_WAIT = 180


@dataclass
class NewsItem:
    """统一的新闻条目（7 字段 schema）。"""

    title: str
    url: str
    content: str = ""
    author: str = ""
    publish_time: Optional[datetime] = None
    source: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        pt = ""
        if self.publish_time is not None:
            dt = self.publish_time
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pt = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "author": self.author,
            "publish_time": pt,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class ErrorItem:
    url: str
    source: str
    error: str

    def to_dict(self) -> dict:
        return {"url": self.url, "source": self.source, "error": self.error}


def expand_env(value: str) -> str:
    """展开字符串中的 ${ENV_VAR} 占位符。"""
    return re.sub(
        r"\$\{(\w+)\}",
        lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
        str(value),
    )


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# RSS / Atom
# ---------------------------------------------------------------------------

async def fetch_rss(
    client: httpx.AsyncClient,
    src: dict,
    cutoff: Optional[datetime],
    errors: list,
) -> list:
    name = src.get("name") or src.get("url", "rss")
    url = expand_env(src["url"])
    items: list = []
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            published_at = _parse_feed_date(entry)
            # 解析不出时保留（宁可多抓，后续去重兜底）
            if published_at is not None and cutoff is not None:
                if to_utc(published_at) < cutoff:
                    continue

            content = _extract_feed_content(entry)
            tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

            items.append(NewsItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", url),
                content=content,
                author=entry.get("author", name),
                publish_time=published_at,
                source=name,
                metadata={
                    "feed_name": name,
                    "category": src.get("category"),
                    "tags": tags,
                },
            ))
    except httpx.HTTPError as e:
        errors.append(ErrorItem(url, name, f"HTTPError: {e}"))
    except Exception as e:
        errors.append(ErrorItem(url, name, f"{type(e).__name__}: {e}"))
    return items


def _parse_feed_date(entry: dict) -> Optional[datetime]:
    for field_name in ("published", "updated", "created"):
        if field_name not in entry:
            continue
        parsed_field = f"{field_name}_parsed"
        try:
            if parsed_field in entry and entry[parsed_field]:
                return datetime.fromtimestamp(
                    calendar.timegm(entry[parsed_field]), tz=timezone.utc
                )
            return to_utc(parsedate_to_datetime(entry[field_name]))
        except Exception:
            continue
    return None


def _extract_feed_content(entry: dict) -> str:
    if entry.get("summary"):
        return entry.summary
    if entry.get("description"):
        return entry.description
    content = entry.get("content")
    if content and isinstance(content, list) and content:
        return content[0].get("value", "")
    return ""


# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------

async def fetch_hackernews(
    client: httpx.AsyncClient,
    src: dict,
    cutoff: Optional[datetime],
    errors: list,
) -> list:
    name = "hackernews"
    fetch_top = int(src.get("fetch_top_stories", 30))
    min_score = int(src.get("min_score", 100))
    fetch_comments = bool(src.get("fetch_comments", True))
    items: list = []
    try:
        resp = await client.get(f"{HN_BASE}/topstories.json", follow_redirects=True)
        resp.raise_for_status()
        story_ids = resp.json()[:fetch_top]

        stories = await asyncio.gather(
            *[_hn_fetch_item(client, sid) for sid in story_ids],
            return_exceptions=True,
        )

        valid = []
        for story in stories:
            if isinstance(story, Exception) or not story:
                continue
            if story.get("score", 0) < min_score:
                continue
            published_at = datetime.fromtimestamp(story["time"], tz=timezone.utc)
            if cutoff is not None and published_at < cutoff:
                continue
            valid.append(story)

        if fetch_comments:
            comment_lists = await asyncio.gather(
                *[_hn_fetch_comments(client, s.get("kids", [])[:HN_TOP_COMMENTS])
                  for s in valid],
                return_exceptions=True,
            )
        else:
            comment_lists = [[] for _ in valid]

        for story, comments in zip(valid, comment_lists):
            if isinstance(comments, Exception):
                comments = []
            items.append(_hn_parse_story(story, comments))
    except httpx.HTTPError as e:
        errors.append(ErrorItem(f"{HN_BASE}/topstories.json", name, f"HTTPError: {e}"))
    except Exception as e:
        errors.append(ErrorItem(f"{HN_BASE}/topstories.json", name, f"{type(e).__name__}: {e}"))
    return items


async def _hn_fetch_item(client: httpx.AsyncClient, item_id: int) -> Optional[dict]:
    try:
        resp = await client.get(f"{HN_BASE}/item/{item_id}.json", follow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return None


async def _hn_fetch_comments(client: httpx.AsyncClient, comment_ids: list) -> list:
    if not comment_ids:
        return []
    raw = await asyncio.gather(
        *[_hn_fetch_item(client, cid) for cid in comment_ids],
        return_exceptions=True,
    )
    comments = []
    for r in raw:
        if isinstance(r, dict) and r.get("text") and not r.get("deleted") and not r.get("dead"):
            comments.append(r)
    return comments


def _hn_parse_story(story: dict, comments: list) -> NewsItem:
    story_id = story["id"]
    parts = []
    if story.get("text"):
        parts.append(story["text"])
    if comments:
        parts.append("\n--- Top Comments ---")
        for c in comments:
            commenter = c.get("by", "anon")
            text = re.sub(r"<[^>]+>", " ", c.get("text", "")).strip()
            if len(text) > 500:
                text = text[:497] + "..."
            parts.append(f"[{commenter}]: {text}")
    content = "\n\n".join(parts)
    return NewsItem(
        title=story.get("title", ""),
        url=story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
        content=content,
        author=story.get("by", "unknown"),
        publish_time=datetime.fromtimestamp(story["time"], tz=timezone.utc),
        source="hackernews",
        metadata={
            "score": story.get("score", 0),
            "descendants": story.get("descendants", 0),
            "type": story.get("type", "story"),
            "discussion_url": f"https://news.ycombinator.com/item?id={story_id}",
            "comment_count": len(comments),
        },
    )


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

async def fetch_reddit(
    client: httpx.AsyncClient,
    src: dict,
    cutoff: Optional[datetime],
    errors: list,
) -> list:
    name = "reddit"
    subreddits = src.get("subreddits") or []
    users = src.get("users") or []
    fetch_comments = int(src.get("fetch_comments", 0))

    tasks = []
    for sub in subreddits:
        if sub.get("enabled", True):
            tasks.append(_reddit_fetch_subreddit(client, sub, cutoff, fetch_comments, errors))
    for user in users:
        if user.get("enabled", True):
            tasks.append(_reddit_fetch_user(client, user, cutoff, errors))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: list = []
    for r in results:
        if isinstance(r, Exception):
            errors.append(ErrorItem("", name, f"{type(r).__name__}: {r}"))
        elif isinstance(r, list):
            items.extend(r)
    return items


async def _reddit_fetch_subreddit(
    client: httpx.AsyncClient, cfg: dict, cutoff: Optional[datetime], fetch_comments: int,
    errors: list,
) -> list:
    sub_name = cfg["name"]
    sort = cfg.get("sort", "hot")
    params = {"limit": min(int(cfg.get("fetch_limit", 25)), 100), "raw_json": 1}
    if sort in ("top", "controversial"):
        params["t"] = cfg.get("time_filter", "day")
    url = f"{REDDIT_BASE}/r/{sub_name}/{sort}.json"
    try:
        data = await _reddit_get(client, url, params)
    except httpx.HTTPError as e:
        errors.append(ErrorItem(url, sub_name, f"Reddit 请求失败: {e}"))
        return []
    if not data:
        return []
    posts = [c["data"] for c in data.get("data", {}).get("children", []) if c.get("kind") == "t3"]
    return await _reddit_process_posts(client, posts, cutoff, "subreddit", sub_name,
                                       int(cfg.get("min_score", 10)), fetch_comments)


async def _reddit_fetch_user(
    client: httpx.AsyncClient, cfg: dict, cutoff: Optional[datetime], errors: list,
) -> list:
    username = cfg["username"]
    params = {
        "limit": min(int(cfg.get("fetch_limit", 10)), 100),
        "sort": cfg.get("sort", "new"),
        "raw_json": 1,
    }
    url = f"{REDDIT_BASE}/user/{username}/submitted.json"
    try:
        data = await _reddit_get(client, url, params)
    except httpx.HTTPError as e:
        errors.append(ErrorItem(url, username, f"Reddit 请求失败: {e}"))
        return []
    if not data:
        return []
    posts = [c["data"] for c in data.get("data", {}).get("children", []) if c.get("kind") == "t3"]
    return await _reddit_process_posts(client, posts, cutoff, "user", username, 0, 0)


async def _reddit_process_posts(
    client: httpx.AsyncClient,
    posts: list,
    cutoff: Optional[datetime],
    subtype: str,
    source_name: str,
    min_score: int,
    fetch_comments: int,
) -> list:
    valid = []
    for post in posts:
        created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)
        if cutoff is not None and created < cutoff:
            continue
        if post.get("score", 0) < min_score:
            continue
        valid.append(post)
    if not valid:
        return []

    if fetch_comments > 0:
        sem = asyncio.Semaphore(REDDIT_COMMENT_CONCURRENCY)

        async def _wrapped(post):
            async with sem:
                return await _reddit_fetch_comments(client, post.get("subreddit", ""), post["id"], fetch_comments)

        comment_lists = await asyncio.gather(
            *[_wrapped(p) for p in valid], return_exceptions=True
        )
    else:
        comment_lists = [[] for _ in valid]

    items = []
    for post, comments in zip(valid, comment_lists):
        if isinstance(comments, Exception):
            comments = []
        items.append(_reddit_parse_post(post, comments, subtype, source_name))
    return items


async def _reddit_fetch_comments(
    client: httpx.AsyncClient, subreddit: str, post_id: str, limit: int
) -> list:
    url = f"{REDDIT_BASE}/r/{subreddit}/comments/{post_id}.json"
    params = {"limit": limit, "depth": 1, "sort": "top", "raw_json": 1}
    try:
        data = await _reddit_get(client, url, params)
    except httpx.HTTPError as e:
        # 评论抓取失败不阻塞帖子本身，仅降级为无评论
        logger.warning("Reddit 评论请求失败 %s: %s", url, e)
        return []
    if not data or not isinstance(data, list) or len(data) < 2:
        return []
    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child["data"]
        if c.get("body") and c.get("distinguished") != "moderator":
            comments.append(c)
    comments.sort(key=lambda c: c.get("score", 0), reverse=True)
    return comments[:limit]


def _reddit_parse_post(post: dict, comments: list, subtype: str, source_name: str) -> NewsItem:
    post_id = post["id"]
    is_self = post.get("is_self", False)
    subreddit = post.get("subreddit", "")
    discussion_url = f"https://www.reddit.com{post.get('permalink', '')}"
    url = discussion_url if is_self else post.get("url", discussion_url)

    parts = []
    if post.get("selftext"):
        text = post["selftext"]
        if len(text) > 1500:
            text = text[:1497] + "..."
        parts.append(text)
    if comments:
        parts.append("\n--- Top Comments ---")
        for c in comments:
            commenter = c.get("author", "anon")
            body = (c.get("body", "") or "").strip()
            if len(body) > 500:
                body = body[:497] + "..."
            parts.append(f"[{commenter} ({c.get('score', 0)} pts)]: {body}")

    return NewsItem(
        title=post.get("title", ""),
        url=url,
        content="\n\n".join(parts),
        author=post.get("author", "unknown"),
        publish_time=datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc),
        source=source_name,
        metadata={
            "subtype": subtype,
            "score": post.get("score", 0),
            "upvote_ratio": post.get("upvote_ratio"),
            "num_comments": post.get("num_comments", 0),
            "subreddit": subreddit,
            "is_self": is_self,
            "flair": post.get("link_flair_text"),
            "discussion_url": discussion_url,
        },
    )


async def _reddit_get(client: httpx.AsyncClient, url: str, params: dict) -> Optional[Any]:
    """GET Reddit JSON。403 评论请求返回 None（降级为无评论）；其余失败抛 HTTPError 由调用方处理。"""
    resp = await client.get(
        url, params=params, headers=REDDIT_HEADERS, follow_redirects=True
    )
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 5))
        logger.warning("Reddit rate limited, retrying after %ds", retry_after)
        await asyncio.sleep(retry_after)
        resp = await client.get(
            url, params=params, headers=REDDIT_HEADERS, follow_redirects=True
        )
    if resp.status_code == 403 and "/comments/" in url:
        logger.info("Reddit blocked comments request for %s; continuing without comments", url)
        return None
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Twitter (via Apify altimis/scweet)
# ---------------------------------------------------------------------------

async def fetch_twitter(
    client: httpx.AsyncClient,
    src: dict,
    cutoff: Optional[datetime],
    errors: list,
) -> list:
    name = "twitter"
    users = [u.strip().lstrip("@") for u in (src.get("users") or []) if u.strip()]
    if not users:
        return []

    token_env = src.get("apify_token_env", "APIFY_TOKEN")
    token = os.environ.get(token_env)
    if not token:
        logger.warning("Twitter: 环境变量 %s 未设置，跳过 Twitter。", token_env)
        return []

    actor_id = src.get("actor_id", "altimis~scweet")
    fetch_limit = int(src.get("fetch_limit", 10))

    run_id, dataset_id = await _apify_start_run(client, token, actor_id, users, fetch_limit)
    if not run_id:
        errors.append(ErrorItem("", name, "Apify 启动运行失败"))
        return []
    if not await _apify_wait_for_run(client, token, run_id):
        errors.append(ErrorItem("", name, f"Apify 运行未成功完成: {run_id}"))
        return []
    raw_items = await _apify_fetch_dataset(client, token, dataset_id)

    items: list = []
    for raw in raw_items:
        if isinstance(raw, dict) and raw.get("noResults"):
            continue
        parsed = _twitter_parse_item(raw, cutoff)
        if parsed:
            items.append(parsed)
    return items


async def _apify_start_run(
    client: httpx.AsyncClient, token: str, actor_id: str, users: list, fetch_limit: int
) -> tuple:
    payload = {
        "source_mode": "profiles",
        "profile_urls": users,
        "search_sort": "Latest",
        "max_items": max(100, fetch_limit),
    }
    url = f"{APIFY_BASE}/acts/{actor_id}/runs?token={token}"
    try:
        resp = await client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()["data"]
        return data["id"], data["defaultDatasetId"]
    except Exception as exc:
        logger.error("Failed to start Apify run: %s", exc)
        return None, None


async def _apify_wait_for_run(client: httpx.AsyncClient, token: str, run_id: str) -> bool:
    url = f"{APIFY_BASE}/actor-runs/{run_id}?token={token}"
    elapsed = 0.0
    while elapsed < APIFY_MAX_WAIT:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            status = resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                return True
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.error("Apify run %s ended with status: %s", run_id, status)
                return False
        except Exception as exc:
            logger.warning("Error polling Apify run %s: %s", run_id, exc)
        await asyncio.sleep(APIFY_POLL_INTERVAL)
        elapsed += APIFY_POLL_INTERVAL
    logger.warning("Apify run %s timed out after %ds.", run_id, APIFY_MAX_WAIT)
    return False


async def _apify_fetch_dataset(client: httpx.AsyncClient, token: str, dataset_id: str) -> list:
    url = f"{APIFY_BASE}/datasets/{dataset_id}/items?token={token}"
    try:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to fetch Apify dataset %s: %s", dataset_id, exc)
        return []


def _twitter_parse_item(item: dict, cutoff: Optional[datetime]) -> Optional[NewsItem]:
    try:
        created_at_str = item.get("created_at")
        if not created_at_str:
            return None
        try:
            published_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            published_at = isoparse(created_at_str)
        published_at = to_utc(published_at)
        if cutoff is not None and published_at < cutoff:
            return None

        raw_id = item.get("id") or ""
        numeric_id = str(raw_id).replace("tweet-", "") if str(raw_id).startswith("tweet-") else str(
            item.get("id_str") or raw_id
        )
        if not numeric_id:
            return None

        conversation_id = str(
            item.get("conversation_id")
            or item.get("tweet", {}).get("conversation_id")
            or numeric_id
        )

        user = item.get("user") or {}
        screen_name = (
            user.get("screen_name")
            or user.get("username")
            or user.get("handle")
            or item.get("handle")
            or item.get("username")
            or "unknown"
        )
        author = user.get("name") or screen_name

        text = unescape((item.get("full_text") or item.get("text") or "").strip())
        if not text:
            return None

        url = item.get("url") or f"https://twitter.com/{screen_name}/status/{numeric_id}"
        title_body = text[:50].replace("\n", " ").strip()
        if len(text) > 50:
            title_body += "..."

        return NewsItem(
            title=f"@{screen_name}: {title_body}",
            url=url,
            content=text,
            author=author,
            publish_time=published_at,
            source=screen_name,
            metadata={
                "tweet_id": numeric_id,
                "conversation_id": conversation_id,
                "favorite_count": item.get("favorite_count", 0),
                "retweet_count": item.get("retweet_count", 0),
                "reply_count": item.get("reply_count", 0),
                "view_count": item.get("view_count"),
                "is_reply": item.get("is_reply", False),
                "in_reply_to_status_id": item.get("in_reply_to_status_id"),
                "in_reply_to_screen_name": item.get("in_reply_to_screen_name"),
            },
        )
    except Exception as exc:
        logger.debug("Failed to parse tweet: %s", exc)
        return None


# ---------------------------------------------------------------------------
# 调度与主入口
# ---------------------------------------------------------------------------

FETCHERS = {
    "rss": fetch_rss,
    "hackernews": fetch_hackernews,
    "reddit": fetch_reddit,
    "twitter": fetch_twitter,
}


async def run_all(config: dict, cutoff: Optional[datetime]) -> tuple:
    """并行抓取所有源，返回 (items, errors)。"""
    timeout = float(config.get("http_timeout", 30))
    headers = {"User-Agent": USER_AGENT}
    errors: list = []
    sources = config.get("sources") or []

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        tasks = []
        for src in sources:
            fetcher = FETCHERS.get(src.get("type"))
            if fetcher is None:
                errors.append(ErrorItem(
                    src.get("url", ""),
                    src.get("name", src.get("type", "?")),
                    f"未知源类型: {src.get('type')}",
                ))
                continue
            tasks.append(fetcher(client, src, cutoff, errors))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list = []
    for src, result in zip(sources, results):
        src_name = src.get("name", src.get("type", "?"))
        if isinstance(result, Exception):
            errors.append(ErrorItem(src.get("url", ""), src_name, f"{type(result).__name__}: {result}"))
        elif isinstance(result, list):
            items.extend(result)
    return items, errors


def load_config(path: str) -> dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_jsonl(path: Optional[str], records: list) -> None:
    def _emit(line: str) -> None:
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            sys.stdout.write(line + "\n")

    for rec in records:
        _emit(json.dumps(rec, ensure_ascii=False))


def list_sources(config: dict) -> None:
    sources = config.get("sources") or []
    print(f"共 {len(sources)} 个数据源：")
    for i, src in enumerate(sources, 1):
        print(f"  {i}. [{src.get('type')}] {src.get('name', src.get('url', ''))}")


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="多源新闻下载器（RSS/HN/Reddit/Twitter → JSONL）")
    parser.add_argument("--config", required=True, help="配置文件路径（YAML）")
    parser.add_argument("--output", default=None, help="输出 JSONL 文件路径；缺省输出到 stdout")
    parser.add_argument("--errors", default=None, help="失败条目 JSONL 文件路径（可选）")
    parser.add_argument("--no-filter", action="store_true", help="不过滤时间窗口")
    parser.add_argument("--list-sources", action="store_true", help="仅打印配置的源后退出")
    return parser.parse_args(argv)


def main(argv: list = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"配置文件不存在: {args.config}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"加载配置失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.list_sources:
        list_sources(config)
        return 0

    window = float(config.get("time_window_hours", 48))
    cutoff = None if args.no_filter else (datetime.now(timezone.utc) - timedelta(hours=window))

    # 清空输出文件
    if args.output:
        open(args.output, "w", encoding="utf-8").close()
    if args.errors:
        open(args.errors, "w", encoding="utf-8").close()

    items, errors = asyncio.run(run_all(config, cutoff))

    write_jsonl(args.output, [it.to_dict() for it in items])
    write_jsonl(args.errors, [e.to_dict() for e in errors]) if args.errors else None

    print(
        f"抓取完成: 成功 {len(items)} 条，失败 {len(errors)} 条"
        + (f"，输出到 {args.output}" if args.output else "（输出到 stdout）"),
        file=sys.stderr,
    )
    for err in errors:
        print(f"  ⚠ [{err.source}] {err.url or '-'}: {err.error}", file=sys.stderr)

    return 0 if items else 1


if __name__ == "__main__":
    sys.exit(main())
