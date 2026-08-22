"""Catatan otomatis per perusahaan untuk shortlist (murni, tanpa I/O)."""

from __future__ import annotations

import re

PKL_KEYWORDS = [
    "pkl", "magang", "internship", "intern", "kunjungan industri",
    "kunjungan siswa", "praktik kerja", "praktik kerja lapangan",
    "siswa", "smk", "student", "students",
]
RESPONSIVE_KEYWORDS = [
    "responsif", "respon", "balas", "fast response", "dibalas",
    "respon cepat", "cepat balas", "merespon", "dibales",
]
GEDUNG_KEYWORDS = [
    "tower", "gedung", "menara", "plaza", "office", "wisma", "scbd",
    "sudirman", "tb simatupang", "rasuna", "gate", "building",
    "centre", "center", "mega kuningan", "lt.", "lantai",
]

_WS_RE = re.compile(r"\s+")


def review_evidence(reviews: list[object], keywords: list[str]) -> list[object]:
    """Review yang teksnya mengandung salah satu keyword."""
    return [
        r for r in reviews
        if (getattr(r, "review_text", None) or "")
        and any(k in getattr(r, "review_text", "").lower() for k in keywords)
    ]


def auto_notes(
    company: object,
    profile: object | None,
    reviews: list[object],
) -> list[str]:
    """Catatan ringkas otomatis dari data perusahaan, profil website, dan review."""
    notes: list[str] = []

    if company.rating is not None:
        notes.append(f"Rating {company.rating:g} dari {company.review_count or 0} ulasan")

    addr = (company.address or "").lower()
    if any(k in addr for k in GEDUNG_KEYWORDS):
        notes.append("Kantor di gedung/perkantoran")

    pkl = review_evidence(reviews, PKL_KEYWORDS)
    if pkl:
        quote = _one_line(getattr(pkl[0], "review_text", "") or "", 90)
        notes.append(f"Disebut menerima kunjungan industri/PKL di review ({len(pkl)}x) — \"{quote}\"")

    responsive = review_evidence(reviews, RESPONSIVE_KEYWORDS)
    if responsive:
        notes.append(f"Review menyebut tim responsif ({len(responsive)}x)")

    if profile and profile.ai_focus:
        notes.append(f"AI terdeteksi: {' / '.join(profile.ai_subfields)}")

    if profile and profile.career_page_found:
        notes.append("Punya halaman karir (terbuka peluang PKL)")

    if company.distance_km is not None:
        distance = company.distance_km
        if distance <= 2:
            notes.append(f"Sangat dekat rumah ({distance:.1f} km)")
        else:
            notes.append(f"Jarak {distance:.1f} km dari rumah")

    if profile and profile.emails:
        notes.append(f"Email kontak: {', '.join(profile.emails[:2])}")

    if profile and profile.linkedin_url:
        label = profile.linkedin_label or "linkedin"
        notes.append(f"LinkedIn: {profile.linkedin_url} ({label})")

    if profile and profile.whatsapp:
        notes.append(f"WhatsApp: {profile.whatsapp}")

    if company.distance_km is not None and company.distance_km > 10.0:
        notes.append(f"WFA (jarak {company.distance_km:.1f} km, >10 km)")

    if profile and profile.core_focus:
        notes.append(f"Fokus: {_one_line(profile.core_focus, 90)}")

    return notes


def combine_note(
    company: object,
    profile: object | None,
    reviews: list[object],
    manual_note: str | None = None,
) -> str:
    """Gabungkan catatan otomatis + catatan manual menjadi satu string."""
    parts = auto_notes(company, profile, reviews)
    if manual_note and manual_note.strip():
        parts.append(f"Catatan kamu: {manual_note.strip()}")
    return " · ".join(parts)


def _one_line(text: str, limit: int) -> str:
    return _WS_RE.sub(" ", text).strip()[:limit]
