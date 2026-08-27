"""Base class and registry for vacancy sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkl_research.models import Vacancy

_REGISTRY: dict[str, VacancySource] = {}


class VacancySource(ABC):
    """Kelas dasar untuk setiap sumber lowongan pekerjaan/magang."""

    source: str

    @abstractmethod
    def fetch(self, query: str, limit: int = 50, board_token: str | None = None) -> list[Vacancy]:
        """Ambil lowongan dari sumber eksternal berdasarkan kueri."""
        ...


def register(source: VacancySource) -> None:
    """Daftarkan sumber lowongan."""
    _REGISTRY[source.source.lower()] = source


def get_source(source_name: str) -> VacancySource | None:
    """Ambil instance sumber lowongan berdasarkan nama."""
    return _REGISTRY.get(source_name.lower())


def all_sources() -> list[str]:
    """Dapatkan semua nama sumber lowongan terdaftar."""
    return sorted(_REGISTRY.keys())


def register_all() -> None:
    """Auto-register semua built-in vacancy sources."""
    from pkl_research.scraper.vacancy_sources.remotive import RemotiveSource
    from pkl_research.scraper.vacancy_sources.remoteok import RemoteokSource
    from pkl_research.scraper.vacancy_sources.himalayas import HimalayasSource
    from pkl_research.scraper.vacancy_sources.wwr import WwrSource
    from pkl_research.scraper.vacancy_sources.greenhouse import GreenhouseSource
    from pkl_research.scraper.vacancy_sources.lever import LeverSource
    from pkl_research.scraper.vacancy_sources.ashby import AshbySource

    register(RemotiveSource())
    register(RemoteokSource())
    register(HimalayasSource())
    register(WwrSource())
    register(GreenhouseSource())
    register(LeverSource())
    register(AshbySource())
