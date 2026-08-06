"""Generator draft pesan lamaran PKL (template pintar, offline)."""

from __future__ import annotations

import re

from pkl_research import config
from pkl_research.models import Company, Review

POSITIVE_KEYWORDS = [
    "rekomendasi", "recommend", "profesional", "professional", "responsif",
    "responsive", "ramah", "friendly", "membantu", "helpful", "cepat", "fast",
    "puas", "satisfied", "bagus", "good", "great", "excellent", "terbaik",
    "best", "kualitas", "quality", "detail", "rapi", "komunikatif", "sesuai",
    "mudah", "easy", "aman", "reliable", "tim", "layanan",
]

_WS_RE = re.compile(r"\s+")


def review_highlights(reviews: list[Review], limit: int = 2) -> list[str]:
    """Pilih kutipan pendek dari review positif (rating >= 4)."""
    positive = [
        r for r in reviews if (r.reviewer_rating or 0) >= 4 and r.review_text
    ]
    positive.sort(key=lambda r: -(r.reviewer_rating or 0))
    highlights: list[str] = []
    for r in positive[:limit]:
        text = _WS_RE.sub(" ", r.review_text or "").strip()
        if not text:
            continue
        quote = text if len(text) <= 140 else text[:137].rstrip() + "..."
        highlights.append(f'"{quote}"')
    return highlights


def theme_counts(reviews: list[Review], limit: int = 3) -> list[str]:
    """Tema pujian yang paling sering muncul di review."""
    counts: dict[str, int] = {}
    for r in reviews:
        text = (r.review_text or "").lower()
        for keyword in POSITIVE_KEYWORDS:
            if keyword in text:
                counts[keyword] = counts.get(keyword, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    return [f"{kw} ({n}x)" for kw, n in top]


def role_text(role_fit: list[str]) -> str:
    if not role_fit:
        return "bidang IT"
    labels = [config.ROLE_LABEL_ID[r] for r in role_fit if r in config.ROLE_LABEL_ID]
    if not labels:
        return "bidang IT"
    return " & ".join(labels)


def _cv_skill_line(company: Company, cv_analysis: dict | None) -> str:
    """Kalimat skill relevan dari hasil analisa CV, untuk role_fit perusahaan."""
    if not cv_analysis:
        return ""
    role_fit = company.role_fit
    if not role_fit:
        return ""
    scores = cv_analysis.get("scores", {})
    best = max(role_fit, key=lambda r: scores.get(r, 0), default=None)
    if not best or scores.get(best, 0) <= 0:
        return ""
    skills = (cv_analysis.get("skills", {}).get(best, []) or [])[:4]
    if not skills:
        return ""
    label = config.ROLE_LABEL_ID.get(best, best)
    return (
        f"Skill saya yang relevan dengan fokus {label}: "
        f"{', '.join(skills)}."
    )


def _build_context(
    company: Company,
    reviews: list[Review],
    identity: dict[str, str],
    profile: object | None = None,
    cv_analysis: dict | None = None,
) -> dict[str, str]:
    highlights = review_highlights(reviews)
    if highlights:
        praise = "Pelanggan sering memuji, antara lain: " + " ".join(highlights)
    else:
        praise = "Perusahaan ini memiliki reputasi baik di mata pelanggannya."
    jarak = (
        f"{company.distance_km:.1f} km"
        if company.distance_km is not None
        else "dekat dari domisili saya"
    )
    kontak = identity["email"] or identity["telepon"] or "[kontak kamu]"

    profil_line = ""
    if profile is not None:
        core_focus = getattr(profile, "core_focus", None)
        ai_subfields = getattr(profile, "ai_subfields", None) or []
        parts: list[str] = []
        if core_focus:
            parts.append(
                f"Di website resmi {company.name}, saya melihat fokus perusahaan "
                f"Anda di: {core_focus}"
            )
        if getattr(profile, "ai_focus", False) and ai_subfields:
            parts.append(
                "Yang paling menarik, Anda juga aktif di bidang "
                + " & ".join(ai_subfields[:2])
                + " — bidang yang sangat saya minati untuk ditekuni."
            )
        if parts:
            profil_line = " ".join(parts)

    cv_line = _cv_skill_line(company, cv_analysis)

    return {
        "nama": identity["nama"],
        "sekolah": identity["sekolah"],
        "jurusan": identity["jurusan"],
        "durasi_pkl": identity["durasi_pkl"],
        "perusahaan": company.name,
        "lokasi": company.address or "Jakarta Selatan",
        "rating": f"{company.rating:g}" if company.rating else "-",
        "review_count": str(company.review_count or 0),
        "role": role_text(company.role_fit),
        "praise": praise,
        "jarak": jarak,
        "kontak": kontak,
        "profil_line": profil_line,
        "cv_line": cv_line,
    }


FORMAL = """Halo tim {perusahaan},

Perkenalkan, saya {nama}, {jurusan} dari {sekolah}. Saat ini saya sedang mencari tempat Praktik Kerja Lapangan (PKL) di bidang {role}, dan {perusahaan} menjadi salah satu pilihan utama saya.

Saya tertarik setelah melihat {perusahaan} memiliki rating {rating} dari {review_count} ulasan di Google Maps. {praise}
{profil_line}
{cv_line}

Lokasi {perusahaan} juga tidak jauh dari domisili saya di Jakarta Selatan ({jarak}), sehingga saya dapat berkomitmen penuh selama PKL {durasi_pkl}.

Saya sangat antusias untuk belajar dan berkontribusi di tim Anda. Apakah berkenan jika saya mengirimkan CV dan portofolio untuk dipertimbangkan?

Hormat saya,
{nama}
{kontak}"""

CASUAL = """Halo kak/tim {perusahaan},

Saya {nama}, {jurusan} dari {sekolah}, lagi cari tempat PKL ({durasi_pkl}) di bidang {role}. Waktu riset, {perusahaan} langsung masuk radar saya — ratingnya {rating} dari {review_count} ulasan. {praise}
{profil_line}
{cv_line}

Lokasi kantornya juga dekat dari domisili saya ({jarak}), jadi mobilitas selama PKL aman. Saya pengen banget belajar sekaligus bantu-bantu tim {perusahaan}, apalagi saya lagi fokus ngembangin skill di bidang {role}.

Kalau berkenan, saya boleh kirim CV/portofolio untuk dipertimbangkan ya. Terima kasih banyak!

{nama}
{kontak}"""

SHORT = """Halo {perusahaan},

Saya {nama} ({jurusan}, {sekolah}) sedang mencari tempat PKL {durasi_pkl} di bidang {role}. Melihat {perusahaan} dengan rating {rating} dari {review_count} ulasan, saya sangat tertarik untuk belajar dan berkontribusi.
{profil_line}
{cv_line}

Domisili saya di Jakarta Selatan, dekat dengan kantor Anda ({jarak}). Boleh saya kirim CV untuk dipertimbangkan?

Terima kasih,
{nama}
{kontak}"""

TEMPLATES: dict[str, str] = {
    "formal": FORMAL,
    "casual": CASUAL,
    "short": SHORT,
}


def build_drafts(
    company: Company,
    reviews: list[Review],
    identity: dict[str, str],
    profile: object | None = None,
    cv_analysis: dict | None = None,
) -> dict[str, str]:
    """Hasilkan 3 varian draft pesan untuk satu perusahaan."""
    ctx = _build_context(company, reviews, identity, profile, cv_analysis)
    return {name: template.format(**ctx) for name, template in TEMPLATES.items()}
