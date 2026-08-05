"""Probe review count di header detail (dev only)."""

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
        page.wait_for_timeout(5000)

        f7 = page.locator("div.F7nice")
        if f7.count():
            print("F7nice:", repr(f7.first.inner_text()[:200]))

        candidates = page.locator('button[jsaction*="review"] span')
        for i in range(min(candidates.count(), 8)):
            t = candidates.nth(i).inner_text()
            if t.strip():
                print("span:", repr(t[:50]))

        panel = page.locator('button[aria-label*="Ulasan"]').first
        if panel.count():
            print("ulasan btn aria:", panel.get_attribute("aria-label"))
            print("ulasan btn text:", repr(panel.inner_text()[:60]))


if __name__ == "__main__":
    main()
