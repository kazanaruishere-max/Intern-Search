"""Indeed internship search."""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class IndeedScraper(BaseScraper):
    source = "indeed"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        q = query.replace(" ", "+")
        page.goto(f"https://id.indeed.com/jobs?q={q}&jt=internship", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        companies: list[Company] = []
        for el in page.locator("a.jcs-JobTitle, h2 a").all():
            try:
                href = el.get_attribute("href") or ""
                name = (el.inner_text() or "").strip()[:60]
            except Exception:
                continue
            if not name:
                continue
            companies.append(Company(place_id=f"indeed:{href[:80]}", name=name, category="internship"))
        return companies[:20]
