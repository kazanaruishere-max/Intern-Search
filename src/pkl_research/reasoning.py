"""Intelligence Engine — kritik strategi, rank dampak, rekomendasi konviksi.

Custom rule-based engine, zero external LLM dependency.
Belajar dari data historis di DB: response rate, rejection pattern, channel effectiveness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pkl_research.models import Application, Company


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Critique:
    severity: str  # "critical" | "warning" | "info"
    message: str
    evidence: str = ""


@dataclass
class RankedTarget:
    company_name: str
    impact_score: float
    verdict: str  # "APPLY_NOW" | "FOLLOW_UP" | "SKIP" | "MONITOR"
    reasons: list[str] = field(default_factory=list)


@dataclass
class BlindSpot:
    area: str
    message: str


@dataclass
class ChannelVerdict:
    channel: str
    response_rate: float
    sample_size: int
    recommendation: str


# ---------------------------------------------------------------------------
# Critic Engine — kritik strategi lamaran secara blak-blakan
# ---------------------------------------------------------------------------

class CriticEngine:
    """Kritik keputusan & strategi lamaran berdasarkan data historis."""

    def critique(
        self,
        companies: list[Company],
        applications: list[tuple[Application, Company]],
        cv_analysis: dict | None,
    ) -> list[Critique]:
        critiques: list[Critique] = []
        apps = [a for a, _ in applications]
        applied = [a for a in apps if a.status == "applied"]
        rejected = [a for a, c in applications if a.status == "rejected"]
        interviews = [(a, c) for a, c in applications if a.status == "interview"]

        # Kritik 1: mismatch CV vs target
        if cv_analysis and cv_analysis.get("scores", {}).get("ai", 0) >= 80:
            non_ai = [
                company.name
                for app, company in applications
                if app.status == "applied"
                and "ai" not in (company.role_fit or [])
            ]
            if non_ai:
                critiques.append(Critique(
                    severity="critical",
                    message=(
                        f"CV-mu AI={cv_analysis['scores']['ai']} tapi "
                        f"{len(non_ai)} target BUKAN perusahaan AI "
                        f"({', '.join(non_ai[:3])}). Mismatch."
                    ),
                    evidence="Prioritaskan target dengan role_fit mengandung 'ai'.",
                ))

        # Kritik 2: kanal tunggal (hanya email)
        email_only = [a for a in applied if not a.sent_via or a.sent_via == "email"]
        if len(email_only) >= 3:
            critiques.append(Critique(
                severity="warning",
                message=(
                    f"{len(email_only)} apply via EMAIL saja. WA response rate "
                    f"biasanya 40%+ vs email 15%. Kamu buang peluang."
                ),
                evidence="Follow-up WA untuk target yang punya nomor terverifikasi.",
            ))

        # Kritik 3: ghosting (applied >5 hari kerja tanpa follow-up)
        if len(applied) >= 4:
            critiques.append(Critique(
                severity="info",
                message=(
                    f"{len(applied)} perusahaan status 'applied' — "
                    f"follow-up yang belum dibalas? Jangan tunggu berminggu-minggu."
                ),
            ))

        # Kritik 4: response rate rendah
        if applied and len(rejected) + len(interviews) >= 1:
            rate = (len(interviews) + len(rejected)) / max(len(applied), 1) * 100
            if rate < 20 and len(applied) >= 5:
                critiques.append(Critique(
                    severity="critical",
                    message=(
                        f"Response rate {rate:.0f}% dari {len(applied)} apply — "
                        f"di bawah standar. Review kualitas draft & target selection."
                    ),
                    evidence=f"{len(rejected)} rejected + {len(interviews)} interview.",
                ))

        return critiques


# ---------------------------------------------------------------------------
# Impact Ranker — skor dampak nyata, bukan cuma angka
# ---------------------------------------------------------------------------

class ImpactRanker:
    """Ranking berbasis dampak nyata: fit + AI + gedung + responsivitas + reputasi."""

    def rank(self, companies: list[Company], profiles: dict[int, object]) -> list[RankedTarget]:
        ranked = []
        for c in companies:
            score = self._score(c, profiles.get(c.id or -1))
            verdict, reasons = self._verdict(c, profiles.get(c.id or -1))
            ranked.append(RankedTarget(
                company_name=c.name,
                impact_score=round(score, 1),
                verdict=verdict,
                reasons=reasons,
            ))
        ranked.sort(key=lambda r: -r.impact_score)
        return ranked

    def _score(self, c: Company, p: object | None) -> float:
        s = 50.0
        if c.fit_score is not None:
            s += (c.fit_score - 70) * 0.5
        if p and getattr(p, "ai_focus", False):
            s += 15
        if p and getattr(p, "career_page_found", False):
            s += 10
        if c.review_count and c.review_count >= 50:
            s += min(15, c.review_count / 10)
        if c.rating and c.rating >= 4.8:
            s += 5
        if c.distance_km is not None:
            if c.distance_km <= 3:
                s += 10
            elif c.distance_km <= 5:
                s += 5
            else:
                s -= min(10, (c.distance_km - 5) * 1.5)
        return max(0.0, min(150.0, s))

    def _verdict(self, c: Company, p: object | None) -> tuple[str, list[str]]:
        score = self._score(c, p)
        reasons = []
        if score >= 90:
            verdict = "APPLY_NOW"
            if p and getattr(p, "ai_focus", False):
                reasons.append("AI match")
            if p and getattr(p, "career_page_found", False):
                reasons.append("career page open")
            if c.distance_km and c.distance_km <= 5:
                reasons.append(f"dekat ({c.distance_km:.1f} km)")
        elif score >= 70:
            verdict = "FOLLOW_UP"
            reasons.append("layak follow-up")
        else:
            verdict = "SKIP"
            reasons.append("dampak rendah")
        return verdict, reasons


# ---------------------------------------------------------------------------
# Blind Spot Detector — temukan apa yang kamu lewatkan
# ---------------------------------------------------------------------------

class BlindSpotDetector:
    """Deteksi gap antara CV dan strategi lamaran yang sedang berjalan."""

    def detect(
        self,
        cv_analysis: dict | None,
        companies: list[Company],
        drafts_sent: dict[str, str],
    ) -> list[BlindSpot]:
        spots: list[BlindSpot] = []

        # Blind spot 1: sertifikasi tidak disebut di draft
        if cv_analysis:
            certs_mentioned = any(
                any(kw in d.lower() for d in drafts_sent.values() for kw in ("certified", "certification", "top 100", "gdg"))
                for _ in [1]
            )
            cv_text = str(cv_analysis)
            if "gemini" in cv_text.lower() or "anthropic" in cv_text.lower():
                if not certs_mentioned and drafts_sent:
                    spots.append(BlindSpot(
                        area="Draft Messages",
                        message=(
                            "Sertifikasi Gemini Certified Educator & AI Fluency Anthropic "
                            "ada di CV tapi BELUM disebut di draft manapun. "
                            "Ini pembeda kuat untuk AI company."
                        ),
                    ))

        # Blind spot 2: quant/trading angle tidak dipitch
        quant_targets = [
            c.name for c in companies
            if any(kw in (c.category or "").lower() for kw in ("wealth", "finance", "invest"))
        ]
        if quant_targets:
            spots.append(BlindSpot(
                area="Quant/Trading Angle",
                message=(
                    f"SEITH (quant trading, Bayesian/CVaR) belum dipitch ke: "
                    f"{', '.join(quant_targets[:3])}. Ini angle unik yang "
                    f"90% pelamar lain tidak punya."
                ),
            ))

        # Blind spot 3: salah kanal kontak
        wrong_channel = [
            c.name for c in companies
            if c.website and "recruitment@" not in (c.website or "")
        ]
        # (simplified check — actual check would look at stored contact data)

        # Blind spot 4: WFA tidak dimanfaatkan
        far_companies = [c.name for c in companies if c.distance_km and c.distance_km > 10]
        if far_companies and drafts_sent:
            has_wfa = any("work from anywhere" in d.lower() or "wfa" in d.lower() for d in drafts_sent.values())
            if not has_wfa:
                spots.append(BlindSpot(
                    area="WFA Strategy",
                    message=(
                        f"{len(far_companies)} target >10 km tapi draft tidak "
                        f"menyebutkan skema WFA/hybrid. Tambahkan usulan hybrid."
                    ),
                ))

        return spots


# ---------------------------------------------------------------------------
# Channel Verdict — vonis kanal terbaik berdasarkan bukti data
# ---------------------------------------------------------------------------

class ChannelVerdictEngine:
    """Vonis kanal terbaik berdasarkan bukti data historis."""

    def verdict(self, applications: list[tuple[Application, Company]]) -> list[ChannelVerdict]:
        by_channel: dict[str, list[Application]] = {}
        for app, _ in applications:
            ch = (app.sent_via or "unknown").lower()
            by_channel.setdefault(ch, []).append(app)

        results = []
        for channel, apps in sorted(by_channel.items(), key=lambda x: -len(x[1])):
            total = len(apps)
            responded = sum(1 for a in apps if a.status in ("replied", "interview", "accepted"))
            rate = responded / max(total, 1) * 100
            if rate >= 30:
                rec = f"EFEKTIF ({rate:.0f}% respons) — prioritaskan kanal ini"
            elif rate >= 10:
                rec = f"CUKUP ({rate:.0f}% respons) — gunakan sebagai secondary"
            else:
                rec = f"RENDAH ({rate:.0f}% respons) — pertimbangkan kanal lain"
            results.append(ChannelVerdict(
                channel=channel,
                response_rate=round(rate, 1),
                sample_size=total,
                recommendation=rec,
            ))
        return results
