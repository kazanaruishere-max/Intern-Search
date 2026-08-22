"""LinkedIn internship search — requires Camofox."""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class LinkedinScraper(BaseScraper):
    source = "linkedin"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        page.goto(
            f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&f_TPR=r604800&f_JT=I",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(4000)
        companies: list[Company] = []
        for el in page.locator("a.job-card-container__link").all():
            try:
                href = el.get_attribute("href") or ""
                name = (el.inner_text() or "").strip()[:60]
            except Exception:
                continue
            if not name:
                continue
            companies.append(Company(place_id=f"linkedin:{href[:80]}", name=name, category="internship"))
        return companies[:20]
