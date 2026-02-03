import html
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import hashlib


_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_html(text: Optional[str]) -> str:
    """Remove HTML tags and decode entities from text."""
    if not text:
        return ""

    text = html.unescape(text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = re.sub(r"(?i)</p\s*>", " ", text)
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def clean_summary_text(text: Optional[str]) -> str:
    """Clean common RSS/aggregator boilerplate from summaries."""
    cleaned = clean_html(text)
    if not cleaned:
        return ""

    # Hacker News RSS often injects boilerplate like "Article URL:" / "Comments URL:".
    cleaned = re.sub(r"(?i)\b(Article URL|Comments URL)\b\s*:\s*\S+.*$", "", cleaned).strip()
    cleaned = _WS_RE.sub(" ", cleaned).strip(" -")
    return cleaned


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from RSS feeds."""
    if not date_str or date_str == 'Unknown date':
        return None

    try:
        # ISO-8601 / RFC-3339 (e.g. 2026-01-31T18:37:56-05:00 or ...Z)
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception:
        pass

    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
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
    text = clean_summary_text(text)
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
