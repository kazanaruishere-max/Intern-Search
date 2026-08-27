"""Vacancy sources package."""

from pkl_research.scraper.vacancy_sources.base import (
    all_sources,
    get_source,
    register,
    register_all,
)

__all__ = ["all_sources", "get_source", "register", "register_all"]
