import pytest

from pkl_research.db.connection import connect
from pkl_research.db.repositories import (
    ApplicationRepository,
    CompanyRepository,
    ReviewRepository,
)
from pkl_research.db.schema import apply_migrations
from pkl_research.models import Application, Company, Review


@pytest.fixture()
def conn(tmp_path):
    db = connect(tmp_path / "test.db")
    apply_migrations(db)
    yield db
    db.close()


def make_company(**overrides) -> Company:
    base = dict(
        place_id="ChIJ_test",
        name="PT Contoh Software",
        category="Software house",
        categories=["Software house"],
        rating=4.8,
        review_count=120,
        address="Jl. Senopati No. 8, Jakarta Selatan",
        latitude=-6.24,
        longitude=106.80,
        in_jakarta=True,
        role_fit=["software"],
        is_it=True,
        maps_url="https://maps.google.com/?cid=123",
    )
    base.update(overrides)
    return Company(**base)


def test_migrations_idempotent(conn):
    apply_migrations(conn)
    apply_migrations(conn)
    version = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()["v"]
    assert version == len(__import__("pkl_research.db.schema", fromlist=["MIGRATIONS"]).MIGRATIONS)


def test_company_upsert_dedupes_by_place_id(conn):
    repo = CompanyRepository(conn)
    c1 = make_company(rating=4.8)
    c2 = make_company(rating=4.9)
    id1 = repo.upsert(c1)
    id2 = repo.upsert(c2)
    assert id1 == id2
    fetched = repo.get_by_place_id("ChIJ_test")
    assert fetched.rating == 4.9
    assert repo.stats()["total"] == 1


def test_company_find_filters(conn):
    repo = CompanyRepository(conn)
    repo.upsert(make_company(place_id="p1", name="Alpha", rating=4.5))
    repo.upsert(make_company(place_id="p2", name="Beta", rating=5.0))
    repo.upsert(make_company(place_id="p3", name="Gamma", rating=3.0, role_fit=[]))

    high = repo.find(min_rating=4.5)
    assert [c.name for c in high] == ["Beta", "Alpha"]

    ai = repo.find(role="software")
    assert len(ai) == 2

    low = repo.find(min_rating=4.0)
    assert len(low) == 2


def test_review_insert_batch_dedupes(conn):
    repo = CompanyRepository(conn)
    reviews = ReviewRepository(conn)
    cid = repo.upsert(make_company())
    batch = [
        Review(company_id=cid, reviewer_name="A", reviewer_rating=5, review_text="Bagus"),
        Review(company_id=cid, reviewer_name="B", reviewer_rating=4, review_text="Oke"),
        Review(company_id=cid, reviewer_name="A", reviewer_rating=5, review_text="Bagus"),
    ]
    inserted = reviews.insert_batch(cid, batch)
    assert inserted == 2
    assert reviews.count_for_company(cid) == 2


def test_application_tracker_flow(conn):
    repo = CompanyRepository(conn)
    apps = ApplicationRepository(conn)
    cid = repo.upsert(make_company())

    app = apps.get_or_create(cid)
    assert app.status == "shortlisted"

    app = apps.update(cid, status="applied", notes="via email", sent_via="email")
    assert app.status == "applied"
    assert app.notes == "via email"

    with pytest.raises(ValueError):
        apps.update(cid, status="bukan-status")

    listed = apps.list(status="applied")
    assert len(listed) == 1
    assert listed[0][1].name == "PT Contoh Software"


def test_pending_enrichment(conn):
    repo = CompanyRepository(conn)
    cid = repo.upsert(make_company())
    assert len(repo.pending_enrichment()) == 1
    repo.mark_enriched(cid)
    assert repo.pending_enrichment() == []
    assert repo.stats()["enriched"] == 1
