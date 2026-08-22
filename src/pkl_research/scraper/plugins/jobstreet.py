"""JobStreet internship search."""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class JobstreetScraper(BaseScraper):
    source = "jobstreet"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        page.goto(
            f"https://www.jobstreet.co.id/id/job-search/jobs/?q={query.replace(' ', '+')}&workType=Internship",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(3000)
        companies: list[Company] = []
        for el in page.locator("a[data-automation='jobTitle'], h3 a").all():
            try:
                href = el.get_attribute("href") or ""
                name = (el.inner_text() or "").strip()[:60]
            except Exception:
                continue
            if not name:
                continue
            companies.append(Company(place_id=f"jobstreet:{href[:80]}", name=name, category="internship"))
        return companies[:20]
