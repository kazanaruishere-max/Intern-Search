"""Probe review panel Google Maps (dev only)."""

from __future__ import annotations

from pkl_research import config
from pkl_research._compat import setup_utf8_io
from pkl_research.scraper.browser import BrowserSession

setup_utf8_io()

URL = (
    "https://www.google.com/maps/place/Noohtify+-+Software+House+Agency/data=!4m7!"
    "3m6!1s0x2e69f32c58707323:0xc60402cdebe8e989!8m2!3d-6.2342157!4d106.8485929!"
    "16s%2Fg%2F11yx7k118v!19sChIJI3NwWCzzaS4Rieno680CBMY?hl=id"
)


def main() -> None:
    with BrowserSession(config.USER_DATA_DIR, headless=True, timeout_ms=30000) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)

        cat = page.locator('button[jsaction*="category"]').first
        if cat.count():
            print("category:", repr(cat.inner_text()[:80]))
            print("category aria:", cat.get_attribute("aria-label"))

        for sel in (
            'button[aria-label*="ulasan"]',
            'button[aria-label*="Ulasan"]',
            'button[aria-label*="reviews"]',
        ):
            n = page.locator(sel).count()
            print(sel, "->", n)
            if n:
                el = page.locator(sel).first
                print("   text:", repr(el.inner_text()[:60]))
                print("   aria:", el.get_attribute("aria-label"))

        # Klik tombol ulasan (cek beragam selector)
        target = None
        for sel in (
            'button[aria-label*="ulasan"]',
            'button[aria-label*="Ulasan"]',
            'button[aria-label*="reviews"]',
            'button[jsaction*="review"][aria-label]',
        ):
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                target = el
                break
        if target:
            print("KLIK review button")
            target.click()
            page.wait_for_timeout(4000)
            for sel in (
                "div.jftiEf",
                'div[role="main"] div.jftiEf',
                "span.w8nwRe",
                "div.d4r55",
                "span.rsqaWe",
                'span[aria-label*="bintang"]',
            ):
                n = page.locator(sel).count()
                print(sel, "->", n)
            first = page.locator("div.jftiEf").first
            if first.count():
                txt = first.inner_text()
                print("--- review pertama ---")
                print(txt[:300])


if __name__ == "__main__":
    main()
