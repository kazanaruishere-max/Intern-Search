import pytest

from pkl_research.ai_detect import detect_ai
from pkl_research.db.connection import connect
from pkl_research.db.repositories import CompanyProfileRepository, CompanyRepository
from pkl_research.db.schema import apply_migrations
from pkl_research.models import Company, CompanyProfile
from pkl_research.scraper.website import is_real_website
from pkl_research.sector import classify_sector


# ---------- ai_detect ----------

def test_ai_false_positive_avoided():
    # "terbaik", "aplikasi", "baikt" mengandung huruf 'ai' tapi bukan AI
    det = detect_ai(["Kami membuat website terbaik untuk aplikasi pelanggan."])
    assert det.ai_focus is False


def test_ai_development_detected():
    det = detect_ai(["Kami fokus pada AI development dan machine learning."])
    assert det.ai_focus is True
    assert "AI Development" in det.subfields
    assert "Machine Learning" in det.subfields
    assert det.evidence


def test_ai_kecerdasan_buatan_detected():
    det = detect_ai(["Kami mengembangkan kecerdasan buatan untuk chatbot."])
    assert det.ai_focus is True
    assert "Artificial Intelligence" in det.subfields
    assert "Chatbot / Virtual Assistant" in det.subfields


def test_ai_llm_detected():
    det = detect_ai(["Solusi berbasis LLM dan generative AI."])
    assert det.ai_focus is True
    assert "LLM / Generative AI" in det.subfields


def test_ai_evidence_has_context():
    det = detect_ai(["x" * 100 + " kami punya machine learning internal " + "y" * 100])
    assert any("machine learning" in e for e in det.evidence)


# ---------- sector ----------

def test_sector_negeri_via_go_id():
    assert classify_sector("Dinas Komunikasi", "Instansi Pemerintah", "https://dki.go.id") == "negeri"
    assert classify_sector("PT Abadi", "Perusahaan Software", "https://diskominfo.jakarta.go.id") == "negeri"


def test_sector_negeri_via_name_word_boundary():
    assert classify_sector("Dinas Kominfo Provinsi DKI", "Kantor Pemerintah", None) == "negeri"
    # 'kedinasan' tidak boleh dianggap 'dinas'
    assert classify_sector("Bimbel Kedinasan Jaya", "Institusi Pendidikan", None) == "swasta"


def test_sector_bumn():
    assert classify_sector("PT Telkom Indonesia (Persero) Tbk", "Perusahaan", None) == "bumn"
    assert classify_sector("PT PLN", "Kantor Perusahaan", None) == "bumn"
    assert classify_sector("Bank Mandiri", "Bank", None) == "bumn"


def test_sector_swasta_default():
    assert classify_sector("PT Karya Digital", "Perusahaan Software", "https://karyadigital.com") == "swasta"
    assert classify_sector("", "", "") == "unknown"


# ---------- is_real_website ----------

def test_is_real_website():
    assert is_real_website("https://ukirama.com/") is True
    assert is_real_website("https://www.rubicweb.com/") is True


def test_is_real_website_skips_social():
    assert is_real_website("http://www.instagram.com/grouplay.id") is False
    assert is_real_website("http://wa.me/6285885048443") is False
    assert is_real_website("https://shope.ee/2AnrOdoDPW") is False
    assert is_real_website(None) is False
    assert is_real_website("") is False


# ---------- CompanyProfileRepository ----------

@pytest.fixture()
def conn(tmp_path):
    db = connect(tmp_path / "test.db")
    apply_migrations(db)
    yield db
    db.close()


def test_profile_upsert_and_get(conn):
    company_repo = CompanyRepository(conn)
    company_id = company_repo.upsert(
        Company(place_id="p1", name="PT A", category="Software", rating=5.0,
                review_count=150, in_jakarta=True, is_it=True)
    )
    profile_repo = CompanyProfileRepository(conn)
    profile = CompanyProfile(
        company_id=company_id,
        website_url="https://a.com",
        core_focus="ERP dan AI development",
        ai_focus=True,
        ai_subfields=["AI Development"],
        emails=["info@a.com"],
        fetch_status="ok",
    )
    profile_repo.upsert(profile)
    fetched = profile_repo.get_by_company(company_id)
    assert fetched is not None
    assert fetched.core_focus == "ERP dan AI development"
    assert fetched.ai_focus is True
    assert fetched.ai_subfields == ["AI Development"]
    assert fetched.emails == ["info@a.com"]

    # upsert kedua -> update, bukan duplikat
    profile.core_focus = "Diganti"
    profile_repo.upsert(profile)
    assert profile_repo.get_by_company(company_id).core_focus == "Diganti"
    assert len(profile_repo.list_with_company()) == 1
