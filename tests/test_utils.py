import unittest
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import (
    calculate_article_hash,
    clean_html,
    clean_summary_text,
    deduplicate_articles,
    is_recent,
    parse_date,
    truncate_text,
)


class UtilsTests(unittest.TestCase):
    def test_clean_html_strips_tags_and_decodes(self) -> None:
        raw = "<p>Hi &amp; bye</p><br> <b>bold</b>"
        self.assertEqual(clean_html(raw), "Hi & bye bold")

    def test_clean_summary_text_removes_hn_boilerplate(self) -> None:
        raw = '<p>Article URL: <a href="https://example.com">https://example.com</a></p><p>Comments URL: <a href="https://news.ycombinator.com">https://news.ycombinator.com</a></p>'
        self.assertEqual(clean_summary_text(raw), "")

    def test_parse_date_supports_iso(self) -> None:
        dt = parse_date("2026-01-31T18:37:56-05:00")
        self.assertIsNotNone(dt)
        assert dt is not None
        self.assertIsNotNone(dt.tzinfo)
        self.assertEqual(dt.year, 2026)

    def test_parse_date_supports_rfc822(self) -> None:
        dt = parse_date("Mon, 02 Feb 2026 06:48:10 +0000")
        self.assertIsNotNone(dt)

    def test_is_recent_filters_old_iso(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        article = {"published": old}
        self.assertFalse(is_recent(article, hours=48))

    def test_truncate_text_short(self) -> None:
        self.assertEqual(truncate_text("short", max_length=10), "short")

    def test_truncate_text_long(self) -> None:
        text = "one two three four five"
        result = truncate_text(text, max_length=10)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 13)

    def test_calculate_article_hash_stable(self) -> None:
        article = {"title": "A", "link": "https://example.com"}
        self.assertEqual(calculate_article_hash(article), calculate_article_hash(article))

    def test_deduplicate_articles(self) -> None:
        articles = [
            {"title": "A", "link": "1", "hash": "x"},
            {"title": "A", "link": "1", "hash": "x"},
            {"title": "B", "link": "2", "hash": "y"}
        ]
        unique = deduplicate_articles(articles)
        self.assertEqual(len(unique), 2)


if __name__ == "__main__":
    unittest.main()
