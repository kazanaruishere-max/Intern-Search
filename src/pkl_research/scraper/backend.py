"""Pilih backend browser: Camofox (opsional) atau Playwright (default)."""

from __future__ import annotations

from pkl_research import config
from pkl_research.scraper.browser import BrowserSession


def resolve_backend(requested: str = "auto") -> str:
    """
    Return 'playwright' atau 'camofox'.
    Camofox hanya dipakai kalau diminta dan CAMOFOX_API tersedia.
    """
    req = (requested or "auto").strip().lower()
    if req not in {"auto", "playwright", "camofox"}:
        raise ValueError(f"Backend tidak dikenal: {requested}")
    if req == "playwright":
        return "playwright"
    if req == "camofox":
        if not config.camofox_api():
            raise RuntimeError(
                "CAMOFOX_API belum diset. Isi di .env atau pakai --backend playwright."
            )
        return "camofox"
    # auto
    if config.camofox_api():
        return "camofox"
    return "playwright"


def open_browser_session(
    backend: str = "auto",
    headless: bool = False,
    timeout_ms: int = 20_000,
) -> BrowserSession:
    """
    Buka session browser.
    Camofox REST belum diintegrasikan di CLI ini (MCP-only di sesi agent);
    fallback ke Playwright selalu aman.
    """
    chosen = resolve_backend(backend)
    if chosen == "camofox":
        # ponytail: Camofox MCP tools available to the agent, not to this process.
        # Upgrade path: wire CAMOFOX_API REST client here when server is up.
        raise RuntimeError(
            "Camofox backend belum tersedia di proses CLI (MCP-only). "
            "Pakai --backend playwright, atau biarkan agent pakai Camofox MCP."
        )
    return BrowserSession(
        config.USER_DATA_DIR,
        headless=headless,
        timeout_ms=timeout_ms,
    )
