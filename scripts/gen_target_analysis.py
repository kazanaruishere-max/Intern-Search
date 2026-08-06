"""Generate output/analisa_5target.md: profil + kecocokan CV untuk 5 target PKL."""

from __future__ import annotations

import sys

from pkl_research import config
from pkl_research._compat import setup_utf8_io
from pkl_research.cv import fit_for_roles, load_analysis
from pkl_research.db.connection import connect
from pkl_research.db.repositories import (
    CompanyProfileRepository,
    CompanyRepository,
    ReviewRepository,
)
from pkl_research.db.schema import apply_migrations
from pkl_research.shortlist import build_shortlist
from pkl_research.target_analysis import (
    build_target_section,
    prioritize,
    responsive_reviews,
)

TARGET_NAMES = [
    "Zahir Internasional",
    "Nectar - Jasa Pembuatan",
    "Noohtify",
    "IlmuKomputer",
    "Majapahit",
]


def main() -> None:
    setup_utf8_io()
    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    repo = CompanyRepository(conn)
    review_repo = ReviewRepository(conn)
    prof_by_id = {p.company_id: p for p, _ in CompanyProfileRepository(conn).list_with_company()}
    analysis = load_analysis(config.OUTPUT_DIR / "cv_analysis.json")
    if not analysis:
        print("cv_analysis.json belum ada. Jalankan: pkl-research cv analyze <path>")
        return

    all_companies = repo.find()
    ai_by_id = {p.company_id: p.ai_focus for p, _ in CompanyProfileRepository(conn).list_with_company()}
    shortlist = build_shortlist(all_companies, analysis, ai_by_id=ai_by_id)
    shortlist_ids = {c.id for c, _, _ in shortlist}

    targets = []
    for name in TARGET_NAMES:
        cands = [c for c in all_companies if name.lower() in c.name.lower() and c.is_it]
        # pilih entri yang punya profil, fallback entri pertama
        cands = sorted(cands, key=lambda c: (c.id in prof_by_id, c.id in shortlist_ids), reverse=True)
        if cands:
            targets.append(cands[0])

    items = []
    lines = [
        "# Analisa 5 Target PKL — Kecocokan dengan CV Azka Syahirull",
        "",
        f"Filter: IT + Jakarta Selatan + jarak ≤ 6 km + fit-CV ≥ 70 + ulasan ≥ 10.",
        "",
        "## Ringkasan 5 Target",
        "",
        "| # | Perusahaan | Fit-CV | AI | Rating (ulasan) | Jarak | Karir | Email |",
        "|---|-----------|--------|----|-----------------|-------|-------|-------|",
    ]

    sections: list[str] = []
    for idx, company in enumerate(targets, start=1):
        profile = prof_by_id.get(company.id)
        reviews = review_repo.list_by_company(company.id) if company.id else []
        fit = fit_for_roles(analysis, company.role_fit)
        ai = bool(profile and profile.ai_focus)
        n_resp = len(responsive_reviews(reviews, limit=99))
        career = bool(profile and profile.career_page_found)
        emails = (profile.emails or []) if profile else []
        items.append({
            "fit": fit, "ai": ai, "career": career, "n_resp": n_resp,
            "distance": company.distance_km or 9.0, "name": company.name,
        })
        lines.append(
            f"| {idx} | {company.name} | {fit:g} | {'Ya' if ai else '-'} | "
            f"{company.rating} ({company.review_count}) | {company.distance_km:.1f} km | "
            f"{'Ya' if career else '-'} | {', '.join(emails[:2]) or '-'} |"
        )
        sections.append(
            "\n".join(build_target_section(idx, company, profile, fit, ai, reviews, analysis))
        )

    lines.append("")
    lines.append("## Detail Per Target")
    lines.append("")
    for section in sections:
        lines.append(section)

    lines.append("## Rekomendasi Urutan Prioritas Lamaran")
    lines.append("")
    for entry in prioritize(items):
        name = entry["item"]["name"]
        lines.append(
            f"{entry['rank']}. **{name}** (skor prioritas {entry['score']}) — {entry['reason']}"
        )
    lines.append("")

    out = config.OUTPUT_DIR / "analisa_5target.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Tersimpan: {out} ({len(targets)} target)")


if __name__ == "__main__":
    main()
