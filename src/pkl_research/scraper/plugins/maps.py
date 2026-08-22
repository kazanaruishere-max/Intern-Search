"""Google Maps plugin — wraps existing search.py."""

from __future__ import annotations

import random

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper
from pkl_research.scraper.search import parse_results, scroll_feed, search_url


class MapsScraper(BaseScraper):
    source = "maps"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        page.goto(search_url(query, region), wait_until="domcontentloaded")
        try:
            page.wait_for_selector("a.hfpxzc", timeout=15_000)
        except Exception:
            return []
        page.wait_for_timeout(random.randint(1500, 3000))
        scroll_feed(page)
        return parse_results(page)
