"""Scraping website perusahaan: profil, fokus, tentang, karir, kontak."""

from __future__ import annotations

import random
import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page

from pkl_research.ai_detect import detect_ai

SKIP_HOSTS = [
    "instagram.com", "wa.me", "whatsapp.com", "facebook.com", "tiktok.com",
    "youtube.com", "twitter.com", "x.com", "linkedin.com", "shopee",
    "shope.ee", "maps.google", "google.com/maps",
]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_WS_RE = re.compile(r"[ \t\r\f\v]+")

ABOUT_PATHS = re.compile(
    r"/(?:tentang|tentang-kami|tentang-perusahaan|tentang-perusahaan-kami|"
    r"about|about-us|about-company|profil|profile|company|who-we-are|mengenal|"
    r"sejarah|our-story)(?:[/.\-_]|$)",
    re.IGNORECASE,
)
CAREER_PATHS = re.compile(
    r"/(?:karir|karier|career|careers|career-page|lowongan|lowongan-kerja|"
    r"jobs|job|join-us|join|recruitment|rekrutmen|hire-us)(?:[/.\-_]|$)",
    re.IGNORECASE,
)
SERVICES_PATHS = re.compile(
    r"/(?:layanan|layanan-kami|services|service|solusi|solutions|produk|"
    r"products|portfolio|fitur|features|what-we-do|keahlian)(?:[/.\-_]|$)",
    re.IGNORECASE,
)
CONTACT_PATHS = re.compile(
    r"/(?:contact|contact-us|kontak|kontak-kami|hubungi|hubungi-kami|"
    r"hubungi-kita|get-in-touch|reach-us)(?:[/.\-_]|$)",
    re.IGNORECASE,
)

SOCIAL_HOSTS = [
    "linkedin.com", "instagram.com", "facebook.com", "tiktok.com",
    "youtube.com", "twitter.com", "x.com",
]


def is_real_website(url: str | None) -> bool:
    """True bila URL mengarah ke website perusahaan (bukan sosmed/WA/shop)."""
    if not url:
        return False
    url = url.strip()
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host or "." not in host:
        return False
    for bad in SKIP_HOSTS:
        if bad in host or bad in url.lower():
            return False
    return True


def _clean_text(text: str, limit: int = 5000) -> str:
    text = _PUA_RE.sub(" ", text or "")
    text = _WS_RE.sub(" ", text)
    return text.strip()[:limit]


def _visible_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text() or ""
    except Exception:
        return ""


def _collect_all_links(page: Page, base_url: str) -> set[str]:
    """Semua anchor absolut (termasuk link eksternal/sosmed)."""
    links: set[str] = set()
    anchors = page.locator("a[href]")
    for i in range(min(anchors.count(), 300)):
        try:
            href = anchors.nth(i).get_attribute("href")
        except Exception:
            continue
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).hostname:
            links.add(absolute)
    return links


def _collect_links(page: Page, base_url: str) -> set[str]:
    """Hanya link sesama host (untuk deteksi halaman internal)."""
    base_host = (urlparse(base_url).hostname or "").lower()
    return {
        link
        for link in _collect_all_links(page, base_url)
        if (urlparse(link).hostname or "").lower() == base_host
    }


def _pick_link(links: set[str], pattern: re.Pattern[str]) -> str | None:
    for link in sorted(links):
        if pattern.search(urlparse(link).path):
            return link
    return None


def _find_emails(texts: list[str]) -> list[str]:
    emails: list[str] = []
    for text in texts:
        for email in _EMAIL_RE.findall(text or ""):
            if email.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                continue
            if email not in emails:
                emails.append(email)
    return emails[:6]


def _find_social(links: set[str]) -> list[str]:
    social: list[str] = []
    for link in sorted(links):
        host = (urlparse(link).hostname or "").lower()
        if any(bad in host for bad in SOCIAL_HOSTS) and link not in social:
            social.append(link)
    return social[:8]


def linkedin_label(url: str) -> str:
    """Klasifikasi jenis LinkedIn dari path URL."""
    path = (urlparse(url).path or "").lower()
    if "/company/" in path or "/organizations/" in path:
        return "company"
    if "/school/" in path:
        return "school"
    if "/in/" in path:
        return "profil pribadi"
    if "/company" == path.rstrip("/"):
        return "company"
    return "linkedin"


