"""Glints internship scraper — cari lowongan magang di glints.com."""

from __future__ import annotations

import re

from pkl_research.models import Company
from pkl_research.scraper.plugins.base import BaseScraper


class GlintsScraper(BaseScraper):
    source = "glints"

    def collect(self, page, query: str, region: dict) -> list[Company]:
        q = self._clean_query(query)
        lang = region.get("lang", "id")
        base = "https://glints.com/id/lowongan-kerja" if lang == "id" else "https://glints.com/en/opportunities"
        url = f"{base}?keyword={q.replace(' ', '%20')}&categories=INTERNSHIP"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        except Exception:
            return []
        page.wait_for_timeout(5000)

        companies: list[Company] = []
        cards = page.locator("a[data-testid='job-card'], a[href*='/lowongan-kerja/detail/'], a[href*='/opportunities/detail/']")
        for i in range(min(cards.count(), 30)):
            try:
                el = cards.nth(i)
                href = el.get_attribute("href") or ""
                text = (el.inner_text() or "").strip()
            except Exception:
                continue
            if not text or len(text) < 5:
                continue
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            name = lines[0][:80] if lines else f"Glints Result {i+1}"
            role = lines[1][:60] if len(lines) > 1 else ""
            companies.append(Company(
                place_id=f"glints:{abs(hash(name + href)) % 10**12}",
                name=name,
                category="internship",
                role_fit=self._detect_roles(text.lower()),
                maps_url=href if href.startswith("http") else "",
            ))
        return companies[:20]

    @staticmethod
    def _clean_query(query: str) -> str:
        q = re.sub(r"\b(jakarta selatan|jakarta|indonesia)\b", "", query, flags=re.I).strip()
        return q or "software intern"

    @staticmethod
    def _detect_roles(text: str) -> list[str]:
        roles = []
        for kw, tag in [("ai", "ai"), ("machine learning", "ai"), ("software", "software"),
                        ("developer", "fullstack"), ("web", "fullstack"), ("game", "game")]:
            if kw in text:
                roles.append(tag)
        return roles or ["software"]
