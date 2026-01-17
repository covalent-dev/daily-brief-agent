import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import feedparser

from utils import calculate_article_hash, deduplicate_articles, filter_recent_articles

logger = logging.getLogger(__name__)


def fetch_articles(feed_config: Dict, max_articles: int = 5) -> List[Dict]:
    """Fetch articles from a single RSS feed."""
    logger.info(f"📡 Fetching: {feed_config['name']}...")

    try:
        feed = feedparser.parse(feed_config['url'])

        if feed.bozo:
            logger.warning(f"  ⚠️  Feed parsing warning for {feed_config['name']}")

        articles = []
        for entry in feed.entries[:max_articles]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', 'No summary')),
                'published': entry.get('published', 'Unknown date'),
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
        return {'articles': [], 'timestamp': None}

    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
            logger.info(f"  ℹ️  Loaded cache from {cache.get('timestamp', 'unknown time')}")
            return cache
    except Exception as e:
        logger.warning(f"  ⚠️  Could not load cache: {e}")
        return {'articles': [], 'timestamp': None}


def save_cache(cache_file: Path, articles: List[Dict]) -> None:
    """Save articles to cache."""
    cache = {
        'articles': articles,
        'timestamp': datetime.now().isoformat()
    }

    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
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


def fetch_all_articles(config: Dict, cache_file: Path, use_cache: bool = True) -> List[Dict]:
    """Fetch from all configured feeds."""
    if use_cache:
        cache = load_cache(cache_file)
        if cache.get('timestamp'):
            cache_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info("✓ Using cached articles (less than 1 hour old)")
                return cache['articles']

    all_articles = []
    max_per_feed = config['settings']['max_articles_per_feed']

    for feed_config in config['feeds']:
        if not should_fetch_feed(feed_config):
            logger.info(f"⏭️  Skipping {feed_config['name']} (not scheduled for today)")
            continue
        articles = fetch_articles(feed_config, max_per_feed)
        all_articles.extend(articles)

    logger.info(f"\n📰 Total articles fetched: {len(all_articles)}")

    all_articles = deduplicate_articles(all_articles)
    logger.info(f"📰 Unique articles: {len(all_articles)}")

    filter_hours = config['settings'].get('filter_hours', 48)
    all_articles = filter_recent_articles(all_articles, filter_hours)
    logger.info(f"📰 Recent articles: {len(all_articles)}\n")

    save_cache(cache_file, all_articles)

    return all_articles
