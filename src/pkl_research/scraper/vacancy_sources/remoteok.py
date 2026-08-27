"""RemoteOK API vacancy source."""

from __future__ import annotations

import re
from datetime import datetime

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json
from pkl_research.scraper.vacancy_sources.remotive import _is_contract, _is_freelance, _is_intern


class RemoteokSource(VacancySource):
    source = "remoteok"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        # RemoteOK uses tags for query
        tag = query.replace(" ", "-").lower()
        url = f"https://remoteok.com/api?tag={tag}"
        data = fetch_json(url)
        if not data or not isinstance(data, list):
            return []

        vacancies = []
        for item in data:
            # Skip the first legal disclaimer object
            if "legal" in item:
                continue

            title = item.get("position", "")
            desc = item.get("description", "")
            tags = item.get("tags", [])
            tag_str = " ".join(tags)

            emp_type = "fulltime"
            if _is_intern(title, desc, tag_str):
                emp_type = "intern"
            elif _is_freelance(title, desc, tag_str):
                emp_type = "freelance"
            elif _is_contract(title, desc, tag_str):
                emp_type = "contract"

            # RemoteOK provides direct salary_min/salary_max keys sometimes
            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            
            # Map salary to float or None
            try:
                sal_min = float(sal_min) if sal_min is not None else None
                sal_max = float(sal_max) if sal_max is not None else None
            except ValueError:
                sal_min = sal_max = None

            currency = "USD" if (sal_min or sal_max) else None

            posted = item.get("date", "")
            if posted:
                try:
                    posted = datetime.fromisoformat(posted.replace("Z", "+00:00")).isoformat()
                except Exception:
                    pass

            vacancies.append(
                Vacancy(
                    source=self.source,
                    source_id=str(item.get("id")),
                    title=title,
                    company_name=item.get("company", "Unknown"),
                    location=item.get("location", "Remote"),
                    remote=True,
                    employment_type=emp_type,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    currency=currency,
                    description_text=desc,
                    tags=tags,
                    url=item.get("url"),
                    posted_at=posted,
                )
            )
            if len(vacancies) >= limit:
                break
        return vacancies
