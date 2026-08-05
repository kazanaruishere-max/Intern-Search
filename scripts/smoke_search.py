"""Smoke test search (live). Jalankan beberapa query, cetak hasil."""

from __future__ import annotations

import sys

from rich.console import Console

from pkl_research import config
from pkl_research._compat import setup_utf8_io
from pkl_research.filters import evaluate_candidate
from pkl_research.scraper.browser import BrowserSession
from pkl_research.scraper.search import collect_candidates

setup_utf8_io()
console = Console(legacy_windows=False)

QUERIES = [
    "software house jakarta selatan",
    "perusahaan AI jakarta selatan",
    "web development jakarta selatan",
    "game studio jakarta selatan",
]


def main(limit: int = 5, headless: bool = True) -> None:
    with BrowserSession(config.USER_DATA_DIR, headless=headless) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        candidates = collect_candidates(page, QUERIES, config.CENTER_JAKSEL)
    console.print(f"Total kandidat unik: {len(candidates)}")

    home = config.home_location()
    passed = []
    for c in candidates:
        res = evaluate_candidate(
            rating=c.rating,
            review_count=c.review_count,
            address=c.address,
            latitude=c.latitude,
            longitude=c.longitude,
            categories=[c.category] if c.category else [],
            home=home,
        )
        if res.passes:
            passed.append((c, res))
    console.print(f"Lolos filter: {len(passed)}")

    for c, res in passed[: int(limit)]:
        console.print(
            f"[bold]{c.name}[/bold] | rating={c.rating} | count={c.review_count}"
            f" | {c.distance_km} km | {res.role_fit}"
        )
        console.print(f"   cat={c.category} | addr={c.address}")
        console.print(f"   maps={c.maps_url}")


if __name__ == "__main__":
    main(limit=sys.argv[1] if len(sys.argv) > 1 else 5)
