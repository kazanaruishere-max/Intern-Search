"""Google Maps plugin — wraps existing search.py parsing logic."""

from __future__ import annotations

import random

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper
from pkl_research.scraper.search import parse_results, scroll_feed, search_url


class MapsScraper(BaseScraper):
    source = "maps"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        center = {"lat": region.get("lat", -6.24), "lng": region.get("lng", 106.80), "zoom": region.get("zoom", 13)}
        page.goto(search_url(query, center), wait_until="domcontentloaded")
        try:
            page.wait_for_selector("a.hfpxzc", timeout=15_000)
        except Exception:
            return []
        page.wait_for_timeout(random.randint(1500, 3000))
        scroll_feed(page)
        results = parse_results(page)
        for c in results:
            c.source = "maps"
        return results
