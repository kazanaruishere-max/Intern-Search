"""Logika filter & klasifikasi (murni, tanpa browser)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from pkl_research import config

_ADDRESS_JAKARTA_RE = re.compile(r"\bjakarta\b", re.IGNORECASE)


@dataclass
class FilterResult:
    """Hasil evaluasi filter untuk satu kandidat."""

    passes: bool
    in_jakarta: bool = False
    is_it: bool = False
    distance_km: float | None = None
    role_fit: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak great-circle antara dua koordinat dalam kilometer."""
    r = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def in_jakarta_bbox(lat: float | None, lon: float | None) -> bool:
    """Cek koordinat dalam bounding box DKI Jakarta."""
    if lat is None or lon is None:
        return False
    b = config.JAKARTA_BBOX
    return (
        b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]
    )


def address_has_jakarta(address: str | None) -> bool:
    if not address:
        return False
    return bool(_ADDRESS_JAKARTA_RE.search(address))


def classify_role(categories: list[str]) -> list[str]:
    """Klasifikasikan kategori Google Maps ke peran target (heuristik)."""
    text = " ".join(categories).lower()
    roles: list[str] = []
    for role, keywords in config.ROLE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            roles.append(role)
    return sorted(set(roles))


def is_it_role(role_fit: list[str]) -> bool:
    """Perusahaan dianggap IT jika tercakup salah satu peran fokus."""
    return bool(role_fit)


def evaluate_candidate(
    *,
    rating: float | None,
    review_count: int | None,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    categories: list[str],
    min_rating: float = config.MIN_RATING,
    min_review_count: int = config.MIN_REVIEW_COUNT,
    home: dict[str, float] | None = None,
) -> FilterResult:
    """Evaluasi semua aturan filter (PRD 5.1) untuk satu kandidat."""
    reasons: list[str] = []
    role_fit = classify_role(categories)
    it = is_it_role(role_fit)
    distance: float | None = None

    if home and latitude is not None and longitude is not None:
        distance = round(
            haversine_km(lat1=latitude, lon1=longitude, lat2=home["lat"], lon2=home["lon"]),
            2,
        )

    in_jakarta = address_has_jakarta(address) or in_jakarta_bbox(latitude, longitude)

    if rating is None or rating < min_rating:
        reasons.append(f"rating {rating} < {min_rating}")
    if review_count is None or review_count < min_review_count:
        reasons.append(f"review_count {review_count} < {min_review_count}")
    if not in_jakarta:
        reasons.append("tidak dalam Jakarta")

    passes = not reasons
    return FilterResult(
        passes=passes,
        in_jakarta=in_jakarta,
        is_it=it,
        distance_km=distance,
        role_fit=role_fit,
        reasons=reasons,
    )


def company_sort_key(company: object) -> tuple[float, float, int]:
    """Kunci sortir: rating 5.0 dulu, lalu jarak terdekat, lalu review terbanyak."""
    rating = company.rating if company.rating is not None else 0.0
    distance = company.distance_km if company.distance_km is not None else float("inf")
    count = company.review_count if company.review_count is not None else 0
    return (-rating, distance, -count)
