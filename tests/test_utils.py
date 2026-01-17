import unittest

from utils import truncate_text, calculate_article_hash, deduplicate_articles


class UtilsTests(unittest.TestCase):
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
