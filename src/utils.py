from datetime import datetime, timedelta
from typing import Dict, Optional, List
import hashlib


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from RSS feeds."""
    if not date_str or date_str == 'Unknown date':
        return None

    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def is_recent(article: Dict, hours: int = 48) -> bool:
    """Check if article is from the last N hours."""
    pub_date = parse_date(article.get('published', ''))
    if not pub_date:
        return True

    cutoff = datetime.now(pub_date.tzinfo) - timedelta(hours=hours)
    return pub_date >= cutoff


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text at word boundary."""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


def calculate_article_hash(article: Dict) -> str:
    """Generate hash for deduplication."""
    content = f"{article['title']}{article['link']}"
    return hashlib.md5(content.encode()).hexdigest()


def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on hash."""
    seen_hashes = set()
    unique_articles = []

    for article in articles:
        article_hash = article.get('hash')
        if article_hash not in seen_hashes:
            seen_hashes.add(article_hash)
            unique_articles.append(article)

    return unique_articles


def filter_recent_articles(articles: List[Dict], hours: int = 48) -> List[Dict]:
    """Filter articles to only recent ones."""
    return [a for a in articles if is_recent(a, hours)]