def _extract_linkedin(page: Page, base_url: str) -> tuple[str | None, str | None]:
    """Cari URL LinkedIn dari anchor + JSON-LD sameAs + og:link."""
    candidates: set[str] = set()
    good_path = re.compile(r"/(company|in|school|organizations)(/|$)", re.IGNORECASE)

    def _accept(url: str) -> bool:
        return bool(good_path.search(urlparse(url).path or ""))

    for link in _collect_all_links(page, base_url):
        host = (urlparse(link).hostname or "").lower()
        if "linkedin.com" in host and _accept(link):
            candidates.add(link.split("?")[0].rstrip("/"))

    scripts = page.locator("script[type='application/ld+json']")
    for i in range(scripts.count()):
        try:
            raw = (scripts.nth(i).inner_text() or "").replace("\\/", "/")
        except Exception:
            continue
        for url in re.findall(r"https?://[^\"\s\\]*linkedin\.com[^\"\s\\]*", raw):
            if _accept(url):
                candidates.add(url.split("?")[0].rstrip("/"))

    og = page.locator('meta[property="og:link"]').first
    if og.count():
        content = og.get_attribute("content")
        if content and "linkedin.com" in content and _accept(content):
            candidates.add(content.split("?")[0].rstrip("/"))

    if not candidates:
        return None, None
    best = sorted(candidates)[0]
    return best, linkedin_label(best)


def _headings(page: Page) -> list[str]:
    result: list[str] = []
    for tag in ("h1", "h2"):
        for el in page.locator(tag).all():
            try:
                text = (el.inner_text() or "").strip()
            except Exception:
                continue
            if text and len(text) < 120:
                result.append(text)
            if len(result) >= 6:
                return result
    return result


def scrape_website(page: Page, url: str, max_pages: int = 3) -> dict[str, object]:
    """Kunjungi website & ambil profil perusahaan. Return dict siap disimpan."""
    result: dict[str, object] = {
        "website_url": url,
        "site_title": None,
        "meta_description": None,
        "core_focus": None,
        "about_text": None,
        "services_text": None,
        "career_page_found": False,
        "career_url": None,
        "career_snippet": None,
        "emails": [],
        "social": [],
        "linkedin": None,
        "linkedin_label": None,
        "pages": [],
    }

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        page.wait_for_timeout(random.randint(2500, 4000))
    except Exception:
        result["fetch_status"] = "failed"
        return result

    result["site_title"] = (page.title() or "").strip() or None
    meta = page.locator('meta[name=description]').first
    if meta.count():
        content = meta.get_attribute("content")
        if content:
            result["meta_description"] = content.strip()[:300]

    home_text = _clean_text(_visible_text(page))
    result["pages"] = [home_text]
    headings = _headings(page)
    if result["meta_description"]:
        result["core_focus"] = result["meta_description"][:300]
    elif headings:
        result["core_focus"] = " | ".join(headings[:4])[:300]
    else:
        result["core_focus"] = (result["site_title"] or "")[:200] or None

    all_links = _collect_all_links(page, url)
    links = _collect_links(page, url)
    result["emails"] = _find_emails(result["pages"] + [result["meta_description"] or ""])
    result["social"] = _find_social(all_links)
    linkedin_url, linkedin_label_value = _extract_linkedin(page, url)
    result["linkedin"] = linkedin_url
    result["linkedin_label"] = linkedin_label_value

    about = _pick_link(links, ABOUT_PATHS)
    career = _pick_link(links, CAREER_PATHS)
    services = _pick_link(links, SERVICES_PATHS)
    contact = _pick_link(links, CONTACT_PATHS)
    if career:
        result["career_page_found"] = True
        result["career_url"] = career

    targets: list[tuple[str, str]] = []
    for kind, link in (("about", about), ("contact", contact),
                       ("career", career), ("services", services)):
        if link and len(targets) < max(0, max_pages - 1):
            targets.append((kind, link))

    for kind, link in targets:
        try:
            page.goto(link, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(random.randint(2000, 3500))
        except Exception:
            continue
        text = _clean_text(_visible_text(page))
        result["pages"].append(text)  # type: ignore[union-attr]
        if kind == "about":
            result["about_text"] = text[:3000]
        elif kind == "services":
            result["services_text"] = text[:3000]
        elif kind == "career":
            result["career_snippet"] = text[:1500]

    result["emails"] = _find_emails(result["pages"])  # type: ignore[arg-type]
    result["fetch_status"] = "ok"
    return result
