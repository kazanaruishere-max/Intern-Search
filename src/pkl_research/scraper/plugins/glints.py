"""Glints internship scraper — POC for intern vacancies."""

from __future__ import annotations

import random
import re
from urllib.parse import urljoin, urlparse

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


def _norm_query(query: str) -> str:
    return re.sub(r"\b(jakarta selatan|jakarta|indonesia)\b", "", query, flags=re.I).strip() or "software intern"


class GlintsScraper(BaseScraper):
    source = "glints"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        q = _norm_query(query)
        url = f"https://glints.com/id/en/search/opportunities?keywords={q.replace(' ', '+')}&jobTypes=INTERNSHIP"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        except Exception:
            return []
        page.wait_for_timeout(random.randint(3000, 5000))
        companies: list[Company] = []
        for sel in ("a[href*='/companies/']", "a[href*='/jobs/']", "div[class*='jobCard'] a"):
            for el in page.locator(sel).all():
                try:
                    href = el.get_attribute("href") or ""
                    name = (el.inner_text() or "").strip()[:60]
                except Exception:
                    continue
                if not href or not name or len(name) < 3:
                    continue
                url_abs = urljoin(url, href)
                place_id = f"glints:{urlparse(url_abs).path.strip('/')}"
                companies.append(
                    Company(
                        place_id=place_id,
                        name=name,
                        category="internship",
                        maps_url=url_abs,
                        address=region.get("label", "") or None,
                    )
                )
            if companies:
                break
        return companies[:20]
