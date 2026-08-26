"""Test redflag.py: red flag, green flag, health scoring."""

import pytest

from pkl_research.models import Company, CompanyProfile, Review
from pkl_research.redflag import (
    analyze_health,
    detect_green_flags,
    detect_red_flags,
    health_score,
)


def make_company(**kw):
    base = dict(place_id="p", name="PT Test", rating=4.8, review_count=50,
                distance_km=3.0, is_it=True, id=1,
                category="Perusahaan Software", website="https://test.com")
    base.update(kw)
    return Company(**base)


def make_profile(**kw):
    base = dict(company_id=1, core_focus="AI development",
                career_page_found=True, career_url="https://test.com/career",
                emails=["hr@test.com"], site_title="Test Corp",
                meta_description="Software company")
    base.update(kw)
    return CompanyProfile(**base)


def make_reviews(*texts):
    return [Review(company_id=1, reviewer_name=f"R{i}", reviewer_rating=5,
                   review_text=t) for i, t in enumerate(texts, 1)]


# --- Green flags ---

def test_green_mentorship():
    reviews = make_reviews("Timnya sangat responsif, mentoring bagus.")
    flags = detect_green_flags(make_company(), make_profile(), reviews)
    assert any(f.category == "Mentorship" for f in flags)


def test_green_career_page():
    p = make_profile(career_page_found=True)
    flags = detect_green_flags(make_company(), p, [])
    assert any(f.category == "Career" for f in flags)


def test_green_corporate_email():
    c = make_company(website="https://test.com")
    p = make_profile(emails=["hr@test.com"])
    flags = detect_green_flags(c, p, [])
    assert any("korporate" in f.message.lower() for f in flags)


# --- Red flags ---

def test_red_financial_instability():
    reviews = make_reviews("Gaji telat 2 bulan terakhir.", "Bagus sih tapi sering lembur.")
    flags = detect_red_flags(make_company(), None, reviews)
    assert any(f.category == "Financial" for f in flags)


def test_red_toxic_culture():
    reviews = make_reviews("Lingkungannya toxic dan burnout.")
    flags = detect_red_flags(make_company(), None, reviews)
    assert any(f.category == "Toxic" for f in flags)


def test_red_website_down():
    from unittest.mock import MagicMock
    p = MagicMock(spec=CompanyProfile)
    p.fetch_status = "failed"
    p.about_text = None
    p.services_text = None
    p.emails = None
    flags = detect_red_flags(make_company(), p, [])
    assert any("website" in f.message.lower() for f in flags)


def test_no_red_flags_healthy_company():
    reviews = make_reviews("Tim solid dan responsif.", "Mentoring bagus.")
    flags = detect_red_flags(make_company(), None, reviews)
    assert len(flags) == 0


# --- Health score ---

def test_health_sehat():
    greens = [
        __import__("pkl_research.redflag", fromlist=["Flag"]).Flag(tag="green", category="Culture", message="ok"),
        __import__("pkl_research.redflag", fromlist=["Flag"]).Flag(tag="green", category="Career", message="ok"),
    ]
    report = health_score([], greens)
    assert report.score >= 70 and report.label == "SEHAT"


def test_health_red_flag():
    reds = [
        __import__("pkl_research.redflag", fromlist=["Flag"]).Flag(tag="red", category="Financial", message="ok"),
        __import__("pkl_research.redflag", fromlist=["Flag"]).Flag(tag="red", category="Toxic", message="ok"),
    ]
    report = health_score(reds, [])
    assert report.score < 40 and report.label == "RED FLAG"


# --- Full analysis ---

def test_analyze_full():
    c = make_company()
    p = make_profile()
    reviews = make_reviews(
        "Timnya responsif, mentoring bagus.",
        "Gaji telat 2 bulan.",
    )
    report = analyze_health(c, p, reviews)
    assert isinstance(report.score, int)
    assert 0 <= report.score <= 100
    assert report.label in ("SEHAT", "CAUTIOUS", "RED FLAG")
