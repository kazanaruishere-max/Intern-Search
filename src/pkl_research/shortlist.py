"""Pembentukan shortlist CV-match: filter Jakarta Selatan + ranking (murni)."""

from __future__ import annotations

from pkl_research.cv import fit_for_roles

JAKSEL_BBOX = {
    "lat_min": -6.34,
    "lat_max": -6.19,
    "lon_min": 106.74,
    "lon_max": 106.90,
}


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

    candidates.sort(key=lambda item: rank_key(item))
    return candidates


def rank_key(item: tuple[object, float, bool]) -> tuple[float, int, float]:
    """Kunci ranking: fit + bonus AI → ulasan terbanyak → jarak terdekat."""
    company, fit, ai = item
    ai_bonus = 10.0 if ai else 0.0
    return (
        -(fit + ai_bonus),
        -(getattr(company, "review_count", 0) or 0),
        getattr(company, "distance_km", 9999.0) or 9999.0,
    )
