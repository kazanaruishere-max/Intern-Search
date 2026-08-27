"""Lever public board API vacancy source."""

from __future__ import annotations

from datetime import datetime, timezone

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class LeverSource(VacancySource):
    source = "lever"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        if not board_token:
            return []

        url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
        jobs = fetch_json(url)
        if not jobs or not isinstance(jobs, list):
            return []

        vacancies = []
        q_lower = query.lower()

        for job in jobs:
            title = job.get("title", "")
            desc = job.get("description", "") or job.get("descriptionPlain", "")
            categories = job.get("categories", {})
            location = categories.get("location", "Remote")
            commitment = categories.get("commitment", "")

            if q_lower not in title.lower() and q_lower not in desc.lower():
                continue

            emp_type = "fulltime"
            if _is_intern(title, desc, commitment):
                emp_type = "intern"
            elif _is_freelance(title, desc, commitment):
                emp_type = "freelance"
            elif _is_contract(title, desc, commitment):
                emp_type = "contract"

            posted = None
            created_at = job.get("createdAt")
            if created_at and isinstance(created_at, (int, float)):
                try:
                    posted = datetime.fromtimestamp(created_at / 1000.0, timezone.utc).isoformat()
                except Exception:
                    pass

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
                    url=job.get("hostedUrl"),
                    posted_at=posted,
                )
            )
            if len(vacancies) >= limit:
                break
        return vacancies
