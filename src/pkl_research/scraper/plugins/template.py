"""Template for community-contributed source plugins.

Copy this file → my_source.py, set `source`, implement `collect`.
Register in plugins/__init__.py.
"""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class TemplateScraper(BaseScraper):
    """Example: replace with your source.

    Steps:
    1. Rename TemplateScraper + source = "my_source"
    2. Implement collect(page, query, region) -> list[Company]
    3. Register: from pkl_research.scraper.plugins.template import TemplateScraper
       then plugins.register(TemplateScraper())
    4. Use: pkl-research search --source my_source --region ID-Jakarta --backend camofox
    """

    source = "template"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        page.goto(f"https://example.com/search?q={query}", wait_until="domcontentloaded")
        companies: list[Company] = []
        for el in page.locator("a.result").all():
            try:
                name = (el.inner_text() or "").strip()[:60]
            except Exception:
                continue
            if not name:
                continue
            companies.append(Company(place_id=f"template:{name}", name=name, category="internship"))
        return companies[:20]
