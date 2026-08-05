"""Parsing panel review Google Maps."""

from __future__ import annotations

import random
import re

from playwright.sync_api import Page

from pkl_research.models import Review

_RATING_ARIA_RE = re.compile(r"(\d+)\s*bintang")


def open_reviews(page: Page) -> bool:
    """Klik tombol Ulasan di halaman place. Return True bila berhasil."""
    button = page.locator('button[aria-label*="Ulasan"]').first
    if not button.count() or not button.is_visible():
        return False
    try:
        button.click(timeout=8000)
    except Exception:
        return False
    page.wait_for_timeout(random.randint(2500, 4000))
    return True


def _scrollable_container(page: Page):
    """Temukan kontainer panel review yang bisa di-scroll."""
    containers = page.locator("div.m6QErb")
    for i in range(containers.count()):
        el = containers.nth(i)
        if not el.is_visible():
            continue
        try:
            info = el.evaluate(
                "el => ({sh: el.scrollHeight, ch: el.clientHeight})"
            )
        except Exception:
            continue
        if info["sh"] > info["ch"]:
            return el
    return None


def scroll_reviews(page: Page, max_rounds: int = 40) -> None:
    """Scroll panel review sampai tidak ada kartu baru (load more)."""
    for _ in range(max_rounds):
        before = page.locator("div.jftiEf").count()
        container = _scrollable_container(page)
        if container is None:
            return
        try:
            container.evaluate("el => el.scrollTo(0, el.scrollHeight)")
        except Exception:
            return
        page.wait_for_timeout(random.randint(1500, 3000))
        after = page.locator("div.jftiEf").count()
        if after <= before:
            return


def _parse_stars(card) -> int | None:
    span = card.locator('span[role="img"][aria-label*="bintang"]').first
    if not span.count():
        return None
    m = _RATING_ARIA_RE.match(span.get_attribute("aria-label") or "")
    return int(m.group(1)) if m else None


def _first_text(card, selector: str) -> str | None:
    locator = card.locator(selector).first
    if locator.count():
        text = locator.inner_text().strip()
        return text or None
    return None


def parse_reviews(page: Page, limit: int = 20) -> list[Review]:
    """Parse kartu review yang sudah tampil (perusahaan_id diisi oleh caller)."""
    reviews: list[Review] = []
    cards = page.locator("div.jftiEf")
    for i in range(cards.count()):
        if len(reviews) >= limit:
            break
        card = cards.nth(i)
        reviews.append(
            Review(
                company_id=-1,  # di-set ulang oleh caller
                reviewer_name=_first_text(card, "div.d4r55"),
                reviewer_rating=_parse_stars(card),
                review_text=_first_text(card, "span.wiI7pd"),
                review_date=_first_text(card, "span.rsqaWe"),
            )
        )
    return reviews
