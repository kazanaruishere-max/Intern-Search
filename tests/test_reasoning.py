from pkl_research.automation import get_mode, is_full_auto  # noqa: F401
from pkl_research.models import Application, Company, CompanyProfile, Review
from pkl_research.reasoning import (
    BlindSpotDetector,
    ChannelVerdictEngine,
    CriticEngine,
    ImpactRanker,
)


def make_company(**kw):
    base = dict(place_id="p", name="PT Test", rating=4.8, review_count=60,
                distance_km=3.0, role_fit=["ai"], is_it=True, id=1,
                category="Perusahaan Software", fit_score=80)
    base.update(kw)
    return Company(**base)


def make_app(**kw):
    base = dict(company_id=1, status="applied", sent_via="email")
    base.update(kw)
    return Application(**base)


def make_profile(**kw):
    base = dict(company_id=1, ai_focus=True, career_page_found=True)
    base.update(kw)
    return CompanyProfile(**base)


def test_critic_email_only():
    engine = CriticEngine()
    apps = [(make_app(sent_via="email"), make_company(id=i)) for i in range(1, 5)]
    critiques = engine.critique([], apps, None)
    assert any("EMAIL" in c.message or "email" in c.message.lower() for c in critiques)


def test_critic_low_response_rate():
    engine = CriticEngine()
    companies = [make_company(id=i) for i in range(1, 7)]
    apps = [(make_app(company_id=i), c) for i, c in enumerate(companies, 1)]
    # 0 interview, 0 rejected → response rate 0%
    critiques = engine.critique(companies, apps, {"scores": {"ai": 100}})
    assert any("response rate" in c.message.lower() for c in critiques)


def test_impact_ranker_ai_first():
    ranker = ImpactRanker()
    p_good = make_profile()
    p_none = None
    c_good = make_company(id=1, name="AI Co", distance_km=2.0)
    c_bad = make_company(id=2, name="Far Co", distance_km=12.0)
    result = ranker.rank([c_good, c_bad], {1: p_good})
    assert result[0].company_name == "AI Co"
    assert result[0].verdict == "APPLY_NOW"


def test_blind_spot_detects_missing_certs():
    detector = BlindSpotDetector()
    cv = {"gemini_certified": True}
    drafts = {"PT X": "Halo PT X, saya Azka..."}
    spots = detector.detect(cv, [], drafts)
    assert any("Draft" in s.area for s in spots) or any("cert" in s.message.lower() for s in spots)


def test_channel_verdict():
    engine = ChannelVerdictEngine()
    wa_apps = [(make_app(sent_via="wa"), make_company())] * 2
    wa_replied = [(make_app(sent_via="wa", status="replied"), make_company())] * 3
    results = engine.verdict(wa_apps + wa_replied)
    assert len(results) == 1
    assert results[0].channel == "wa"
    assert results[0].response_rate >= 30
