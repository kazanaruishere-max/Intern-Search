"""Remotive API vacancy source."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pkl_research.models import Vacancy
from pkl_research.scraper.vacancy_sources.base import VacancySource
from pkl_research.scraper.vacancy_sources.http import fetch_json


class RemotiveSource(VacancySource):
    source = "remotive"

    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        url = f"https://remotive.com/api/remote-jobs?search={urllib_quote(query)}&limit={limit}"
        data = fetch_json(url)
        if not data or not isinstance(data, dict) or "jobs" not in data:
            return []

        jobs = data["jobs"]
        vacancies = []
        for job in jobs[:limit]:
            title = job.get("title", "")
            desc = job.get("description", "")
            job_type = job.get("job_type", "")
            
            emp_type = "fulltime"
            if _is_intern(title, desc, job_type):
                emp_type = "intern"
            elif _is_freelance(title, desc, job_type):
                emp_type = "freelance"
            elif _is_contract(title, desc, job_type):
                emp_type = "contract"

            # Try to parse salary from salary string if any
            salary_str = job.get("salary", "")
            sal_min, sal_max, currency = _parse_salary(salary_str)

            posted = job.get("publication_date", "")
            if posted:
                try:
                    # Normalize ISO date
                    posted = datetime.fromisoformat(posted.replace("Z", "+00:00")).isoformat()
                except Exception:
                    pass

            tags = job.get("tags", [])

            vacancies.append(
                Vacancy(
                    source=self.source,
                    source_id=str(job.get("id")),
                    title=title,
                    company_name=job.get("company_name", "Unknown"),
                    location=job.get("candidate_required_location", "Remote"),
                    remote=True,
                    employment_type=emp_type,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    currency=currency,
                    description_text=desc,
                    tags=tags,
                    url=job.get("url"),
                    posted_at=posted,
                )
            )
        return vacancies


def urllib_quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)


def _is_intern(title: str, desc: str, job_type: str) -> bool:
    text = (title + " " + desc + " " + job_type).lower()
    return "intern" in text or "internship" in text or "magang" in text or "pkl" in text


def _is_freelance(title: str, desc: str, job_type: str) -> bool:
    text = (title + " " + desc + " " + job_type).lower()
    return "freelance" in text or "freelancer" in text or "proyekan" in text


def _is_contract(title: str, desc: str, job_type: str) -> bool:
    text = (title + " " + desc + " " + job_type).lower()
    return "contract" in text or "kontrak" in text or "temp" in text or "temporary" in text


def _parse_salary(salary_str: str) -> tuple[float | None, float | None, str | None]:
    """Cari range gaji (mis. '$50k - $70k', '$60,000') dan kembalikan min, max, currency."""
    if not salary_str:
        return None, None, None
    
    currency = None
    if "$" in salary_str:
        currency = "USD"
    elif "€" in salary_str or "eur" in salary_str.lower():
        currency = "EUR"
    elif "£" in salary_str or "gbp" in salary_str.lower():
        currency = "GBP"
    elif "rp" in salary_str.lower() or "idr" in salary_str.lower():
        currency = "IDR"

    # Find numbers
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d+[\d,]*", salary_str)]
    if not nums:
        return None, None, currency
    
    # Check if 'k' suffix exists to multiply by 1000
    is_k = "k" in salary_str.lower()
    if is_k:
        nums = [n * 1000 for n in nums]

    if len(nums) >= 2:
        return min(nums), max(nums), currency
    return nums[0], nums[0], currency
