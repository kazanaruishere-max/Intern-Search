"""Plugin registry — register & get scrapers by source name."""

from __future__ import annotations

from pkl_research.scraper.plugins.base import BaseScraper

_REGISTRY: dict[str, BaseScraper] = {}


def register(scraper: BaseScraper) -> None:
    _REGISTRY[scraper.source] = scraper


def get(source: str) -> BaseScraper | None:
    return _REGISTRY.get(source.lower())


def all_sources() -> list[str]:
    return sorted(_REGISTRY)


def available() -> dict[str, BaseScraper]:
    return dict(_REGISTRY)
