import json
import logging
import os
import socket
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import feedparser

from utils import (
    calculate_article_hash,
    clean_summary_text,
    deduplicate_articles,
    filter_relevant_articles,
    filter_recent_articles,
    parse_date,
)

logger = logging.getLogger(__name__)

_CACHE_VERSION = 2


def _parse_entry_datetime(entry: Dict) -> datetime | None:
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            # feedparser struct_time is UTC
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    for key in ("published", "updated", "created"):
        val = entry.get(key)
        dt = parse_date(val) if isinstance(val, str) else None
        if dt:
            return dt

    return None


def fetch_articles(feed_config: Dict, max_articles: int = 5) -> List[Dict]:
    """Fetch articles from a single RSS feed."""
    logger.info(f"📡 Fetching: {feed_config['name']}...")

    try:
        feed = feedparser.parse(feed_config['url'])

        if feed.bozo:
            bozo_error = getattr(feed, "bozo_exception", None)
            if bozo_error:
                logger.warning(f"  ⚠️  Feed parsing warning for {feed_config['name']}: {bozo_error}")
            else:
                logger.warning(f"  ⚠️  Feed parsing warning for {feed_config['name']}")

        articles = []
        for entry in feed.entries[:max_articles]:
            published_dt = _parse_entry_datetime(entry)
            published = published_dt.isoformat() if published_dt else entry.get('published', 'Unknown date')
            summary_raw = entry.get('summary', entry.get('description', 'No summary'))
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': clean_summary_text(summary_raw),
                'published': published,
                'published_raw': entry.get('published', entry.get('updated', 'Unknown date')),
                'source': feed_config['name'],
                'category': feed_config.get('category', 'General')
            }

            article['hash'] = calculate_article_hash(article)
            articles.append(article)

        logger.info(f"  ✓ Got {len(articles)} articles")
        return articles
    except Exception as e:
        logger.error(f"  ✗ Error fetching {feed_config['name']}: {e}")
        return []


def load_cache(cache_file: Path) -> Dict:
    """Load cached articles from previous run."""
    if not cache_file.exists():
        return {'articles': [], 'cached_at': None, 'timestamp': None, 'version': _CACHE_VERSION}

    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
            cached_at = cache.get('cached_at') or cache.get('timestamp')
            logger.info(f"  ℹ️  Loaded cache from {cached_at or 'unknown time'}")
            return cache
    except Exception as e:
        logger.warning(f"  ⚠️  Could not load cache: {e}")
        return {'articles': [], 'cached_at': None, 'timestamp': None, 'version': _CACHE_VERSION}


def save_cache(cache_file: Path, articles: List[Dict]) -> None:
    """Save articles to cache."""
    cached_at = datetime.now().isoformat()
    cache = {'version': _CACHE_VERSION, 'articles': articles, 'cached_at': cached_at, 'timestamp': cached_at}

    try:
        tmp = cache_file.with_suffix(".json.tmp")
        with open(tmp, 'w') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        tmp.replace(cache_file)
        logger.info(f"  ℹ️  Saved {len(articles)} articles to cache")
    except Exception as e:
        logger.warning(f"  ⚠️  Could not save cache: {e}")


def should_fetch_feed(feed_config: Dict) -> bool:
    """Check if feed should be fetched based on day filter."""
    days_filter = feed_config.get('days')
    if not days_filter:
        return True

    today = datetime.now().strftime('%A').lower()
    return today in [d.lower() for d in days_filter]


def has_network_dns() -> bool:
    """Return True if DNS resolution works."""
    if (os.getenv("DAILYBRIEF_FORCE_NETWORK_DOWN") or "").strip().lower() in {"1", "true", "yes", "y", "on"}:
        return False
    try:
        socket.getaddrinfo("example.com", 80)
        return True
    except OSError:
        return False


