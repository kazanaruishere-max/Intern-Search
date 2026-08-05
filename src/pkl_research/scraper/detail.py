"""Parsing halaman detail perusahaan (info + foto)."""

from __future__ import annotations

import re

from playwright.sync_api import Page

from pkl_research.models import Company

_F7_RE = re.compile(r"([\d.,]+)\s*\n\s*\(\s*([\d.,]+)\s*\)")
_ICON_RE = re.compile(r"^[\ue000-\uf8ff\s]+")


def _clean_icon(text: str) -> str:
    return _ICON_RE.sub("", text or "").strip()


def _first_text(container: object, selector: str) -> str | None:
    """Ambil inner_text elemen pertama yang cocok, atau None."""
    locator = container.locator(selector).first  # type: ignore[attr-defined]
    if locator.count() and locator.is_visible():
        text = locator.inner_text().strip()
        return text or None
    return None


def parse_rating_summary(text: str | None) -> tuple[float | None, int | None]:
    """Parse rating & jumlah review dari div.F7nice (mis. '5,0\\n(25)')."""
    if not text:
        return None, None
    m = _F7_RE.search(text)
    if not m:
        return None, None
    rating = float(m.group(1).replace(",", "."))
    count = int(re.sub(r"[^\d]", "", m.group(2)) or 0)
    return rating, count


def scrape_detail(page: Page) -> dict[str, object]:
    """Ambil info detail dari halaman place yang sedang terbuka."""
    name = None
    h1 = page.locator("h1.DUwDvf").first
    if h1.count():
        name = h1.inner_text().strip()

    rating, review_count = None, None
    f7 = page.locator("div.F7nice").first
    if f7.count():
        rating, review_count = parse_rating_summary(f7.inner_text())

    address_btn = page.locator('button[data-item-id="address"]').first
    address = _clean_icon(address_btn.inner_text()) if address_btn.count() else None

    phone_btn = page.locator('button[data-item-id^="phone:tel:"]').first
    phone = _clean_icon(phone_btn.inner_text()) if phone_btn.count() else None

    website = None
    site = page.locator('a[data-item-id="authority"]').first
    if site.count():
        website = site.get_attribute("href")

    category = None
    cat = page.locator('button[jsaction*="category"]').first
    if cat.count():
        category = _clean_icon(cat.inner_text())

    photos: list[str] = []
    imgs = page.locator('img[src*="lh3.googleusercontent"]')
    for i in range(imgs.count()):
        src = imgs.nth(i).get_attribute("src")
        if src and src not in photos:
            photos.append(src)

    return {
        "name": name,
        "rating": rating,
        "review_count": review_count,
        "address": address,
        "phone": phone,
        "website": website,
        "category": category,
        "photos": photos,
        "photo_count": len(photos),
    }


def apply_detail(company: Company, detail: dict[str, object]) -> Company:
    """Salin hasil detail ke dataclass Company (immutable-style)."""
    return Company(
        **{
            **company.to_dict(),
            "name": detail["name"] or company.name,
            "rating": detail["rating"] if detail["rating"] is not None else company.rating,
            "review_count": (
                detail["review_count"]
                if detail["review_count"] is not None
                else company.review_count
            ),
            "address": detail["address"] or company.address,
            "phone": detail["phone"] or company.phone,
            "website": detail["website"] or company.website,
            "category": detail["category"] or company.category,
            "photos": detail["photos"] or company.photos,
            "photo_count": detail["photo_count"] or company.photo_count,
        }
    )
