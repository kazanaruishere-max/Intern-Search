"""BaseScraper ABC — contract for all source plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pkl_research.models import Company


class BaseScraper(ABC):
    source: str

    @abstractmethod
    def collect(self, page, query: str, region: dict) -> list[Company]:
        """Collect companies for one query in one region. Return Company list."""
        ...