def fetch_all_articles_with_meta(config: Dict, cache_file: Path, use_cache: bool = True) -> tuple[List[Dict], Dict]:
    """Fetch from all configured feeds. Returns (articles, meta)."""
    cache = None
    meta: Dict = {
        "fetch_started_at": datetime.now().isoformat(),
        "network_ok": None,
        "cache_used": False,
        "cache_cached_at": None,
        "cache_age_seconds": None,
        "cache_ttl_seconds": None,
        "feed_errors": [],
    }

    cache_ttl_minutes = int(config.get("settings", {}).get("cache_ttl_minutes", 60))
    meta["cache_ttl_seconds"] = cache_ttl_minutes * 60
    if use_cache:
        cache = load_cache(cache_file)
        cached_at = cache.get("cached_at") or cache.get("timestamp")
        meta["cache_cached_at"] = cached_at
        if cached_at:
            try:
                cache_time = datetime.fromisoformat(cached_at)
                age_s = (datetime.now() - cache_time).total_seconds()
                meta["cache_age_seconds"] = age_s
            except Exception:
                age_s = None

            if age_s is not None and age_s < meta["cache_ttl_seconds"]:
                if cache.get('articles'):
                    logger.info("✓ Using cached articles (%dm old)", int(age_s // 60))
                    meta["cache_used"] = True
                    cached_articles = filter_recent_articles(cache['articles'], int(config['settings'].get('filter_hours', 48)))
                    if len(cached_articles) != len(cache['articles']):
                        logger.info("⚠️  Dropped %d stale cached items after recency filter", len(cache['articles']) - len(cached_articles))
                    before_relevance = len(cached_articles)
                    cached_articles = filter_relevant_articles(cached_articles)
                    if len(cached_articles) != before_relevance:
                        logger.info("🧹 Dropped %d cached non-tech/political articles", before_relevance - len(cached_articles))
                    return cached_articles, meta
                logger.info("⚠️  Cache is fresh but empty; refetching feeds")

    network_ok = has_network_dns()
    meta["network_ok"] = network_ok
    if not network_ok:
        logger.error("❌ Network/DNS unavailable; skipping feed fetch")
        if cache and cache.get('articles'):
            logger.info("⚠️  Using cached articles despite stale timestamp")
            meta["cache_used"] = True
            cached_articles = filter_recent_articles(cache['articles'], int(config['settings'].get('filter_hours', 48)))
            before_relevance = len(cached_articles)
            cached_articles = filter_relevant_articles(cached_articles)
            if len(cached_articles) != before_relevance:
                logger.info("🧹 Dropped %d cached non-tech/political articles", before_relevance - len(cached_articles))
            return cached_articles, meta
        meta["status"] = "network_unavailable"
        return [], meta

    all_articles = []
    max_per_feed = config['settings']['max_articles_per_feed']

    for feed_config in config['feeds']:
        if not should_fetch_feed(feed_config):
            logger.info(f"⏭️  Skipping {feed_config['name']} (not scheduled for today)")
            continue
        try:
            articles = fetch_articles(feed_config, max_per_feed)
        except Exception as e:
            meta["feed_errors"].append({"name": feed_config.get("name"), "url": feed_config.get("url"), "error": str(e)})
            logger.exception("  ✗ Unexpected error fetching %s", feed_config.get("name"))
            articles = []
        all_articles.extend(articles)

    logger.info(f"\n📰 Total articles fetched: {len(all_articles)}")

    all_articles = deduplicate_articles(all_articles)
    logger.info(f"📰 Unique articles: {len(all_articles)}")

    filter_hours = config['settings'].get('filter_hours', 48)
    all_articles = filter_recent_articles(all_articles, filter_hours)
    logger.info(f"📰 Recent articles: {len(all_articles)}\n")

    before_relevance = len(all_articles)
    all_articles = filter_relevant_articles(all_articles)
    dropped_relevance = before_relevance - len(all_articles)
    if dropped_relevance:
        logger.info(f"🧹 Dropped {dropped_relevance} non-tech/political articles")
    logger.info(f"📰 Relevant articles: {len(all_articles)}\n")

    save_cache(cache_file, all_articles)

    meta["fetch_finished_at"] = datetime.now().isoformat()
    meta["status"] = "ok"
    return all_articles, meta


def fetch_all_articles(config: Dict, cache_file: Path, use_cache: bool = True) -> List[Dict]:
    """Backward-compatible wrapper. Prefer fetch_all_articles_with_meta."""
    articles, _meta = fetch_all_articles_with_meta(config, cache_file, use_cache=use_cache)
    return articles
