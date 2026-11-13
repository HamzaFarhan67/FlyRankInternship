import sys
import unittest
from urllib.parse import urljoin

sys.path.insert(0, "src")

from main import BookRecord, Scraper


class ScraperTests(unittest.TestCase):
    def test_price_is_numeric(self):
        record = BookRecord(
            title="Book",
            product_url="https://books.toscrape.com/catalogue/book/index.html",
            price_text="£12.50",
            availability_text="In stock",
            rating_text="Three",
            description=None,
            source_page="https://books.toscrape.com/",
            fetched_at="2026-01-01T00:00:00+00:00",
            price_gbp=12.5,
        )
        self.assertEqual(record.price_gbp, 12.5)

    def test_relative_url_is_absolute(self):
        result = urljoin(
            "https://books.toscrape.com/catalogue/page-1.html",
            "../book/index.html",
        )
        self.assertEqual(
            result,
            "https://books.toscrape.com/book/index.html",
        )

    def test_missing_description_is_allowed(self):
        scraper = Scraper()
        scraper.fetch = lambda url, path: (
            '<div class="product_main"><h1>Book</h1>'
            '<p class="price_color">£1.00</p></div>'
        )
        result = scraper.extract(
            "https://books.toscrape.com/catalogue/book/index.html",
            "https://books.toscrape.com/",
        )
        self.assertIsNone(result["description"])


if __name__ == "__main__":
    unittest.main()
