"""Parsing hasil pencarian Google Maps (kandidat perusahaan)."""

from __future__ import annotations

import random
import re
from urllib.parse import quote, unquote

from playwright.sync_api import Page

from pkl_research import config
from pkl_research.models import Company

_RATING_COUNT_RE = re.compile(r"^([0-9]+[.,][0-9])\s*\(\s*([0-9.,\s]+)\s*\)$")
_RATING_ONLY_RE = re.compile(r"^([0-9]+[.,][0-9])$")
_COORD_3D_RE = re.compile(r"!3d(-?[0-9.]+)!4d(-?[0-9.]+)")
_COORD_AT_RE = re.compile(r"@(-?[0-9.]+),(-?[0-9.]+)")
_GID_RE = re.compile(r"16s/g/([^!]+)")
_CID_RE = re.compile(r"1s0x[0-9a-f]+:0x([0-9a-f]+)")
_BULLET_RE = re.compile(r"[•·|]")
_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_SKIP_LINE_RE = re.compile(
    r"^(buka|tutup|segera|situs|rute|tewaktu|jam)", re.IGNORECASE
)


def _clean(text: str) -> str:
    """Hilangkan glyph icon (private-use area) dari teks kartu."""
    return _PUA_RE.sub("", text).strip()


def search_url(query: str, center: dict[str, float]) -> str:
    return (
        "https://www.google.com/maps/search/"
        f"{quote(query)}/@{center['lat']},{center['lng']},{center['zoom']}z?hl=id"
    )


def _parse_count(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _split_cat_addr(line: str) -> dict[str, str | None]:
    line = _clean(line)
    m = _BULLET_RE.search(line)
    if m:
        return {
            "category": line[: m.start()].strip() or None,
            "address": line[m.end() :].lstrip(" \u2022\u00b7\t") or None,
        }
    return {"category": line.strip() or None, "address": None}


def _parse_card_text(text: str) -> dict[str, object]:
    lines = [_clean(ln) for ln in text.splitlines() if _clean(ln)]
    result: dict[str, object] = {"rating": None, "review_count": None,
                                 "category": None, "address": None}

    for i, line in enumerate(lines):
        m = _RATING_COUNT_RE.match(line)
        if m:
            result["rating"] = float(m.group(1).replace(",", "."))
            result["review_count"] = _parse_count(m.group(2))
            rest = line[len(m.group(0)) :].strip()
            if rest:
                result.update(_split_cat_addr(rest))
            else:
                for j in range(i + 1, len(lines)):
                    cand = lines[j]
                    if _SKIP_LINE_RE.match(cand):
                        continue
                    result.update(_split_cat_addr(cand))
                    break
            return result
        if _RATING_ONLY_RE.match(line):
            result["rating"] = float(line.replace(",", "."))

    if "Tidak ada ulasan" in text or "Belum ada ulasan" in text:
        result["review_count"] = 0
    return result


def parse_results(page: Page) -> list[Company]:
    """Parse semua kartu hasil yang sedang tampil."""
    companies: list[Company] = []
    anchors = page.locator("a.hfpxzc")
    for i in range(anchors.count()):
        anchor = anchors.nth(i)
        name = (anchor.get_attribute("aria-label") or "").strip()
        href = anchor.get_attribute("href") or ""
        if not name:
            continue
        decoded = unquote(href)

        lat = lon = None
        m = _COORD_3D_RE.search(decoded) or _COORD_AT_RE.search(decoded)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))

        gid_m = _GID_RE.search(decoded)
        gid = gid_m.group(1).strip("/") if gid_m else None
        cid_m = _CID_RE.search(decoded)
        cid = "0x" + cid_m.group(1) if cid_m else None

        container = anchor.locator(
            "xpath=ancestor::div[contains(@class,'Nv2PK')][1]"
        )
        text = container.first.inner_text() if container.count() else ""
        parsed = _parse_card_text(text)

        place_id = gid or f"{name.lower()}|{lat or ''},{lon or ''}"
        companies.append(
            Company(
                place_id=place_id,
                name=name,
                category=parsed["category"],
                rating=parsed["rating"],
                review_count=parsed["review_count"],
                address=parsed["address"],
                latitude=lat,
                longitude=lon,
                cid=cid,
                maps_url=href.split("@")[0],
            )
        )
    return companies


def scroll_feed(page: Page, max_rounds: int = 6) -> None:
    """Scroll panel hasil sampai tidak ada item baru."""
    feed = page.locator('div[role="feed"]')
    if not feed.count():
        return
    el = feed.first
    for _ in range(max_rounds):
        before = page.locator("a.hfpxzc").count()
        el.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
        page.wait_for_timeout(random.randint(1200, 2500))
        after = page.locator("a.hfpxzc").count()
        if after <= before:
            return


def collect_candidates(
    page: Page,
    queries: list[str],
    center: dict[str, float],
) -> list[Company]:
    """Jalankan semua query, gabungkan hasil, dedupe by place_id."""
    seen: dict[str, Company] = {}
    for query in queries:
        page.goto(search_url(query, center), wait_until="domcontentloaded")
        try:
            page.wait_for_selector("a.hfpxzc", timeout=15_000)
        except Exception:
            continue
        page.wait_for_timeout(random.randint(1500, 3000))
        scroll_feed(page)
        for company in parse_results(page):
            seen[company.place_id] = company
    return list(seen.values())
