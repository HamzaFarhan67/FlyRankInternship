# The Polite Scraper

## Run

```bash
cd assignment4week5
python -m pip install -r requirements.txt
python src/main.py
```

Use `python src/main.py --include-failure` to verify that one broken URL is skipped and reported.

## Target classification

The target is Books to Scrape, a public practice sandbox designed for scraping exercises. This scraper processes only the first three catalogue pages, discovers their 60 book URLs, and collects title, product URL, price, availability, rating, description, source page, and fetch time. This limited scope is appropriate because the site is explicitly provided for practice.

The site's `robots.txt` was requested before development and returned 404, so no robots file was found. A missing robots file is not treated as permission to reuse this code elsewhere.

I will not reuse this code on another site without checking its rules and terms first.

## Design

This is the Python lane using Requests, Beautiful Soup, and Pydantic. Real requests identify the scraper, use a ten-second timeout, wait at least 500 milliseconds between requests, check the status code, and retry once for a timeout or server error. Catalogue and detail HTML is cached locally, so development reruns do not repeatedly contact the site.

Validated records are written to `output/books.json`. Invalid records are written to `output/errors.json`, and every run writes `output/run-report.json`. Product URLs are unique, and `price_gbp` is numeric.

The core assignment needs no browser because the data is already in the HTML sent by the server, so a browser would only add cost.

Use an official API when one exists. Never bypass logins, paywalls, or blocks, and collect only what is needed.
