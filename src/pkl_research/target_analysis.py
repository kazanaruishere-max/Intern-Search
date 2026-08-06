"""Analisa target PKL: profil perusahaan + kecocokan CV (murni, tanpa I/O)."""

from __future__ import annotations

import re

RESPONSIVE_KW = [
    "responsif", "respon", "balas", "fast response", "dibalas",
    "respon cepat", "cepat balas", "merespon", "dibales",
]

_WS_RE = re.compile(r"\s+")


def responsive_reviews(reviews: list[object], limit: int = 2) -> list[str]:
    """Kutipan review yang menyebut responsivitas/cepat balas."""
    quotes: list[str] = []
    for review in reviews:
        text = (getattr(review, "review_text", None) or "").strip()
        if not text:
            continue
        if any(kw in text.lower() for kw in RESPONSIVE_KW):
            clean = _WS_RE.sub(" ", text)
            quotes.append(clean if len(clean) <= 160 else clean[:157] + "...")
        if len(quotes) >= limit:
            break
    return quotes


def cv_match_points(
    company: object,
    profile: object | None,
    cv_analysis: dict | None,
) -> list[str]:
    """Mapping proyek & skill CV ke kebutuhan perusahaan (berbasis data)."""
    points: list[str] = []
    subfields = profile.ai_subfields if profile else []
    roles = company.role_fit or []
    text = " ".join(
        filter(
            None,
            [
                company.name or "",
                company.category or "",
                profile.core_focus if profile else "",
                (profile.about_text or "")[:500] if profile else "",
            ],
        )
    ).lower()
    has_ai = bool(profile and profile.ai_focus)

    if has_ai and any(
        s in subfields
        for s in ("Chatbot / Virtual Assistant", "LLM / Generative AI", "Artificial Intelligence")
    ):
        points.append(
            "SafeWallet AI — pengalaman membangun deteksi berbasis LLM (Gemini + Groq API) "
            f"cocok dengan arah AI perusahaan ({' / '.join(subfields)})."
        )
    elif has_ai and any(
        s in subfields for s in ("Machine Learning", "Deep Learning", "Data Science")
    ):
        points.append(
            "Xondra AI — pengalaman multi-agent LLM + ChromaDB + Rust cocok dengan fokus "
            f"ML/data perusahaan ({' / '.join(subfields)})."
        )
    elif has_ai:
        points.append(
            f"Proyek AI (SafeWallet & Xondra) relevan dengan fokus AI perusahaan "
            f"({' / '.join(subfields)})."
        )

    if "fullstack" in roles:
        points.append(
            "SafeWallet AI — dashboard Next.js (frontend + backend) membuktikan "
            "kemampuan fullstack yang perusahaan butuhkan."
        )
    if "software" in roles:
        points.append(
            "Xondra AI & SEITH — Python/Rust/Go untuk sistem & komputasi; "
            "fondasi software engineering yang solid."
        )
    if any(
        kw in text
        for kw in (
            "akuntansi", "accounting", "erp", "finansial", "financial",
            "wealth", "investasi", "investor", "keuangan", "trading",
            "pembayaran", "payment",
        )
    ):
        points.append(
            "SEITH — sistem trading kuantitatif (Bayesian, CVaR, order-flow) "
            "menunjukkan pemahaman domain finansial/ERP."
        )
    if not points:
        points.append(
            "Portofolio AI + fullstack + sistem (Python, Rust, TypeScript) "
            "dengan 34+ repo & 560+ commit GitHub."
        )
    return points


def prioritize(items: list[dict]) -> list[dict]:
    """Urutkan target berdasarkan skor prioritas (fit + AI + karir + responsif + jarak)."""
    scored: list[tuple[float, dict, str]] = []
    for item in items:
        fit = item.get("fit", 0)
        ai = bool(item.get("ai"))
        career = bool(item.get("career"))
        n_resp = int(item.get("n_resp", 0))
        distance = float(item.get("distance", 9.0))
        score = (
            fit
            + (30 if ai else 0)
            + (25 if career else 0)
            + min(20, n_resp * 4)
            - max(0.0, (distance - 3.0) * 3.0)
        )
        reasons: list[str] = []
        if ai:
            reasons.append("fokus AI (sejalan dengan CV)")
        if career:
            reasons.append("halaman karir (terbuka PKL)")
        if n_resp >= 3:
            reasons.append(f"{n_resp} review menyebut responsif")
        if distance <= 2:
            reasons.append("sangat dekat rumah")
        scored.append((round(score, 1), item, "; ".join(reasons) or "kandidat layak"))

    scored.sort(key=lambda entry: -entry[0])
    return [
        {"rank": i, "score": s, "item": item, "reason": reason}
        for i, (s, item, reason) in enumerate(scored, start=1)
    ]


def build_target_section(
    idx: int,
    company: object,
    profile: object | None,
    fit: float,
    ai: bool,
    reviews: list[object],
    cv_analysis: dict | None,
) -> list[str]:
    """Bagian markdown untuk satu target."""
    lines: list[str] = []
    lines.append(f"### {idx}. {company.name}")
    role_label = ", ".join(company.role_fit) or "-"
    if profile and profile.ai_focus:
        ai_txt = "Ya — " + " / ".join(profile.ai_subfields)
    elif ai:
        ai_txt = "Ya (tag peran, belum terkonfirmasi website)"
    else:
        ai_txt = "Tidak terdeteksi"
    lines.append(
        f"- **Skor kecocokan CV**: {fit:g}/100 (arah: {role_label}) · AI: {ai_txt}"
    )
    lines.append(
        f"- **Data kunci**: Rating {company.rating} ({company.review_count} ulasan) · "
        f"Jarak {company.distance_km:.1f} km · Sektor {company.sector or '-'} · Status: shortlisted"
    )
    if profile:
        if profile.core_focus:
            lines.append(f"- **Fokus**: {_one_line(profile.core_focus, 300)}")
        if profile.about_text:
            lines.append(f"- **Tentang**: {_one_line(profile.about_text, 300)}")
        if profile.services_text:
            lines.append(f"- **Layanan**: {_one_line(profile.services_text, 200)}")
        if profile.career_page_found:
            lines.append(f"- **Halaman karir**: Ya — {profile.career_url}")
        if profile.emails:
            lines.append(f"- **Email kontak**: {', '.join(profile.emails)}")
    lines.append("- **Kenapa cocok dengan CV-mu**:")
    for point in cv_match_points(company, profile, cv_analysis):
        lines.append(f"  - {point}")
    quotes = responsive_reviews(reviews)
    if quotes:
        lines.append(f"- **Sinyal responsif** ({len(quotes)} review menyebut responsif):")
        for quote in quotes:
            lines.append(f'  - "{quote}"')
    else:
        lines.append("- **Sinyal responsif**: belum ada indikasi dari review yang diambil")
    if profile and profile.emails:
        lines.append(f"- **Cara kontak terbaik**: email {', '.join(profile.emails[:2])}")
    else:
        lines.append("- **Cara kontak terbaik**: form kontak / WhatsApp di website")
    lines.append("")
    return lines


def _one_line(text: str, limit: int) -> str:
    return _WS_RE.sub(" ", text).strip()[:limit]
