"""Plugin registry — register & get scrapers by source name.

Usage:
    from pkl_research.scraper.plugins import register_all, get_scraper
    register_all()
    scraper = get_scraper("glints")
    companies = scraper.collect(page, query="software intern", region={...})
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkl_research.scraper.plugins.base import BaseScraper

_REGISTRY: dict[str, "BaseScraper"] = {}


def register(scraper: "BaseScraper") -> None:
    """Daftarkan scraper ke registry."""
    _REGISTRY[scraper.source.lower()] = scraper


def get(source: str) -> "BaseScraper | None":
    """Ambil scraper berdasarkan nama sumber."""
    return _REGISTRY.get(source.lower())


def all_sources() -> list[str]:
    return sorted(_REGISTRY)


def available() -> dict[str, "BaseScraper"]:
    return dict(_REGISTRY)


def register_all() -> None:
    """Auto-register semua built-in plugins."""
    from pkl_research.scraper.plugins.glints import GlintsScraper
    from pkl_research.scraper.plugins.indeed import IndeedScraper
    from pkl_research.scraper.plugins.jobstreet import JobstreetScraper
    from pkl_research.scraper.plugins.linkedin import LinkedinScraper
    from pkl_research.scraper.plugins.maps import MapsScraper

    for scraper_cls in (MapsScraper, GlintsScraper, LinkedinScraper,
                        JobstreetScraper, IndeedScraper):
        register(scraper_cls())
