"""Pure scoring system (0-100) for vacancies based on CV match and flags."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkl_research.models import Vacancy

RED_FLAG_PATTERNS = [
    (r"\bunpaid\b", "unpaid"),
    (r"\bno stipend\b", "no stipend"),
    (r"\bno salary\b", "no salary"),
    (r"\bno pay\b", "no pay"),
    (r"\bvolunteer\b", "volunteer"),
]


def detect_red_flags(text: str) -> list[str]:
    """Cari red flag dalam teks lowongan (unpaid, no stipend, dll)."""
    flags = []
    text_lower = text.lower()
    for pattern, label in RED_FLAG_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(label)
    return flags


def calculate_overlap_score(cv_skills: list[str], job_text: str) -> tuple[float, list[str], list[str]]:
    """Hitung persentase overlap skill CV dengan Job Description.

    Return (score, matched_skills, missing_skills).
    """
    if not cv_skills:
        return 0.0, [], []

    matched = []
    missing = []
    job_text_lower = job_text.lower()

    for skill in cv_skills:
        skill_clean = skill.lower().strip()
        # Handle c++ and c# word boundaries carefully
        if "++" in skill_clean or "#" in skill_clean:
            found = skill_clean in job_text_lower
        else:
            found = re.search(rf"\b{re.escape(skill_clean)}\b", job_text_lower) is not None

        if found:
            matched.append(skill)
        else:
            missing.append(skill)

    score = (len(matched) / len(cv_skills)) * 100.0
    return score, matched, missing


def evaluate_vacancy(vacancy: Vacancy, cv_analysis: dict | None) -> dict[str, object]:
    """Evaluasi lowongan secara mendalam. Return dict dengan score dan flags."""
    # Flatten all CV skills
    cv_skills = []
    if cv_analysis and "skills" in cv_analysis:
        for skills_list in cv_analysis["skills"].values():
            for skill in skills_list:
                if skill not in cv_skills:
                    cv_skills.append(skill)

    title = vacancy.title or ""
    desc = vacancy.description_text or ""
    tags_str = " ".join(vacancy.tags) if vacancy.tags else ""
    full_text = f"{title}\n{desc}\n{tags_str}"

    overlap_pct, matched, missing = calculate_overlap_score(cv_skills, full_text)

    # Base score is the skill overlap
    score = overlap_pct

    # Remote bonus
    if vacancy.remote:
        score += 15.0

    # Employment type fit (internship is highly preferred)
    if vacancy.employment_type == "intern":
        score += 15.0

    # Red flag penalty
    red_flags = detect_red_flags(full_text)
    score -= len(red_flags) * 15.0

    # Repost penalty (reposted multiple times is slightly degraded)
    if vacancy.repost_count > 0:
        score -= min(20.0, vacancy.repost_count * 10.0)

    # Ghost flag (first seen > 30 days ago and still active)
    from datetime import datetime, timezone
    ghost_flag = False
    if vacancy.first_seen:
        try:
            first_dt = datetime.fromisoformat(vacancy.first_seen.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            delta = (now_dt - first_dt).days
            if delta > 30:
                ghost_flag = True
                score -= 10.0
        except Exception:
            pass

    # Clamp score 0-100
    final_score = max(0.0, min(100.0, score))

    return {
        "score": round(final_score, 1),
        "matched_skills": matched,
        "missing_skills": missing,
        "red_flags": red_flags,
        "repost_flag": repost_flag if "repost_flag" in locals() else (vacancy.repost_count > 1),
        "ghost_flag": ghost_flag,
    }
