"""Probe DOM halaman detail Google Maps (dev only)."""

from __future__ import annotations

import sys

from pkl_research import config
from pkl_research.scraper.browser import BrowserSession

URL = (
    "https://www.google.com/maps/place/Noohtify+-+Software+House+Agency/"
    "data=!4m7!3m6!1s0x2e69f32c58707323:0xc60402cdebe8e989!8m2!3d-6.2342157!"
    "4d106.8485929!16s%2Fg%2F11yx7k118v!19sChIJI3NwWCzzaS4Rieno680CBMY?hl=id"
)


def main(url: str = URL) -> None:
    with BrowserSession(config.USER_DATA_DIR, headless=True, timeout_ms=30000) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(7000)

        print("URL sekarang:", page.url[:160])
        html = page.content()
        (config.OUTPUT_DIR / "probe_detail.html").write_text(html, encoding="utf-8")
        print("HTML tersimpan.")

        selectors = [
            "h1",
            "h1.DUwDvf",
            'div.F7nice span',
            'button[jsaction*="review"]',
            'button[data-item-id="address"]',
            'button[data-item-id^="phone:tel:"]',
            'a[data-item-id="authority"]',
            'button[jsaction*="category"]',
            'div.fontBodyMedium a[jsaction*="category"]',
            'img[src*="lh3.googleusercontent"]',
            'div[role="region"] img',
        ]
        for sel in selectors:
            try:
                n = page.locator(sel).count()
                print(f"{sel!r}: {n}")
            except Exception as e:
                print(f"{sel!r}: ERROR {e}")

        h1 = page.locator("h1.DUwDvf")
        if h1.count():
            print("h1.DUwDvf:", repr(h1.first.inner_text()[:60]))
        rating = page.locator('div.F7nice span').first
        if rating.count():
            print("rating text:", repr(rating.inner_text()))
        addr = page.locator('button[data-item-id="address"]').first
        if addr.count():
            print("address:", repr(addr.inner_text()[:100]))
        phone = page.locator('button[data-item-id^="phone:tel:"]').first
        if phone.count():
            print("phone:", repr(phone.inner_text()[:50]))
        site = page.locator('a[data-item-id="authority"]').first
        if site.count():
            print("website:", site.get_attribute("href"))
        imgs = page.locator('img[src*="lh3.googleusercontent"]')
        for i in range(min(imgs.count(), 3)):
            print("img:", imgs.nth(i).get_attribute("src")[:120])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else URL)
