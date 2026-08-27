"""We Work Remotely (WWR) RSS vacancy source (zero-dependency)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_url
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class WwrSource(VacancySource):
    source = "wwr"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        import urllib.parse
        q = urllib.parse.quote(query)
        url = f"https://weworkremotely.com/jobs/search?term={q}&format=rss"
        xml_content = fetch_url(url)
        if not xml_content:
            return []

        try:
            root = ET.fromstring(xml_content.encode("utf-8"))
        except ET.ParseError:
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        vacancies = []
        for item in channel.findall("item")[:limit]:
            title_raw = item.findtext("title") or ""
            link = item.findtext("link") or ""
            guid = item.findtext("guid") or link
            desc = item.findtext("description") or ""
            pub_date_raw = item.findtext("pubDate") or ""
            categories = [c.text for c in item.findall("category") if c.text]

            # WWR RSS titles are usually "Company Name: Job Title"
            company_name = "Unknown"
            title = title_raw
            if ":" in title_raw:
                parts = title_raw.split(":", 1)
                company_name = parts[0].strip()
                title = parts[1].strip()

            emp_type = "fulltime"
            if _is_intern(title, desc, " ".join(categories)):
                emp_type = "intern"
            elif _is_freelance(title, desc, " ".join(categories)):
                emp_type = "freelance"
            elif _is_contract(title, desc, " ".join(categories)):
                emp_type = "contract"

            posted = None
            if pub_date_raw:
                try:
                    # Parse RFC 822 format (e.g. "Mon, 10 Aug 2026 12:00:00 +0000")
                    # Python's email.utils can parse this easily
                    import email.utils
                    parsed_time = email.utils.parsedate_to_datetime(pub_date_raw)
                    posted = parsed_time.isoformat()
                except Exception:
                    pass

            vacancies.append(
                Vacancy(
                    source=self.source,
                    source_id=guid.split("/")[-1] or guid,
                    title=title,
                    company_name=company_name,
                    location="Remote",
                    remote=True,
                    employment_type=emp_type,
                    description_text=desc,
                    tags=categories,
                    url=link,
                    posted_at=posted,
                )
            )
        return vacancies
