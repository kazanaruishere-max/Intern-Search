"""LinkedIn internship search — butuh Camofox (anti-detect wajib)."""

from __future__ import annotations

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class LinkedinScraper(BaseScraper):
    source = "linkedin"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        q = query.replace(" ", "%20")
        geo = "102478259" if "id" in region.get("lang", "id") else ""
        url = (
            f"https://www.linkedin.com/jobs/search/?keywords={q}"
            f"&f_JT=I&f_TP=1%2C2&position=1&pageNum=0"
            + (f"&geoId={geo}" if geo else "")
        )
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        except Exception:
            return []
        page.wait_for_timeout(5000)

        companies: list[Company] = []
        cards = page.locator("div.job-card-container, li.jobs-search-results__list-item")
        for i in range(min(cards.count(), 25)):
            try:
                card = cards.nth(i)
                title_el = card.locator("h3.job-card-list__title, .job-card-container__title").first
                company_el = card.locator("h4.job-card-container__company-name, .job-card-container__primary-description").first
                link_el = card.locator("a.job-card-container__link, a.base-card__full-link").first
                title = (title_el.inner_text() or "").strip()[:80] if title_el.count() else ""
                company_name = (company_el.inner_text() or "").strip()[:60] if company_el.count() else ""
                href = (link_el.get_attribute("href") or "")[:120]
            except Exception:
                continue
            if not title:
                continue
            companies.append(Company(
                place_id=f"linkedin:{abs(hash(title + company_name)) % 10**12}",
                name=f"{title} @ {company_name}" if company_name else title,
                category="internship",
                role_fit=self._detect_roles((title + " " + company_name).lower()),
                maps_url=href,
            ))
        return companies[:20]

    @staticmethod
    def _detect_roles(text: str) -> list[str]:
        roles = []
        for kw, tag in [("ai", "ai"), ("machine learning", "ai"), ("ml ", "ai"),
                        ("software", "software"), ("developer", "fullstack"),
                        ("web", "fullstack"), ("game", "game")]:
            if kw in text.lower():
                roles.append(tag)
        return roles or ["software"]
