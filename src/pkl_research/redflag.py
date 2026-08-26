"""Red flag + Green flag detection & health scoring (pure, no I/O)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pkl_research import config
from pkl_research.models import Company


@dataclass
class Flag:
    tag: str  # "red" | "green"
    category: str  # e.g. "financial", "culture", "mentorship"
    message: str
    evidence: str = ""
    count: int = 1


@dataclass
class HealthReport:
    score: int  # 0–100
    label: str  # 🟢 SEHAT / 🟡 CAUTIOUS / 🔴 RED FLAG
    red_flags: list[Flag] = field(default_factory=list)
    green_flags: list[Flag] = field(default_factory=list)

    @property
    def emoji(self) -> str:
        if self.label == "SEHAT":
            return "🟢"
        if self.label == "CAUTIOUS":
            return "🟡"
        return "🔴"


def _find_flag_evidence(reviews: list[Review], keywords: list[str], limit: int = 2) -> list[str]:
    """Ambil kutipan review yang mengandung keyword."""
    evidence = []
    for r in reviews:
        text = (r.review_text or "").lower()
        for kw in keywords:
            if kw in text:
                clean = re.sub(r"\s+", " ", r.review_text).strip()[:120]
                evidence.append(f'"{clean}"')
                break
        if len(evidence) >= limit:
            break
    return evidence


def detect_red_flags(
    company: Company,
    profile: object | None,
    reviews: list,
) -> list[Flag]:
    """Deteksi red flags dari review + website profile."""
    flags: list[Flag] = []
    blob_reviews = " ".join((r.review_text or "").lower() for r in reviews)
    blob_all = blob_reviews + " " + ((profile.about_text or "") + (profile.services_text or "")).lower() if profile else blob_reviews

    for category, keywords in config.RED_FLAG_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in blob_reviews]
        if not hits:
            continue
        evidence = _find_flag_evidence(reviews, [h for h in hits])
        flags.append(Flag(
            tag="red",
            category=category.replace("_", " ").title(),
            message=f"Disebut di review ({len(hits)} keyword): {', '.join(hits[:3])}",
            evidence=" | ".join(evidence[:2]),
            count=len(hits),
        ))

    # Website down
    if profile and getattr(profile, "fetch_status", "") == "failed":
        flags.append(Flag(tag="red", category="Professional",
                          message="Website tidak dapat diakses"))

    # No corporate email
    if profile and not profile.emails and company.website:
        flags.append(Flag(tag="red", category="Professional",
                          message="Tidak ada email korporate yang terdeteksi"))

    # Multi-domain specialization (services listing >5 domain sangat berbeda)
    if profile and profile.services_text:
        svc = profile.services_text.lower()
        domains = sum(1 for d in ("web", "mobile", "ai", "game", "desain",
                                  "marketing", "e-commerce", "blockchain") if d in svc)
        if domains >= 5:
            flags.append(Flag(tag="red", category="Specialization",
                              message=f"Klaim {domains} domain sekaligus — kemungkinan generalisasi tanpa spesialisasi"))

    return flags


def detect_green_flags(
    company: Company,
    profile: object | None,
    reviews: list,
) -> list[Flag]:
    """Deteksi green flags dari review + website profile."""
    flags: list[Flag] = []

    for category, keywords in config.GREEN_FLAG_KEYWORDS.items():
        hits = [kw for r in reviews for kw in keywords
                if kw in (r.review_text or "").lower()]
        if not hits:
            continue
        unique_hits = sorted(set(hits))
        evidence = _find_flag_evidence(reviews, unique_hits)
        flags.append(Flag(
            tag="green",
            category=category.replace("_", " ").title(),
            message=f"Review menyebut ({len(unique_hits)} sinyal): {', '.join(unique_hits[:3])}",
            evidence=" | ".join(evidence[:2]),
            count=len(unique_hits),
        ))

    # Career page aktif
    if profile and getattr(profile, "career_page_found", False):
        flags.append(Flag(tag="green", category="Career",
                          message=f"Halaman karir aktif — {getattr(profile, 'career_url', '')}"))

    # Corporate email
    if profile and profile.emails:
        corporate = [e for e in profile.emails
                     if company.website and any(
                         d in e.split("@")[-1].lower()
                         for d in [company.website.split("//")[-1].split("/")[0].replace("www.", "")]
                     )]
        if corporate:
            flags.append(Flag(tag="green", category="Professional",
                              message=f"Email korporate: {', '.join(corporate)}"))

    # Specialized focus (≤3 domain)
    if profile and profile.services_text:
        svc = profile.services_text.lower()
        domains = sum(1 for d in ("web development", "mobile app", "AI solutions",
                                  "cloud infrastructure") if d in svc)
        if 1 <= domains <= 3:
            flags.append(Flag(tag="green", category="Specialization",
                              message=f"Fokus pada {domains} domain utama"))

    # Website profesional (title + meta lengkap)
    if profile and profile.site_title and profile.meta_description:
        flags.append(Flag(tag="green", category="Professional",
                          message="Website profesional dengan metadata lengkap"))

    return flags


def health_score(red_flags: list[Flag], green_flags: list[Flag]) -> HealthReport:
    """Hitung health score: base 50 + greens*10 - reds*15, clamp 0–100."""
    score = max(0, min(100, 50 + len(green_flags) * 10 - len(red_flags) * 15))
    if score >= 70:
        label = "SEHAT"
    elif score >= 40:
        label = "CAUTIOUS"
    else:
        label = "RED FLAG"
    return HealthReport(score=score, label=label, red_flags=red_flags, green_flags=green_flags)


def analyze_health(company: Company, profile: object | None, reviews: list) -> HealthReport:
    """Full analysis: deteksi red + green flags → health report."""
    reds = detect_red_flags(company, profile, reviews)
    greens = detect_green_flags(company, profile, reviews)
    return health_score(reds, greens)
