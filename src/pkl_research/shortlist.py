"""Pembentukan shortlist CV-match: filter Jakarta Selatan + ranking (murni)."""

from __future__ import annotations

import re

from pkl_research import config
from pkl_research.cv import fit_for_roles

JAKSEL_BBOX = {
    "lat_min": -6.34,
    "lat_max": -6.19,
    "lon_min": 106.74,
    "lon_max": 106.90,
}


def is_non_dev(name: str | None, category: str | None) -> bool:
    """True bila perusahaan jelas bukan software development
    (gym/desain/branding/marketing/kursus/percetakan), baik dari nama maupun kategori."""
    cat = (category or "").lower()
    nm = (name or "").lower()
    if any(kw in nm for kw in config.NON_DEV_NAME_KEYWORDS):
        return True
    if any(sig in cat for sig in config.DEV_CATEGORY_SIGNALS):
        return False
    return any(kw in cat for kw in config.NON_DEV_CATEGORY_KEYWORDS)


def _norm_name(name: str) -> str:
    """Normalisasi nama untuk dedupe (lowercase, buang kata umum)."""
    text = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    for word in ("pt", "pt.", "cv", "cv.", "indonesia", "jakarta", "teknologi",
                 "digital", "the", "international", "company", "group", "global",
                 "nusantara"):
        text = re.sub(rf"\b{re.escape(word)}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_jakarta_selatan(
    address: str | None,
    latitude: float | None,
    longitude: float | None,
) -> bool:
    """True bila alamat mengandung 'Jakarta Selatan' atau koordinat dalam bbox-nya."""
    if address and "jakarta selatan" in address.lower():
        return True
    return bool(
        latitude is not None
        and longitude is not None
        and JAKSEL_BBOX["lat_min"] <= latitude <= JAKSEL_BBOX["lat_max"]
        and JAKSEL_BBOX["lon_min"] <= longitude <= JAKSEL_BBOX["lon_max"]
    )


def build_shortlist(
    companies: list[object],
    analysis: dict,
    *,
    max_km: float = 8.0,
    min_fit: float = 70.0,
    min_ulasan: int = 10,
    min_rating: float = 4.5,
    ai_by_id: dict[int, bool] | None = None,
) -> list[tuple[object, float, bool]]:
    """Filter & ranking kandidat. Return [(company, fit_score, ai_focus), ...]."""
    ai_by_id = ai_by_id or {}
    candidates: list[tuple[object, float, bool]] = []
    for company in companies:
        if not getattr(company, "is_it", False):
            continue
        if is_non_dev(
            getattr(company, "name", None),
            getattr(company, "category", None),
        ):
            continue
        if not is_jakarta_selatan(
            getattr(company, "address", None),
            getattr(company, "latitude", None),
            getattr(company, "longitude", None),
        ):
            continue
        if (getattr(company, "rating", 0) or 0) < min_rating:
            continue
        if (getattr(company, "review_count", 0) or 0) < min_ulasan:
            continue
        distance = getattr(company, "distance_km", None)
        if distance is None or distance > max_km:
            continue
        fit = fit_for_roles(analysis, getattr(company, "role_fit", []))
        if fit < min_fit:
            continue
        candidates.append((company, fit, bool(ai_by_id.get(getattr(company, "id", -1), False))))

    # Dedupe by nama (keep record paling kaya: enriched > review_count > terdekat)
    best: dict[str, tuple[object, float, bool]] = {}
    for item in candidates:
        company = item[0]
        key = _norm_name(getattr(company, "name", ""))
        if not key:
            continue
        existing = best.get(key)
        if existing is None or _better_than(item, existing):
            best[key] = item
    candidates = list(best.values())

    candidates.sort(key=lambda item: rank_key(item))
    return candidates


def _better_than(
    item: tuple[object, float, bool],
    other: tuple[object, float, bool],
) -> bool:
    c1, c2 = item[0], other[0]
    e1 = 1 if getattr(c1, "enriched_at", None) else 0
    e2 = 1 if getattr(c2, "enriched_at", None) else 0
    if e1 != e2:
        return e1 > e2
    r1 = getattr(c1, "review_count", 0) or 0
    r2 = getattr(c2, "review_count", 0) or 0
    if r1 != r2:
        return r1 > r2
    d1 = getattr(c1, "distance_km", 9999) or 9999
    d2 = getattr(c2, "distance_km", 9999) or 9999
    return d1 < d2


def rank_key(item: tuple[object, float, bool]) -> tuple[float, int, float]:
    """Kunci ranking: fit + bonus AI → ulasan terbanyak → jarak terdekat."""
    company, fit, ai = item
    ai_bonus = 10.0 if ai else 0.0
    return (
        -(fit + ai_bonus),
        -(getattr(company, "review_count", 0) or 0),
        getattr(company, "distance_km", 9999.0) or 9999.0,
    )
