"""Scan WhatsApp untuk kandidat shortlist yang belum punya kontak WA."""

from __future__ import annotations

from pkl_research import config
from pkl_research._compat import setup_utf8_io
from pkl_research.cli import _scan_website_profile
from pkl_research.cv import load_analysis
from pkl_research.db.connection import connect
from pkl_research.db.repositories import CompanyProfileRepository, CompanyRepository
from pkl_research.db.schema import apply_migrations
from pkl_research.scraper.browser import BrowserSession, human_delay
from pkl_research.scraper.website import is_real_website
from pkl_research.shortlist import build_shortlist


def main() -> None:
    setup_utf8_io()
    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    repo = CompanyRepository(conn)
    profile_repo = CompanyProfileRepository(conn)
    analysis = load_analysis(config.OUTPUT_DIR / "cv_analysis.json")
    if not analysis:
        print("cv_analysis.json belum ada")
        return
    plist = profile_repo.list_with_company()
    prof_by_id = {p.company_id: p for p, _ in plist}
    ai_by_id = {p.company_id: p.ai_focus for p, _ in plist}
    items = build_shortlist(repo.find(), analysis, ai_by_id=ai_by_id)
    targets = [
        c for c, _, _ in items
        if is_real_website(c.website)
        and not (prof_by_id.get(c.id) and prof_by_id[c.id].whatsapp)
    ]
    print(f"Akan discan ulang (tanpa WhatsApp): {len(targets)}", flush=True)
    with BrowserSession(config.USER_DATA_DIR, headless=True) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for i, c in enumerate(targets, start=1):
            summary = _scan_website_profile(page, c, profile_repo)
            print(f"[{i}/{len(targets)}] {c.name[:40]} ok={summary['ok']}", flush=True)
            human_delay(page, (2.0, 4.0))
    plist = profile_repo.list_with_company()
    has = sum(1 for p, _ in plist if p.whatsapp)
    print(f"Total profil dengan WhatsApp: {has}", flush=True)


if __name__ == "__main__":
    main()
