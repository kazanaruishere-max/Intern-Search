from pkl_research.models import Company, CompanyProfile, Review
from pkl_research.target_analysis import (
    build_target_section,
    cv_match_points,
    prioritize,
    responsive_reviews,
)


def make_company(**kw):
    base = dict(place_id="p", name="PT Target", category="Software house",
                rating=4.8, review_count=50, distance_km=2.0, role_fit=["ai"],
                sector="swasta", id=1)
    base.update(kw)
    return Company(**base)


def make_profile(**kw):
    base = dict(company_id=1, core_focus="Chatbot AI berbasis LLM",
                about_text="Kami membangun solusi AI dan chatbot.", ai_focus=True,
                ai_subfields=["Chatbot / Virtual Assistant"], ai_evidence=["buat chatbot"],
                emails=["hr@target.com"], career_page_found=True)
    base.update(kw)
    return CompanyProfile(**base)


def make_reviews():
    return [
        Review(company_id=1, reviewer_name="A", reviewer_rating=5,
               review_text="Timnya sangat responsif dan cepat balas."),
        Review(company_id=1, reviewer_name="B", reviewer_rating=4,
               review_text="Respon cukup, komunikasi enak."),
        Review(company_id=1, reviewer_name="C", reviewer_rating=3,
               review_text="Lumayan."),
    ]


def test_responsive_reviews():
    quotes = responsive_reviews(make_reviews())
    assert len(quotes) == 2
    assert "responsif" in quotes[0]


def test_cv_match_chatbot_mentions_safewallet():
    c = make_company()
    p = make_profile(ai_subfields=["Chatbot / Virtual Assistant"])
    points = cv_match_points(c, p, None)
    assert any("SafeWallet AI" in pt for pt in points)
    assert any("LLM" in pt for pt in points)


def test_cv_match_finance_mentions_seith():
    c = make_company(role_fit=["software"])
    p = make_profile(ai_focus=False, ai_subfields=[],
                     core_focus="ERP akuntansi dan keuangan bisnis")
    points = cv_match_points(c, p, None)
    assert any("SEITH" in pt for pt in points)


def test_cv_match_fullstack():
    c = make_company(role_fit=["fullstack"])
    p = make_profile(ai_focus=False, ai_subfields=[])
    points = cv_match_points(c, p, None)
    assert any("fullstack" in pt.lower() for pt in points)


def test_prioritize_ai_and_career_first():
    items = [
        {"fit": 70, "ai": False, "career": False, "n_resp": 0, "distance": 5.0},
        {"fit": 70, "ai": True, "career": True, "n_resp": 6, "distance": 3.0},
    ]
    result = prioritize(items)
    assert result[0]["rank"] == 1
    assert result[0]["item"]["ai"] is True


def test_build_section_contains_key_fields():
    c = make_company()
    p = make_profile()
    lines = build_target_section(1, c, p, 73.0, True, make_reviews(), None)
    text = "\n".join(lines)
    assert "### 1. PT Target" in text
    assert "Skor kecocokan CV" in text
    assert "Kenapa cocok" in text
    assert "Sinyal responsif" in text
    assert "Cara kontak terbaik" in text
    assert "hr@target.com" in text
