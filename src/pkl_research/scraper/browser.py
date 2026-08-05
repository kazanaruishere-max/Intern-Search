"""Browser automation (Playwright) + lapisan anti-blow."""

from __future__ import annotations

import random
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
]

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--disable-infobars",
    "--disable-popup-blocking",
]


def human_delay(page: Page, delay_range: tuple[float, float] = (2.0, 6.0)) -> None:
    """Jeda acak menyerupai manusia."""
    page.wait_for_timeout(random.randint(int(delay_range[0] * 1000), int(delay_range[1] * 1000)))


def dismiss_consent(page: Page) -> None:
    """Tutup dialog cookie/consent Google bila muncul."""
    for selector in (
        'button[aria-label="Tolak semua"]',
        'button[aria-label="Reject all"]',
        'button[jsaction*="consent"]',
    ):
        try:
            button = page.locator(selector).first
            if button.count() and button.is_visible():
                button.click(timeout=3000)
                return
        except Exception:
            continue


class BrowserSession:
    """Context manager untuk session browser persistent (anti-blow)."""

    def __init__(
        self,
        user_data_dir: str | Path,
        headless: bool = False,
        timeout_ms: int = 20_000,
    ) -> None:
        self.user_data_dir = str(user_data_dir)
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._pw = None
        self.context: BrowserContext | None = None

    def __enter__(self) -> BrowserContext:
        self._pw = sync_playwright().start()
        self.context = self._pw.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1440, "height": 900},
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            args=STEALTH_ARGS,
        )
        self.context.set_default_timeout(self.timeout_ms)
        return self.context

    def __exit__(self, *exc: object) -> None:
        if self.context:
            self.context.close()
        if self._pw:
            self._pw.stop()
