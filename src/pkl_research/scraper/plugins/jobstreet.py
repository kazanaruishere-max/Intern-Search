"""JobStreet internship search."""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class JobstreetScraper(BaseScraper):
    source = "jobstreet"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        q = query.replace(" ", "+")
        url = f"https://www.jobstreet.co.id/id/job-search/jobs?q={q}&workType=Internship"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        except Exception:
            return []
        page.wait_for_timeout(5000)

        companies: list[Company] = []
        cards = page.locator("article[data-automation='normalJob'], div[data-automation='jobCard']")
        for i in range(min(cards.count(), 25)):
            try:
                card = cards.nth(i)
                title_el = card.locator("a[data-automation='jobTitle'], h3 a, h1 a").first
                company_el = card.locator("[data-automation='companyName'], span[data-testid='company-name']").first
                title = (title_el.inner_text() or "").strip()[:80] if title_el.count() else ""
                cname = (company_el.inner_text() or "").strip()[:60] if company_el.count() else ""
                href = (title_el.get_attribute("href") or "") if title_el.count() else ""
            except Exception:
                continue
            if not title:
                continue
            companies.append(Company(
                place_id=f"jobstreet:{abs(hash(title + cname)) % 10**12}",
                name=f"{title} @ {cname}" if cname else title,
                category="internship",
                role_fit=self._detect_roles((title + " " + cname).lower()),
            ))
        return companies[:20]

    @staticmethod
    def _detect_roles(text: str) -> list[str]:
        roles = []
        for kw, tag in [("ai", "ai"), ("software", "software"), ("developer", "fullstack"),
                        ("web", "fullstack"), ("game", "game")]:
            if kw in text.lower():
                roles.append(tag)
        return roles or ["software"]
