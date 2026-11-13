import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternshipA9/1.0 (https://github.com/HamzaFarhan67/FlyRankInternship)"
TIMEOUT = 10
DELAY = 0.5


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str
    price_gbp: float


class Scraper:
    def __init__(self) -> None:
        self.cache_dir = ROOT / "cache"
        self.output_dir = ROOT / "output"
        self.cache_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.last_request = 0.0
        self.pages_fetched = 0
        self.cache_hits = 0
        self.failed_pages = []

    def _wait(self) -> None:
        elapsed = monotonic() - self.last_request
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

    def fetch(self, url: str, cache_path: Path) -> Optional[str]:
        if cache_path.exists():
            self.cache_hits += 1
            print(f"CACHE HIT {url}")
            return cache_path.read_text(encoding="utf-8")

        for attempt in range(2):
            print(f"FETCH {url}")
            self._wait()
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                self.last_request = monotonic()
                self.pages_fetched += 1
            except requests.RequestException as error:
                self.last_request = monotonic()
                if attempt == 0:
                    continue
                self.failed_pages.append({"url": url, "reason": str(error)})
                return None

            if response.status_code == 200:
                cache_path.write_text(response.text, encoding="utf-8")
                return response.text
            if response.status_code >= 500 and attempt == 0:
                continue
            self.failed_pages.append(
                {"url": url, "reason": f"HTTP {response.status_code}"}
            )
            return None
        return None

    def catalogue_cache_path(self, page_number: int) -> Path:
        return self.cache_dir / f"catalogue-page-{page_number}.html"

    def detail_cache_path(self, url: str) -> Path:
        name = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"detail-{name}.html"

    def discover(self) -> list[tuple[str, str]]:
        page_url = BASE_URL
        books = []
        for page_number in range(1, 4):
            html = self.fetch(page_url, self.catalogue_cache_path(page_number))
            if html is None:
                break
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select("article.product_pod h3 a"):
                product_url = urljoin(page_url, link.get("href", ""))
                books.append((product_url, page_url))
            next_link = soup.select_one("li.next a")
            if next_link is None:
                break
            page_url = urljoin(page_url, next_link.get("href", ""))
        unique = {}
        for product_url, source_page in books:
            unique.setdefault(product_url, source_page)
        return list(unique.items())

    def extract(self, url: str, source_page: str) -> Optional[dict]:
        html = self.fetch(url, self.detail_cache_path(url))
        if html is None:
            return None
        soup = BeautifulSoup(html, "html.parser")
        product = soup.select_one("div.product_main")
        if product is None:
            self.failed_pages.append({"url": url, "reason": "product area missing"})
            return None
        price = product.select_one(".price_color")
        availability = product.select_one(".availability")
        rating = product.select_one(".star-rating")
        description = soup.select_one("#product_description + p")
        raw_price = price.get_text(" ", strip=True) if price else ""
        price_match = re.search(r"\d+(?:\.\d+)?", raw_price)
        return {
            "title": product.select_one("h1").get_text(" ", strip=True),
            "product_url": url,
            "price_text": raw_price,
            "availability_text": availability.get_text(" ", strip=True) if availability else "",
            "rating_text": " ".join(rating.get("class", [])[1:]) if rating else "",
            "description": description.get_text(" ", strip=True) if description else None,
            "source_page": source_page,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "price_gbp": float(price_match.group()) if price_match else None,
        }

    def run(self, include_failure: bool) -> dict:
        started = datetime.now(timezone.utc)
        discovered = self.discover()
        if include_failure:
            discovered.append(("https://books.toscrape.com/not-a-real-book/", BASE_URL))
        records = []
        errors = []
        for url, source_page in discovered:
            try:
                raw = self.extract(url, source_page)
                if raw is None:
                    continue
                record = BookRecord(**raw)
                records.append(json.loads(record.json()))
            except (ValidationError, AttributeError, TypeError, ValueError) as error:
                errors.append({"url": url, "reason": str(error)})
        books_by_url = {record["product_url"]: record for record in records}
        (self.output_dir / "books.json").write_text(
            json.dumps(list(books_by_url.values()), indent=2),
            encoding="utf-8",
        )
        (self.output_dir / "errors.json").write_text(
            json.dumps(errors + self.failed_pages, indent=2),
            encoding="utf-8",
        )
        finished = datetime.now(timezone.utc)
        report = {
            "started_at": started.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "catalogue_pages": 3,
            "discovered": len(discovered),
            "unique_urls": len({url for url, _ in discovered}),
            "pages_fetched": self.pages_fetched,
            "cache_hits": self.cache_hits,
            "valid_records": len(books_by_url),
            "invalid_records": len(errors),
            "failed_pages": len(self.failed_pages),
        }
        (self.output_dir / "run-report.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-failure", action="store_true")
    args = parser.parse_args()
    report = Scraper().run(args.include_failure)
    print(
        f"catalogue_pages={report['catalogue_pages']} "
        f"discovered={report['discovered']} unique_urls={report['unique_urls']} "
        f"detail_pages={report['valid_records']} valid_records={report['valid_records']} "
        f"failed_pages={report['failed_pages']}"
    )


if __name__ == "__main__":
    main()
