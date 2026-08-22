"""Klasifikasi sektor perusahaan: swasta / negeri / bumn / unknown."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_NEGERI_NAME_RE = re.compile(
    r"\b(pemerintah|kementerian|dinas|pemprov|pemkot|pemkab|instansi"
    r"|ministry|government agency|government department)\b",
    re.IGNORECASE,
)
_NEGERI_CATEGORY_RE = re.compile(
    r"(instansi pemerintah|lembaga pemerintah|kantor pemerintahan|pemerintah"
    r"|government agency|government office)",
    re.IGNORECASE,
)
_BUMN_PATTERNS = [
    r"\(persero\)",
    r"\bbumn\b",
    r"\bbadan usaha milik negara\b",
    r"^\s*(?:pt\s+)?(?:telkom|pln|pertamina|peruri|pindad|angkasa pura|pelni|"
    r"pos indonesia|pupuk|garuda indonesia|biofarma|kimia farma|bank mandiri|"
    r"bank negara indonesia|bank rakyat indonesia|bank tabungan negara|jasa marga|"
    r"jasa raharja|damri|kereta api indonesia|wijaya karya|adhi karya|"
    r"hutama karya|waskita|semen indonesia|timah|aneka tambang|antam|"
    r"pengembangan pariwisata|telkomsel|indosat)\b",
]
_BUMN_RE = re.compile("|".join(_BUMN_PATTERNS), re.IGNORECASE)


def _hostname(url: str | None) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def classify_sector(
    name: str | None,
    category: str | None,
    website: str | None,
) -> str:
    """Klasifikasi sektor berdasarkan nama, kategori, dan website."""
    name = (name or "").strip()
    category = (category or "").strip()
    host = _hostname(website)

    if host.endswith(".go.id") or _NEGERI_CATEGORY_RE.search(category):
        return "negeri"
    if _NEGERI_NAME_RE.search(name):
        return "negeri"
    if _BUMN_RE.search(name) or _BUMN_RE.search(category):
        return "bumn"
    if name or category or host:
        return "swasta"
    return "unknown"
