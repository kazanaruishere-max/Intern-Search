"""Himalayas API vacancy source."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class HimalayasSource(VacancySource):
    source = "himalayas"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        import urllib.parse
        q = urllib.parse.quote(query)
        url = f"https://himalayas.app/jobs/api?query={q}&limit={limit}"
        data = fetch_json(url)
        if not data or not isinstance(data, dict) or "jobs" not in data:
            return []

        jobs = data["jobs"]
        vacancies = []
        for job in jobs[:limit]:
            title = job.get("title", "")
            desc = job.get("description", "")
            
            # Extract tags/categories
            tags = job.get("categories", []) or []
            tags_str = " ".join(tags)

            emp_type = "fulltime"
            if _is_intern(title, desc, tags_str):
                emp_type = "intern"
            elif _is_freelance(title, desc, tags_str):
                emp_type = "freelance"
            elif _is_contract(title, desc, tags_str):
                emp_type = "contract"

            # Parse salary
            sal_min = job.get("salaryMin")
            sal_max = job.get("salaryMax")
            try:
                sal_min = float(sal_min) if sal_min is not None else None
                sal_max = float(sal_max) if sal_max is not None else None
            except ValueError:
                sal_min = sal_max = None

            currency = job.get("currency", "USD") if (sal_min or sal_max) else None

            posted = job.get("pubDate")
            if posted:
                try:
                    if isinstance(posted, (int, float)):
                        posted = datetime.fromtimestamp(posted, timezone.utc).isoformat()
                    else:
                        posted = datetime.fromisoformat(str(posted).replace("Z", "+00:00")).isoformat()
                except Exception:
                    pass

            vacancies.append(
                Vacancy(
                    source=self.source,
                    source_id=str(job.get("id") or hash(title + job.get("companyName", ""))),
                    title=title,
                    company_name=job.get("companyName", "Unknown"),
                    location=job.get("location", "Remote"),
                    remote=bool(job.get("remote", True)),
                    employment_type=emp_type,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    currency=currency,
                    description_text=desc,
                    tags=tags,
                    url=job.get("applicationLink") or job.get("url"),
                    posted_at=posted,
                )
            )
        return vacancies
