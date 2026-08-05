from pkl_research import filters


def test_haversine_known_distance():
    # Rumah di Setiabudi (-6.20, 106.83) vs Blok M (-6.244, 106.798)
    d = filters.haversine_km(-6.20, 106.83, -6.244, 106.798)
    assert 5.5 < d < 6.5


def test_haversine_zero():
    assert filters.haversine_km(-6.24, 106.80, -6.24, 106.80) == 0.0


def test_in_bbox_inside():
    assert filters.in_jakarta_bbox(-6.24, 106.80) is True


def test_in_bbox_outside():
    assert filters.in_jakarta_bbox(-7.0, 110.0) is False
    assert filters.in_jakarta_bbox(None, None) is False


def test_address_has_jakarta():
    assert filters.address_has_jakarta("Jl. Senopati No.8, Jakarta Selatan") is True
    assert filters.address_has_jakarta("Jl. Sudirman No. 1, Bekasi") is False
    assert filters.address_has_jakarta(None) is False


def test_classify_role():
    assert "software" in filters.classify_role(["Perusahaan perangkat lunak"])
    assert "ai" in filters.classify_role(["AI company", "Startup"])
    assert "game" in filters.classify_role(["Game developer"])
    assert "fullstack" in filters.classify_role(["Web development agency"])
    assert filters.classify_role(["Toko roti"]) == []


def test_evaluate_pass():
    res = filters.evaluate_candidate(
        rating=4.8,
        review_count=120,
        address="Jl. Gatot Subroto, Jakarta Selatan",
        latitude=-6.24,
        longitude=106.80,
        categories=["Software house"],
        home={"lat": -6.20, "lon": 106.83, "max_distance_km": 5.0},
    )
    assert res.passes is True
    assert res.in_jakarta is True
    assert res.is_it is True
    assert res.distance_km is not None


def test_evaluate_low_rating_fails():
    res = filters.evaluate_candidate(
        rating=4.0,
        review_count=100,
        address="Jakarta Selatan",
        latitude=-6.24,
        longitude=106.80,
        categories=["Software house"],
    )
    assert res.passes is False
    assert any("rating" in r for r in res.reasons)


def test_evaluate_few_reviews_fails():
    res = filters.evaluate_candidate(
        rating=5.0,
        review_count=2,
        address="Jakarta Selatan",
        latitude=-6.24,
        longitude=106.80,
        categories=["Software house"],
    )
    assert res.passes is False


def test_evaluate_outside_jakarta_fails():
    res = filters.evaluate_candidate(
        rating=4.9,
        review_count=50,
        address="Jl. Raya Bekasi",
        latitude=-6.23,
        longitude=107.01,
        categories=["Software house"],
    )
    assert res.passes is False
    assert any("Jakarta" in r for r in res.reasons)


def test_evaluate_distance_computed():
    res = filters.evaluate_candidate(
        rating=4.9,
        review_count=50,
        address="Jakarta Selatan",
        latitude=-6.24,
        longitude=106.80,
        categories=["Software"],
        home={"lat": -6.24, "lon": 106.80, "max_distance_km": 3.0},
    )
    assert res.distance_km == 0.0
