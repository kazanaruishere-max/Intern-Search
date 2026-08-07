"""Model domain: dataclass yang dipetakan ke tabel SQLite."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field


def _loads(value: str | None) -> object:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


@dataclass
class Company:
    """Satu perusahaan hasil scrape Google Maps."""

    place_id: str
    name: str
    category: str | None = None
    categories: list[str] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    rating_breakdown: dict[int, int] = field(default_factory=dict)
    address: str | None = None
    district: str | None = None
    city: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    in_jakarta: bool = False
    distance_km: float | None = None
    role_fit: list[str] = field(default_factory=list)
    is_it: bool = False
    sector: str = "unknown"
    fit_score: float | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    plus_code: str | None = None
    maps_url: str | None = None
    cid: str | None = None
    open_hours: dict | None = None
    description: str | None = None
    price_range: str | None = None
    photos: list[str] = field(default_factory=list)
    photo_count: int = 0
    scraped_at: str | None = None
    enriched_at: str | None = None
    id: int | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Company":
        data = dict(row)
        return cls(
            id=data.pop("id"),
            place_id=data.pop("place_id"),
            name=data.pop("name"),
            category=data.pop("category"),
            categories=_loads(data.pop("categories")) or [],
            rating=data.pop("rating"),
            review_count=data.pop("review_count"),
            rating_breakdown=_loads(data.pop("rating_breakdown")) or {},
            address=data.pop("address"),
            district=data.pop("district"),
            city=data.pop("city"),
            postal_code=data.pop("postal_code"),
            latitude=data.pop("latitude"),
            longitude=data.pop("longitude"),
            in_jakarta=bool(data.pop("in_jakarta")),
            distance_km=data.pop("distance_km"),
            role_fit=_loads(data.pop("role_fit")) or [],
            is_it=bool(data.pop("is_it")),
            sector=data.pop("sector") or "unknown",
            fit_score=data.pop("fit_score"),
            phone=data.pop("phone"),
            website=data.pop("website"),
            email=data.pop("email"),
            plus_code=data.pop("plus_code"),
            maps_url=data.pop("maps_url"),
            cid=data.pop("cid"),
            open_hours=_loads(data.pop("open_hours")) or None,
            description=data.pop("description"),
            price_range=data.pop("price_range"),
            photos=_loads(data.pop("photos")) or [],
            photo_count=data.pop("photo_count") or 0,
            scraped_at=data.pop("scraped_at"),
            enriched_at=data.pop("enriched_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "place_id": self.place_id,
            "name": self.name,
            "category": self.category,
            "categories": self.categories,
            "rating": self.rating,
            "review_count": self.review_count,
            "rating_breakdown": self.rating_breakdown,
            "address": self.address,
            "district": self.district,
            "city": self.city,
            "postal_code": self.postal_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "in_jakarta": self.in_jakarta,
            "distance_km": self.distance_km,
            "role_fit": self.role_fit,
            "is_it": self.is_it,
            "sector": self.sector,
            "fit_score": self.fit_score,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "plus_code": self.plus_code,
            "maps_url": self.maps_url,
            "cid": self.cid,
            "open_hours": self.open_hours,
            "description": self.description,
            "price_range": self.price_range,
            "photos": self.photos,
            "photo_count": self.photo_count,
            "scraped_at": self.scraped_at,
            "enriched_at": self.enriched_at,
        }


@dataclass
class Review:
    """Satu ulasan pelanggan."""

    company_id: int
    reviewer_name: str | None = None
    reviewer_rating: float | None = None
    review_text: str | None = None
    review_date: str | None = None
    helpful_count: int = 0
    language: str | None = None
    translated_text: str | None = None
    id: int | None = None


@dataclass
class Application:
    """Tracker lamaran PKL (1 per perusahaan)."""

    company_id: int
    status: str = "shortlisted"
    applied_at: str | None = None
    sent_via: str | None = None
    contact_person: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    draft_message: str | None = None
    notes: str | None = None
    result_notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: int | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Application":
        data = dict(row)
        return cls(**data)


@dataclass
class CompanyProfile:
    """Profil perusahaan hasil scan website (fokus, tentang, karir, AI)."""

    company_id: int
    website_url: str | None = None
    site_title: str | None = None
    meta_description: str | None = None
    core_focus: str | None = None
    about_text: str | None = None
    services_text: str | None = None
    career_page_found: bool = False
    career_url: str | None = None
    career_snippet: str | None = None
    ai_focus: bool = False
    ai_subfields: list[str] = field(default_factory=list)
    ai_keywords: list[str] = field(default_factory=list)
    ai_evidence: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    social: list[str] = field(default_factory=list)
    linkedin_url: str | None = None
    linkedin_label: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    fetch_status: str = "pending"
    fetched_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: int | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "CompanyProfile":
        data = dict(row)
        data["career_page_found"] = bool(data.pop("career_page_found"))
        data["ai_focus"] = bool(data.pop("ai_focus"))
        for key in ("ai_subfields", "ai_keywords", "ai_evidence", "emails", "social", "tech_stack", "keywords"):
            data[key] = _loads(data.pop(key)) or []
        return cls(**data)
