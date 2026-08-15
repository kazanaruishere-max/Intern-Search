"""Konfigurasi global tool PKL Research."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
DB_PATH = DATA_DIR / "pkl.db"
USER_DATA_DIR = PROJECT_ROOT / "user_data"
PHOTOS_DIR = OUTPUT_DIR / "photos"


def _load_env_file() -> None:
    """Load file .env di root project (tanpa dependency eksternal)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_env_file()

JAKARTA_BBOX = {
    "lat_min": -6.364,
    "lat_max": -6.052,
    "lon_min": 106.685,
    "lon_max": 106.970,
}

CENTER_JAKSEL = {"lat": -6.24, "lng": 106.80, "zoom": 13}

MIN_RATING = 4.5
MIN_REVIEW_COUNT = 10

TARGET_RATING = 4.9
TARGET_MIN_REVIEWS = 100

SECTORS = ["swasta", "negeri", "bumn", "unknown"]

# Kategori Google Maps yang BUKAN perusahaan software development (di luar konteks PKL dev).
NON_DEV_CATEGORY_KEYWORDS = [
    "penjenamaan", "branding", "agensi desain", "desain grafis", "desain",
    "pemasaran", "marketing", "advertising", "iklan", "media promosi",
    "kursus", "pelatihan", "academy", "percetakan", "cetak", "printing",
    "logo", "fotografi", "event organizer", "humas", "public relations",
]
# Sinyal kategori yang TETAP dianggap dev (override NON_DEV).
DEV_CATEGORY_SIGNALS = [
    "software", "web", "aplikasi", "developer", "development", "programming",
    "teknologi", "it ", "pengembang", "sistem informasi",
]

DEFAULT_MAX_REVIEWS = 20
MAX_REVIEWS = 100
MAX_PHOTOS = 20

QUERY_SUFFIX = "jakarta selatan"

QUERIES_BY_ROLE: dict[str, list[str]] = {
    "software": [
        "software house",
        "perusahaan perangkat lunak",
        "software development",
        "it company",
    ],
    "ai": [
        "perusahaan AI",
        "artificial intelligence company",
        "AI startup",
        "machine learning company",
        "AI development",
        "ai developer",
        "ai company",
        "perusahaan kecerdasan buatan",
        "data science company",
        "computer vision company",
        "machine learning jakarta selatan",
        "chatbot company",
        "startup teknologi",
    ],
    "fullstack": [
        "web development",
        "perusahaan web",
        "pengembang aplikasi",
        "it consultant",
        "digital agency",
        "backend developer",
        "frontend developer",
        "fullstack agency",
        "jasa pembuatan website",
        "pembuatan aplikasi web",
        "web agency",
        "web design company",
    ],
    "game": [
        "game developer",
        "game studio",
        "perusahaan game",
        "game developer indonesia",
        "game publisher",
        "pembuat game",
        "studio game",
    ],
}

ROLE_KEYWORDS: dict[str, list[str]] = {
    "ai": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "kecerdasan buatan",
        "data science",
        "data analytics",
    ],
    "game": ["game", "gaming", "permainan"],
    "fullstack": [
        "web",
        "website",
        "digital",
        "front end",
        "backend",
        "pengembangan web",
    ],
    "software": [
        "software",
        "perangkat lunak",
        "aplikasi",
        "programmer",
        "development",
        "developer",
        "teknologi",
        "technology",
        "konsultan it",
        "it consultant",
        "consulting",
    ],
}

ROLE_LABEL_ID: dict[str, str] = {
    "ai": "AI / machine learning",
    "game": "game development",
    "fullstack": "fullstack / web development",
    "software": "software development",
}

SEARCH_ACTIONS_DELAY_SEC = (2.0, 6.0)
BETWEEN_COMPANIES_DELAY_SEC = (5.0, 10.0)
SCROLL_BATCH = 8


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def identity() -> dict[str, str]:
    """Identitas pemohon, dari env, untuk pengisian draft pesan."""
    return {
        "nama": env_str("NAMA", "[Nama Kamu]"),
        "sekolah": env_str("SEKOLAH", "[Sekolah/Kampus]"),
        "jurusan": env_str("JURUSAN", "[Jurusan]"),
        "durasi_pkl": env_str("DURASI_PKL", "[Durasi PKL, mis. 3 bulan]"),
        "email": env_str("EMAIL", ""),
        "telepon": env_str("TELEPON", ""),
    }


def home_location() -> dict[str, float] | None:
    """Koordinat rumah + jarak maksimum (env HOME_LAT/HOME_LON/MAX_DISTANCE_KM)."""
    lat = os.getenv("HOME_LAT")
    lon = os.getenv("HOME_LON")
    if not lat or not lon:
        return None
    try:
        return {
            "lat": float(lat),
            "lon": float(lon),
            "max_distance_km": float(os.getenv("MAX_DISTANCE_KM", "8.0")),
        }
    except ValueError:
        return None


def camofox_api() -> str | None:
    """URL REST API Camofox (opsional). Kosong = pakai Playwright."""
    return os.getenv("CAMOFOX_API", "").strip() or None
