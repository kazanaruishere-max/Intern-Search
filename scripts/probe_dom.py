"""Probe DOM Google Maps search (dev only). Simpan HTML + statistik selector."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pkl_research.config import OUTPUT_DIR
from pkl_research.scraper.browser import BrowserSession

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main(query: str = "software house jakarta selatan") -> None:
    from urllib.parse import quote

    url = (
        "https://www.google.com/maps/search/"
        + quote(query)
        + "/@-6.24,106.80,13z?hl=id"
    )
    print("URL:", url)
    with BrowserSession("user_data", headless=True, timeout_ms=30000) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)

        html = page.content()
        (OUTPUT_DIR / "probe_search.html").write_text(html, encoding="utf-8")
        print("HTML tersimpan:", OUTPUT_DIR / "probe_search.html")

        selectors = [
            'div[role="feed"]',
            "a.hfpxzc",
            "span.MW4etd",
            "span.UY7F9",
            "div.Nv2PK",
            "div.W4Efsd",
        ]
        for sel in selectors:
            n = page.locator(sel).count()
            print(f"{sel!r}: {n}")

        anchors = page.locator("a.hfpxzc")
        for i in range(min(anchors.count(), 5)):
            a = anchors.nth(i)
            print("---")
            print("aria-label:", (a.get_attribute("aria-label") or "")[:80])
            href = a.get_attribute("href") or ""
            print("href:", href[:180])
            m = re.search(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", href)
            if m:
                print("coords !3d!4d:", m.groups())
            m2 = re.search(r"@(-?[\d.]+),(-?[\d.]+)", href)
            if m2:
                print("coords @:", m2.groups())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "software house jakarta selatan")
