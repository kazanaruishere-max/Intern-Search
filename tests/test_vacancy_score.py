from pkl_research.models import Vacancy
from pkl_research.vacancy_score import (
    calculate_overlap_score,
    detect_red_flags,
    evaluate_vacancy,
)


def test_detect_red_flags():
    text1 = "This is an unpaid internship for students."
    assert "unpaid" in detect_red_flags(text1)

    text2 = "We offer a competitive salary and monthly stipend."
    assert not detect_red_flags(text2)


def test_calculate_overlap_score():
    cv_skills = ["Python", "React", "Rust", "C++", "C#"]
    job_text = "We are looking for a Python and C++ developer. Experience with React is a plus."
    score, matched, missing = calculate_overlap_score(cv_skills, job_text)
    assert score == 60.0
    assert "Python" in matched
    assert "React" in matched
    assert "C++" in matched
    assert "Rust" in missing


def test_evaluate_vacancy_full():
    vacancy = Vacancy(
        source="himalayas",
        source_id="h1",
        title="Frontend Intern",
        company_name="Vercel",
        location="Remote",
        remote=True,
        employment_type="intern",
        description_text="We need someone with React and JavaScript experience. This is an unpaid role.",
        tags=["React", "Frontend"],
        posted_at="2026-08-10T12:00:00",
    )
    cv_analysis = {
        "skills": {
            "software": ["Python"],
            "fullstack": ["React", "JavaScript", "Node.js"],
        }
    }
    # 2 matched out of 4 total unique skills (Python, React, JavaScript, Node.js) -> 50%
    # +15 remote
    # +15 intern
    # -15 red flag (unpaid)
    # total = 50 + 15 + 15 - 15 = 65
    res = evaluate_vacancy(vacancy, cv_analysis)
    assert res["score"] == 65.0
    assert "unpaid" in res["red_flags"]
    assert "React" in res["matched_skills"]
