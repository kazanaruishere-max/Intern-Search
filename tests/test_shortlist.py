from pkl_research.cv import analyze_cv
from pkl_research.models import Company
from pkl_research.shortlist import build_shortlist, is_jakarta_selatan, is_non_dev, _norm_name

AI_CV = """
AI engineer focused on LLM tooling, machine learning, chatbots using Python, TensorFlow, ChromaDB, Gemini.
"""


def make_company(**kw):
    base = dict(
        place_id="p", name="PT X", category="Software house",
        rating=4.8, review_count=50, address="Jl. Senopati, Jakarta Selatan",
        latitude=-6.24, longitude=106.80, distance_km=3.0, is_it=True,
        role_fit=["software"], id=1,
    )
    base.update(kw)
    return Company(**base)


def test_is_jakarta_selatan():
    assert is_jakarta_selatan("Jl. Senopati, Jakarta Selatan", -6.24, 106.80) is True
    assert is_jakarta_selatan("Jl. Raya Tangerang", -6.20, 106.66) is False
    assert is_jakarta_selatan("Jakarta Pusat", -6.18, 106.82) is False
    assert is_jakarta_selatan("Tanpa alamat", -6.24, 106.80) is True  # bbox cocok


def test_build_shortlist_filters():
    analysis = analyze_cv(AI_CV)
    companies = [
        make_company(place_id="1", name="AI Match", role_fit=["ai"], rating=4.8,
                     review_count=50, distance_km=2.0, id=1),
        make_company(place_id="2", name="Jauh", role_fit=["software"], rating=4.9,
                     review_count=100, distance_km=9.0, id=2),
        make_company(place_id="3", name="Luar Jaksel", role_fit=["software"], rating=4.8,
                     review_count=50, address="Tangerang", latitude=-6.20, longitude=106.65,
                     distance_km=3.0, id=3),
        make_company(place_id="4", name="Review sedikit", role_fit=["ai"], rating=5.0,
                     review_count=3, distance_km=1.0, id=4),
        make_company(place_id="5", name="Non IT", role_fit=[], is_it=False, rating=5.0,
                     review_count=200, distance_km=1.0, id=5),
    ]
    result = build_shortlist(companies, analysis)
    names = [c.name for c, _, _ in result]
    assert "AI Match" in names
    assert "Jauh" not in names       # > 6km
    assert "Luar Jaksel" not in names  # bukan Jaksel
    assert "Review sedikit" not in names  # < 10 ulasan
    assert "Non IT" not in names


def test_ai_bonus_rank_first():
    analysis = analyze_cv(AI_CV)
    base = make_company(place_id="a", name="Tanpa AI", role_fit=["ai"],
                        rating=4.8, review_count=100, distance_km=2.0, id=10)
    ai_company = make_company(place_id="b", name="Dengan AI", role_fit=["ai"],
                              rating=4.8, review_count=90, distance_km=2.0, id=11)
    result = build_shortlist([base, ai_company], analysis, ai_by_id={11: True})
    assert len(result) == 2
    assert result[0][0].name == "Dengan AI"


def test_is_non_dev_drops_design_and_keeps_software():
    assert is_non_dev("Milestone", "Agensi penjenamaan") is True
    assert is_non_dev("Jaya Cetak Digital", "Layanan cetak digital") is True
    assert is_non_dev("ITSTEP ACADEMY", "Kursus Komputer") is True
    assert is_non_dev("PT Software Maju", "Perusahaan Software") is False
    assert is_non_dev("Nectar", "Jasa pembuatan website") is False
    assert is_non_dev("Think Web", "Desain Situs Web") is False  # sinyal "web"


def test_build_shortlist_excludes_non_dev():
    analysis = analyze_cv(AI_CV)
    companies = [
        make_company(place_id="1", name="Design Agency X", category="Agensi desain",
                     role_fit=["ai"], rating=4.9, review_count=50, distance_km=3.0, id=1),
        make_company(place_id="2", name="Software House Y", category="Perusahaan Software",
                     role_fit=["ai"], rating=4.8, review_count=50, distance_km=3.0, id=2),
    ]
    result = build_shortlist(companies, analysis)
    assert [c.name for c, _, _ in result] == ["Software House Y"]


def test_dedupe_by_name_keeps_best():
    analysis = analyze_cv(AI_CV)
    enriched = make_company(place_id="a", name="PT Qwords Indonesia", category="Software",
                            role_fit=["ai"], rating=4.5, review_count=157, distance_km=3.5, id=1)
    enriched.enriched_at = "2026-08-01"
    dup = make_company(place_id="b", name="Qwords", category="Software",
                       role_fit=["ai"], rating=4.5, review_count=5, distance_km=3.5, id=2)
    result = build_shortlist([dup, enriched], analysis)
    assert len(result) == 1
    assert result[0][0].id == 1


def test_norm_name():
    assert _norm_name("PT Qwords Company International") == _norm_name("Qwords Company")
