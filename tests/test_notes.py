from pkl_research.models import Company, CompanyProfile, Review
from pkl_research.notes import auto_notes, combine_note, review_evidence


def make_company(**kw):
    base = dict(place_id="p", name="PT Qwords", rating=4.5, review_count=157,
                address="Gedung Cyber 1, Jl. Kuningan Barat, Jakarta Selatan",
                distance_km=3.5, role_fit=["fullstack"], sector="swasta", id=1)
    base.update(kw)
    return Company(**base)


def make_profile(**kw):
    base = dict(company_id=1, core_focus="Web hosting dan AI automation",
                ai_focus=True, ai_subfields=["AI Agent / Automation"],
                career_page_found=True, emails=["info@qwords.com"])
    base.update(kw)
    return CompanyProfile(**base)


def make_reviews():
    return [
        Review(company_id=1, reviewer_name="A", reviewer_rating=5,
               review_text="SMK kami melaksanakan kunjungan industri ke perusahaan ini."),
        Review(company_id=1, reviewer_name="B", reviewer_rating=5,
               review_text="Timnya responsif dan membantu sekali."),
        Review(company_id=1, reviewer_name="C", reviewer_rating=4,
               review_text="Layanan baik."),
    ]


def test_review_evidence_pkl():
    hits = review_evidence(make_reviews(), ["kunjungan industri", "pkl", "magang"])
    assert len(hits) == 1
    assert "kunjungan industri" in hits[0].review_text


def test_auto_notes_include_key_signals():
    notes = auto_notes(make_company(), make_profile(), make_reviews())
    text = " | ".join(notes)
    assert "kunjungan industri" in text
    assert "gedung" in text.lower()
    assert "AI terdeteksi" in text
    assert "halaman karir" in text
    assert "Email kontak" in text
    assert "Jarak 3.5 km" in text


def test_auto_notes_no_ai_no_profile():
    c = make_company()
    notes = auto_notes(c, None, [])
    text = " | ".join(notes)
    assert "AI terdeteksi" not in text
    assert "Rating 4.5 dari 157 ulasan" in text


def test_combine_note_adds_manual():
    combined = combine_note(make_company(), make_profile(), make_reviews(),
                            "HR: Pak Budi")
    assert "Catatan kamu: HR: Pak Budi" in combined


def test_combine_note_empty_manual():
    combined = combine_note(make_company(), make_profile(), make_reviews(), None)
    assert "Catatan kamu" not in combined
