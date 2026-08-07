"""Ekspor laporan: CSV, JSON, Markdown (murni)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pkl_research.models import Application, Company, Review

CSV_FIELDS = [
    "name", "category", "rating", "review_count", "address", "district",
    "latitude", "longitude", "distance_km", "in_jakarta", "role_fit",
    "is_it", "phone", "website", "maps_url", "photos", "scraped_at", "enriched_at",
]


def _status_for(company_id: int | None, applications: list[Application]) -> str:
    for app in applications:
        if app.company_id == company_id:
            return app.status
    return ""


def companies_to_csv(
    companies: list[Company],
    path: str | Path,
    applications: list[Application] | None = None,
) -> None:
    apps = applications or []
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS + ["status"])
        writer.writeheader()
        for c in companies:
            row = {field: c.to_dict().get(field) for field in CSV_FIELDS}
            row["role_fit"] = ",".join(c.role_fit)
            row["photos"] = len(c.photos)
            row["status"] = _status_for(c.id, apps)
            writer.writerow(row)


def companies_to_json(
    companies: list[Company],
    path: str | Path,
) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([c.to_dict() for c in companies], fh, ensure_ascii=False, indent=2)


def reviews_to_json(
    companies: list[Company],
    reviews_by_company: dict[int, list[Review]],
    path: str | Path,
) -> None:
    payload = [
        {
            "company": c.to_dict(),
            "reviews": [r.__dict__ for r in reviews_by_company.get(c.id or -1, [])],
        }
        for c in companies
    ]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def report_markdown(
    companies: list[Company],
    path: str | Path,
    applications: list[Application] | None = None,
) -> None:
    """Laporan Markdown berisi daftar perusahaan + status aplikasi."""
    apps = applications or []
    lines = ["# Laporan Riset PKL — Perusahaan IT Jakarta Selatan", ""]
    lines.append(f"Total perusahaan: **{len(companies)}**")
    lines.append("")
    for c in companies:
        lines.append(f"## {c.name}")
        lines.append(f"- Kategori: {c.category or '-'} | Role: {', '.join(c.role_fit) or '-'}")
        lines.append(f"- Rating: {c.rating} ({c.review_count} ulasan)")
        lines.append(f"- Alamat: {c.address or '-'}")
        if c.distance_km is not None:
            lines.append(f"- Jarak: {c.distance_km:.1f} km")
        lines.append(f"- Website: {c.website or '-'}")
        lines.append(f"- Telepon: {c.phone or '-'}")
        lines.append(f"- Status PKL: {_status_for(c.id, apps) or 'belum ada'}")
        lines.append(f"- Maps: {c.maps_url or '-'}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def drafts_markdown(
    drafts_by_company: dict[str, dict[str, str]],
    path: str | Path,
) -> None:
    """Dokumen semua draft pesan (3 varian per perusahaan) untuk direview user."""
    lines = ["# Draft Pesan Lamaran PKL", ""]
    for company_name, variants in drafts_by_company.items():
        lines.append(f"## {company_name}")
        for variant, text in variants.items():
            lines.append(f"### Varian: {variant}")
            lines.append(text)
            lines.append("")
            lines.append("---")
            lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def profiles_markdown(
    profiles_with_company: list[tuple[object, Company]],
    path: str | Path,
) -> None:
    """Dokumen profil perusahaan hasil scan website (qualified shortlist)."""
    lines = ["# Profil Perusahaan (dari Website) — Qualified Shortlist", ""]
    for profile, company in profiles_with_company:
        ai_subfields = getattr(profile, "ai_subfields", None) or []
        ai_focus = getattr(profile, "ai_focus", False)
        lines.append(f"## {company.name}")
        lines.append(f"- Website: {getattr(profile, 'website_url', None) or '-'}")
        lines.append(f"- Fokus: {getattr(profile, 'core_focus', None) or '-'}")
        if getattr(profile, "site_title", None):
            lines.append(f"- Judul situs: {profile.site_title}")
        if ai_focus:
            lines.append(f"- **AI: {' / '.join(ai_subfields)}**")
            for evidence in (getattr(profile, "ai_evidence", None) or [])[:2]:
                lines.append(f'  - Bukti: "{evidence}"')
        else:
            lines.append("- AI: tidak terdeteksi")
        career = (
            f"ya — {getattr(profile, 'career_url', '')}"
            if getattr(profile, "career_page_found", False)
            else "tidak"
        )
        lines.append(f"- Halaman karir: {career}")
        emails = getattr(profile, "emails", None) or []
        social = getattr(profile, "social", None) or []
        if emails:
            lines.append(f"- Email: {', '.join(emails)}")
        if social:
            lines.append(f"- Sosmed: {', '.join(social)}")
        about = getattr(profile, "about_text", None)
        if about:
            lines.append("- Tentang:")
            lines.append(f"  {about[:400]}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def shortlist_markdown(
    items: list[tuple[Company, float, bool]],
    profiles_by_id: dict[int, object],
    path: str | Path,
    notes_by_id: dict[int, str] | None = None,
    status_by_id: dict[int, str] | None = None,
) -> None:
    """Laporan mendalam kandidat shortlist (profil + tentang + AI + fit + jarak)."""
    notes_by_id = notes_by_id or {}
    status_by_id = status_by_id or {}
    lines = [
        "# Shortlist CV-Match — Perusahaan IT Jakarta Selatan",
        "",
        f"Total: **{len(items)}** perusahaan | filter: IT + Jakarta Selatan + "
        "jarak ≤ 6 km + fit-CV ≥ 70 + ulasan ≥ 10",
        "",
    ]
    for idx, (company, fit, ai) in enumerate(items, start=1):
        profile = profiles_by_id.get(company.id)
        lines.append(f"## {idx}. {company.name}")
        lines.append(
            f"- Fit-CV: **{fit:g}** | Rating: {company.rating} "
            f"({company.review_count} ulasan) | Jarak: {company.distance_km:.1f} km"
        )
        lines.append(
            f"- Role: {', '.join(company.role_fit) or '-'} | "
            f"Sektor: {company.sector or '-'} | Website: {company.website or '-'}"
        )
        status = status_by_id.get(company.id)
        if status:
            lines.append(f"- **Status lamaran**: {status}")
        note = notes_by_id.get(company.id)
        if note:
            lines.append(f"- **Catatan**: {note}")
        if profile and profile.linkedin_url:
            label = profile.linkedin_label or "linkedin"
            lines.append(f"- **LinkedIn**: {profile.linkedin_url} ({label})")
        if profile and profile.whatsapp:
            lines.append(f"- **WhatsApp**: {profile.whatsapp}")
        if profile and profile.ai_focus:
            lines.append(
                f"- **AI: {' / '.join(profile.ai_subfields)}**"
            )
        elif ai:
            lines.append("- AI: (tertag peran, belum terkonfirmasi website)")
        if profile:
            if profile.core_focus:
                lines.append(f"- Fokus: {profile.core_focus}")
            if profile.about_text:
                lines.append(f"- Tentang: {profile.about_text[:350]}")
            if profile.services_text:
                lines.append(f"- Layanan: {profile.services_text[:250]}")
            if profile.career_page_found:
                lines.append(f"- Halaman karir: ya — {profile.career_url}")
            if profile.emails:
                lines.append(f"- Email: {', '.join(profile.emails)}")
            if profile.social:
                lines.append(f"- Sosmed: {', '.join(profile.social)}")
            if profile.ai_focus:
                for evidence in (profile.ai_evidence or [])[:2]:
                    lines.append(f'  - Bukti AI: "{evidence}"')
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
