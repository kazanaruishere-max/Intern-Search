"""Greenhouse public board API vacancy source."""

from __future__ import annotations

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class GreenhouseSource(VacancySource):
    source = "greenhouse"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        if not board_token:
            return []

        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        data = fetch_json(url)
        if not data or not isinstance(data, dict) or "jobs" not in data:
            return []

        jobs = data["jobs"]
        vacancies = []
        q_lower = query.lower()

        for job in jobs:
            title = job.get("title", "")
            desc = job.get("content", "")
            location = job.get("location", {}).get("name", "Remote")
            
            # Simple keyword search/filter
            if q_lower not in title.lower() and q_lower not in desc.lower():
                continue

            emp_type = "fulltime"
            if _is_intern(title, desc, ""):
                emp_type = "intern"
            elif _is_freelance(title, desc, ""):
                emp_type = "freelance"
            elif _is_contract(title, desc, ""):
                emp_type = "contract"

            posted = job.get("updated_at")

            vacancies.append(
                Vacancy(
                    source=self.source,
                    source_id=f"{board_token}:{job.get('id')}",
                    title=title,
                    company_name=board_token.title(),
                    location=location,
                    remote="remote" in location.lower() or "remote" in title.lower(),
                    employment_type=emp_type,
                    description_text=desc,
                    url=job.get("absolute_url"),
                    posted_at=posted,
                )
            )
            if len(vacancies) >= limit:
                break
        return vacancies
