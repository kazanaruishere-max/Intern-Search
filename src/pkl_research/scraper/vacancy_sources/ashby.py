"""Ashby public board API vacancy source."""

from __future__ import annotations

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class AshbySource(VacancySource):
    source = "ashby"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        if not board_token:
            return []

        url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
        data = fetch_json(url)
        if not data or not isinstance(data, dict) or "jobs" not in data:
            return []

        jobs = data["jobs"]
        vacancies = []
        q_lower = query.lower()

        for job in jobs:
            title = job.get("title", "")
            desc = job.get("jobDescriptionPlain", "") or job.get("jobDescriptionHtml", "")
            location = job.get("location", "Remote")
            employment_type_raw = job.get("employmentType", "")

            if q_lower not in title.lower() and q_lower not in desc.lower():
                continue

            emp_type = "fulltime"
            if _is_intern(title, desc, employment_type_raw):
                emp_type = "intern"
            elif _is_freelance(title, desc, employment_type_raw):
                emp_type = "freelance"
            elif _is_contract(title, desc, employment_type_raw):
                emp_type = "contract"

            posted = job.get("publishedAt")

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
                    url=job.get("infoUrl"),
                    posted_at=posted,
                )
            )
            if len(vacancies) >= limit:
                break
        return vacancies
