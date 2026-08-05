from pkl_research.messaging import build_drafts, review_highlights, theme_counts
from pkl_research.models import Company, Review


def make_reviews():
    return [
        Review(company_id=1, reviewer_name="A", reviewer_rating=5,
               review_text="Timnya sangat profesional dan responsif. Rekomendasi banget!"),
        Review(company_id=1, reviewer_name="B", reviewer_rating=4,
               review_text="Pelayanan ramah dan hasilnya sesuai permintaan."),
        Review(company_id=1, reviewer_name="C", reviewer_rating=2,
               review_text="Lama responsnya, kurang memuaskan."),
    ]


def make_company():
    return Company(
        place_id="p1", name="PT Karya Digital", category="Software house",
        rating=4.8, review_count=120, address="Jl. Sudirman, Jakarta Selatan",
        role_fit=["software", "fullstack"], distance_km=2.5,
    )


def test_review_highlights_only_positive():
    highlights = review_highlights(make_reviews(), limit=2)
    assert len(highlights) == 2
    assert "profesional" in highlights[0]


def test_theme_counts():
    themes = theme_counts(make_reviews())
    assert any("responsif" in t for t in themes)
    assert any("profesional" in t for t in themes)


def test_build_drafts_all_variants():
    identity = {
        "nama": "Budi", "sekolah": "SMK N 1 Jakarta", "jurusan": "RPL",
        "durasi_pkl": "3 bulan", "email": "budi@mail.com", "telepon": "",
    }
    drafts = build_drafts(make_company(), make_reviews(), identity)
    assert set(drafts) == {"formal", "casual", "short"}
    for text in drafts.values():
        assert "PT Karya Digital" in text
        assert "Budi" in text
        assert "4.8" in text
        assert "120" in text


def test_build_drafts_empty_reviews():
    identity = {
        "nama": "Budi", "sekolah": "SMK", "jurusan": "RPL",
        "durasi_pkl": "3 bulan", "email": "", "telepon": "",
    }
    drafts = build_drafts(make_company(), [], identity)
    assert "reputasi baik" in drafts["formal"]


def test_role_text():
    from pkl_research.messaging import role_text

    assert "AI" in role_text(["ai"])
    assert "fullstack" in role_text(["fullstack", "game"])
    assert "bidang IT" in role_text([])
