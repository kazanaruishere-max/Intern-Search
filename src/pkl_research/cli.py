"""CLI utama pkl-research."""

from __future__ import annotations

import random
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pkl_research import config
from pkl_research.db.connection import connect
from pkl_research.db.repositories import (
    ApplicationRepository,
    CompanyProfileRepository,
    CompanyRepository,
    ReviewRepository,
)
from pkl_research.db.schema import apply_migrations
from pkl_research import cv as cvmod
from pkl_research.exporter import (
    companies_to_csv,
    companies_to_json,
    drafts_markdown,
    profiles_markdown,
    report_markdown,
    shortlist_markdown,
)
from pkl_research.filters import evaluate_candidate
from pkl_research.messaging import build_drafts
from pkl_research.models import Company, CompanyProfile, Review
from pkl_research.scraper.browser import BrowserSession, human_delay
from pkl_research.scraper.detail import apply_detail, scrape_detail
from pkl_research.scraper.reviews import open_reviews, parse_reviews, scroll_reviews
from pkl_research.scraper.search import collect_candidates
from pkl_research.scraper.website import is_real_website, phone_to_wa, scrape_website
from pkl_research.sector import classify_sector
from pkl_research.shortlist import build_shortlist
from pkl_research.notes import combine_note
from pkl_research.xlsx_export import export_shortlist_xlsx

console = Console(legacy_windows=False)

app = typer.Typer(help="PKL Research Tool — riset perusahaan IT Jakarta Selatan.")
db_app = typer.Typer(help="Manajemen database.")
track_app = typer.Typer(help="Tracker status lamaran PKL.")
cv_app = typer.Typer(help="Analisa CV & pencocokan arah/perusahaan.")
app.add_typer(db_app, name="db")
app.add_typer(track_app, name="track")
app.add_typer(cv_app, name="cv")


def _connect():
    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_company(conn, name: str) -> Company:
    repo = CompanyRepository(conn)
    company = repo.get_by_name(name)
    if company:
        return company
    matches = [c for c in repo.find() if name.lower() in c.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise typer.BadParameter(f"Perusahaan '{name}' tidak ditemukan di database.")
    raise typer.BadParameter(
        f"'{name}' ambigu. Cocok: {', '.join(c.name for c in matches[:5])}"
    )


def _load_cv_analysis() -> dict | None:
    return cvmod.load_analysis(config.OUTPUT_DIR / "cv_analysis.json")


def _apply_filters(company: Company) -> Company:
    """Hitung ulang flag filter, jarak, dan sektor untuk satu Company."""
    res = evaluate_candidate(
        rating=company.rating,
        review_count=company.review_count,
        address=company.address,
        latitude=company.latitude,
        longitude=company.longitude,
        categories=company.categories or ([company.category] if company.category else []),
        home=config.home_location(),
    )
    company.in_jakarta = res.in_jakarta
    company.distance_km = res.distance_km
    company.role_fit = res.role_fit
    company.is_it = res.is_it
    company.sector = classify_sector(company.name, company.category, company.website)
    return company


# ---------------------------------------------------------------------------
# db
# ---------------------------------------------------------------------------

@db_app.command("init")
def db_init() -> None:
    """Buat schema + jalankan migrasi (idempotent)."""
    conn = _connect()
    console.print(f"[green]Database siap:[/green] {config.DB_PATH}")


@db_app.command("list")
def db_list(
    status: str | None = typer.Option(None, help="Filter status aplikasi"),
    min_rating: float | None = typer.Option(None, help="Rating minimum"),
    min_reviews: int | None = typer.Option(None, help="Jumlah ulasan minimum"),
    role: str | None = typer.Option(None, help="Peran: ai|software|fullstack|game"),
    category: str | None = typer.Option(None, help="Filter kategori (LIKE)"),
    sector: str | None = typer.Option(None, help="swasta|negeri|bumn|unknown"),
    qualified: bool = typer.Option(False, "--qualified", help="Shortlist qualified (>=4.9, >=100 ulasan, IT, Jakarta)"),
    sort: str = typer.Option("rating", help="rating|distance|reviews|name"),
) -> None:
    """Tampilkan perusahaan di database dengan filter."""
    conn = _connect()
    repo = CompanyRepository(conn)
    if qualified:
        companies = repo.qualified(
            min_rating=min_rating, min_reviews=min_reviews
        )
    else:
        companies = repo.find(
            status=status, min_rating=min_rating, role=role,
            category=category, sector=sector, sort=sort,
        )
    apps = {app.company_id: app.status for app, _ in ApplicationRepository(conn).list()}
    table = Table(title=f"Perusahaan ({len(companies)})")
    for col in ("Nama", "Rating", "Ulasan", "Jarak", "Sektor", "Role", "Status"):
        table.add_column(col)
    for c in companies:
        table.add_row(
            c.name,
            f"{c.rating:g}" if c.rating else "-",
            str(c.review_count or "-"),
            f"{c.distance_km:.1f} km" if c.distance_km is not None else "-",
            c.sector or "-",
            ",".join(c.role_fit) or "-",
            apps.get(c.id, ""),
        )
    console.print(table)


@db_app.command("stats")
def db_stats() -> None:
    """Ringkasan data di database."""
    conn = _connect()
    stats = CompanyRepository(conn).stats()
    console.print(f"Total perusahaan : {stats['total']}")
    console.print(f"Sudah di-enrich  : {stats['enriched']}")
    console.print(f"Rata-rata rating : {stats['avg_rating']}")
    if stats.get("by_sector"):
        console.print("Per sektor:")
        for sector, n in stats["by_sector"].items():
            console.print(f"  - {sector}: {n}")
    if stats["by_status"]:
        console.print("Per status aplikasi:")
        for status, n in stats["by_status"].items():
            console.print(f"  - {status}: {n}")


# ---------------------------------------------------------------------------
# search / details
# ---------------------------------------------------------------------------

@app.command()
def search(
    headless: bool = typer.Option(False, "--headless", help="Jalankan tanpa jendela browser"),
) -> None:
    """Scan kandidat perusahaan IT di Jakarta Selatan → simpan ke DB."""
    conn = _connect()
    repo = CompanyRepository(conn)
    app_repo = ApplicationRepository(conn)
    home = config.home_location()
    if home is None:
        console.print(
            "[yellow]HOME_LAT/HOME_LON/MAX_DISTANCE_KM belum diset — "
            "filter jarak dari rumah dilewati. Set env untuk hasil terbaik.[/yellow]"
        )

    queries = [
        f"{q} {config.QUERY_SUFFIX}"
        for qs in config.QUERIES_BY_ROLE.values()
        for q in qs
    ]
    console.print(f"Menjalankan {len(queries)} query...")

    with BrowserSession(config.USER_DATA_DIR, headless=headless) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        candidates = collect_candidates(page, queries, config.CENTER_JAKSEL)

    added = passed = 0
    for c in candidates:
        c = _apply_filters(c)
        c.scraped_at = _now()
        c.categories = c.categories or ([c.category] if c.category else [])
        existing = repo.get_by_place_id(c.place_id)
        if existing is None:
            added += 1
        if c.in_jakarta and c.rating and c.review_count and c.rating >= config.MIN_RATING:
            passed += 1
        company_id = repo.upsert(c)
        app_repo.get_or_create(company_id)

    console.print(
        f"[green]Selesai.[/green] Kandidat unik: {len(candidates)} "
        f"(baru {added}), lolos filter Jakarta+rating: {passed}."
    )


@app.command()
def details(
    force: bool = typer.Option(False, "--force", help="Enrich ulang semua, abaikan yang sudah"),
    scope: str = typer.Option("it", "--scope", help="it|all — it: hanya kandidat IT rating>=4.5"),
    max_reviews: int = typer.Option(config.DEFAULT_MAX_REVIEWS, help="Maks review per perusahaan"),
    headless: bool = typer.Option(False, "--headless", help="Tanpa jendela browser"),
    limit: int | None = typer.Option(None, help="Batasi jumlah perusahaan (debug)"),
) -> None:
    """Enrich detail kandidat: kontak, foto, dan review."""
    conn = _connect()
    repo = CompanyRepository(conn)
    review_repo = ReviewRepository(conn)
    if scope == "it":
        companies = repo.it_candidates(config.MIN_RATING)
    elif scope == "all":
        companies = repo.find() if force else repo.pending_enrichment()
    else:
        raise typer.BadParameter("--scope harus 'it' atau 'all'")
    if limit:
        companies = companies[:limit]
    console.print(f"Perusahaan akan di-enrich: {len(companies)}")

    with BrowserSession(config.USER_DATA_DIR, headless=headless) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for idx, c in enumerate(companies, start=1):
            console.print(f"[{idx}/{len(companies)}] {c.name}...", end=" ")
            if not c.maps_url:
                console.print("[yellow]tanpa URL, dilewati[/yellow]")
                repo.mark_enriched(c.id)
                continue
            try:
                page.goto(c.maps_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_selector("h1.DUwDvf, h1", timeout=25000)
                page.wait_for_timeout(random.randint(2000, 3500))
            except Exception:
                console.print("[red]gagal load halaman[/red]")
                continue

            detail = scrape_detail(page)
            updated = apply_detail(c, detail)
            updated = _apply_filters(updated)
            updated.enriched_at = _now()
            company_id = repo.upsert(updated)

            reviews: list[Review] = []
            if open_reviews(page):
                scroll_reviews(page, target=max_reviews)
                parsed = parse_reviews(page, limit=max_reviews)
                for r in parsed:
                    r.company_id = company_id
                reviews = parsed
            review_repo.insert_batch(company_id, reviews)

            console.print(
                f"[green]ok[/green] | rating {updated.rating} | "
                f"{updated.review_count} ulasan | {len(reviews)} review diambil"
            )
            human_delay(page, config.BETWEEN_COMPANIES_DELAY_SEC)


def _scan_website_profile(page, company, profile_repo) -> dict[str, object]:
    """Scan 1 website perusahaan → upsert CompanyProfile. Return ringkasan log."""
    from pkl_research.ai_detect import detect_ai

    raw = scrape_website(page, company.website)  # type: ignore[arg-type]
    now = _now()
    if raw.get("fetch_status") != "ok":
        profile_repo.upsert(
            CompanyProfile(
                company_id=company.id,
                website_url=company.website,
                fetch_status="failed",
                fetched_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        return {"ok": False, "ai_label": "gagal", "focus": "-"}

    pages = raw.get("pages") or []
    texts = [
        str(raw.get("site_title") or ""),
        str(raw.get("meta_description") or ""),
        *(str(p) for p in pages),
    ]
    detection = detect_ai(texts)

    whatsapp = raw.get("whatsapp")
    if not whatsapp or "whatsapp.com/send" in str(whatsapp):
        wa_number = phone_to_wa(company.phone)
        if wa_number:
            whatsapp = wa_number
    profile_repo.upsert(
        CompanyProfile(
            company_id=company.id,
            website_url=company.website,
            site_title=raw.get("site_title"),
            meta_description=raw.get("meta_description"),
            core_focus=raw.get("core_focus"),
            about_text=raw.get("about_text"),
            services_text=raw.get("services_text"),
            career_page_found=bool(raw.get("career_page_found")),
            career_url=raw.get("career_url"),
            career_snippet=raw.get("career_snippet"),
            ai_focus=detection.ai_focus,
            ai_subfields=detection.subfields,
            ai_keywords=detection.keywords,
            ai_evidence=detection.evidence,
            emails=raw.get("emails"),
            social=raw.get("social"),
            linkedin_url=raw.get("linkedin") or None,
            linkedin_label=raw.get("linkedin_label") or None,
            whatsapp=whatsapp,
            fetch_status="ok",
            fetched_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    ai_label = ", ".join(detection.subfields) if detection.ai_focus else "tidak terdeteksi"
    return {
        "ok": True,
        "ai_label": ai_label,
        "focus": str(raw.get("core_focus") or "-")[:60],
    }


@app.command()
def profile(
    headless: bool = typer.Option(False, "--headless", help="Tanpa jendela browser"),
    force: bool = typer.Option(False, "--force", help="Scan ulang semua, abaikan yang sudah"),
    limit: int | None = typer.Option(None, help="Batasi jumlah (debug)"),
) -> None:
    """Kunjungi website perusahaan qualified → simpan profil (fokus, tentang, AI)."""
    conn = _connect()
    repo = CompanyRepository(conn)
    profile_repo = CompanyProfileRepository(conn)
    companies = repo.qualified()

    targets = [c for c in companies if is_real_website(c.website)]
    if not force:
        done = {
            p.company_id
            for p, _ in profile_repo.list_with_company()
            if p.fetch_status == "ok"
        }
        targets = [c for c in targets if c.id not in done]
    if limit:
        targets = targets[:limit]
    console.print(
        f"Qualified: {len(companies)} | website asli: {len([c for c in companies if is_real_website(c.website)])} "
        f"| akan discan: {len(targets)}"
    )

    with BrowserSession(config.USER_DATA_DIR, headless=headless) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for idx, c in enumerate(targets, start=1):
            console.print(f"[{idx}/{len(targets)}] {c.name}...", end=" ")
            summary = _scan_website_profile(page, c, profile_repo)
            if summary["ok"]:
                console.print(
                    f"[green]ok[/green] | AI: {summary['ai_label']} | fokus: {summary['focus']}"
                )
            else:
                console.print("[red]gagal load website[/red]")
            human_delay(page, (2.0, 4.0))


# ---------------------------------------------------------------------------
# shortlist
# ---------------------------------------------------------------------------

@app.command()
def shortlist(
    max_km: float = typer.Option(6.0, "--max-km", help="Jarak maksimal dari rumah"),
    min_fit: float = typer.Option(70.0, "--min-fit", help="Minimal fit score CV"),
    min_ulasan: int = typer.Option(10, "--min-ulasan", help="Minimal jumlah ulasan"),
    min_rating: float = typer.Option(4.5, "--min-rating", help="Minimal rating"),
    headless: bool = typer.Option(False, "--headless", help="Tanpa jendela browser"),
    scan_websites: bool = typer.Option(True, "--scan/--no-scan", help="Scan website kandidat"),
    force: bool = typer.Option(False, "--force", help="Scan ulang semua website"),
    top_drafts: int = typer.Option(10, "--top-drafts", help="Jumlah draft yang dibuat"),
) -> None:
    """Shortlist CV-match: IT + Jakarta Selatan + dekat rumah + fit CV → profil mendalam + draft."""
    analysis = _load_cv_analysis()
    if not analysis:
        raise typer.BadParameter(
            "Belum ada analisa CV. Jalankan dulu: pkl-research cv analyze <path>"
        )
    conn = _connect()
    repo = CompanyRepository(conn)
    profile_repo = CompanyProfileRepository(conn)
    review_repo = ReviewRepository(conn)

    companies = repo.find()
    ai_by_id = {p.company_id: p.ai_focus for p, _ in profile_repo.list_with_company()}
    items = build_shortlist(
        companies,
        analysis,
        max_km=max_km,
        min_fit=min_fit,
        min_ulasan=min_ulasan,
        min_rating=min_rating,
        ai_by_id=ai_by_id,
    )
    console.print(
        f"[bold]Shortlist: {len(items)} perusahaan[/bold] "
        f"(IT + Jakarta Selatan + ≤{max_km:g} km + fit ≥ {min_fit:g} + ulasan ≥ {min_ulasan})"
    )

    if scan_websites:
        done = {
            p.company_id
            for p, _ in profile_repo.list_with_company()
            if p.fetch_status == "ok"
        }
        targets = [
            c for c, _, _ in items
            if is_real_website(c.website) and (force or c.id not in done)
        ]
        console.print(f"Menscan website {len(targets)} kandidat...")
        with BrowserSession(config.USER_DATA_DIR, headless=headless) as ctx:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            for idx, c in enumerate(targets, start=1):
                console.print(f"[{idx}/{len(targets)}] {c.name}...", end=" ")
                summary = _scan_website_profile(page, c, profile_repo)
                if summary["ok"]:
                    console.print(
                        f"[green]ok[/green] | AI: {summary['ai_label']} | fokus: {summary['focus']}"
                    )
                else:
                    console.print("[red]gagal[/red]")
                human_delay(page, (2.0, 4.0))
        ai_by_id = {p.company_id: p.ai_focus for p, _ in profile_repo.list_with_company()}
        items = build_shortlist(
            companies, analysis, max_km=max_km, min_fit=min_fit,
            min_ulasan=min_ulasan, min_rating=min_rating, ai_by_id=ai_by_id,
        )

    profiles_by_id = {p.company_id: p for p, _ in profile_repo.list_with_company()}
    app_notes = {
        app.company_id: app.notes
        for app, _ in ApplicationRepository(conn).list()
    }
    app_status = {
        app.company_id: app.status
        for app, _ in ApplicationRepository(conn).list()
    }
    notes_by_id: dict[int, str] = {}
    for company, _, _ in items:
        profile = profiles_by_id.get(company.id)
        reviews = review_repo.list_by_company(company.id) if company.id else []
        notes_by_id[company.id] = combine_note(
            company, profile, reviews, app_notes.get(company.id)
        )

    table = Table(title=f"Shortlist ({len(items)})")
    for col in ("Nama", "Fit", "AI", "Rating", "Ulasan", "Jarak", "Role"):
        table.add_column(col)
    for company, fit, ai in items[:30]:
        table.add_row(
            company.name,
            f"{fit:g}",
            "[green]YA[/green]" if ai else "-",
            f"{company.rating:g}" if company.rating else "-",
            str(company.review_count or "-"),
            f"{company.distance_km:.1f} km" if company.distance_km is not None else "-",
            ",".join(company.role_fit) or "-",
        )
    console.print(table)

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shortlist_markdown(
        items,
        profiles_by_id,
        config.OUTPUT_DIR / "shortlist.md",
        notes_by_id,
        app_status,
    )

    identity = config.identity()
    drafts: dict[str, dict[str, str]] = {}
    for company, _, _ in items[:top_drafts]:
        reviews = review_repo.list_by_company(company.id) if company.id else []
        profile = profiles_by_id.get(company.id)
        drafts[company.name] = build_drafts(company, reviews, identity, profile, analysis)
    drafts_markdown(drafts, config.OUTPUT_DIR / "shortlist_drafts.md")
    export_shortlist_xlsx(
        items,
        profiles_by_id,
        drafts,
        config.OUTPUT_DIR / "shortlist.xlsx",
        notes_by_id,
        app_status,
    )

    console.print("[green]File dibuat:[/green]")
    console.print(f"  - {config.OUTPUT_DIR / 'shortlist.md'}")
    console.print(f"  - {config.OUTPUT_DIR / 'shortlist.xlsx'} (3 sheet berwarna)")
    console.print(f"  - {config.OUTPUT_DIR / 'shortlist_drafts.md'} ({len(drafts)} draft)")

    ai_items = [
        (c, f) for c, f, a in items
        if a or (profiles_by_id.get(c.id) and profiles_by_id[c.id].ai_focus)
    ]
    console.print("\n[bold]Rekomendasi teratas (AI-first):[/bold]")
    for company, fit in ai_items[:3]:
        console.print(
            f"  • [green][AI][/green] {company.name} — fit {fit:g}, "
            f"{company.review_count} ulasan, {company.distance_km:.1f} km"
        )
    for company, fit, _ in items[3:8]:
        console.print(
            f"  • {company.name} — fit {fit:g}, "
            f"{company.review_count} ulasan, {company.distance_km:.1f} km"
        )


# ---------------------------------------------------------------------------
# cv
# ---------------------------------------------------------------------------

@cv_app.command("analyze")
def cv_analyze(
    path: str = typer.Argument(..., help="Path file CV (PDF/DOCX/TXT)"),
) -> None:
    """Analisa CV: skor arah (software/AI/fullstack/game) + checklist ATS."""
    try:
        text = cvmod.extract_text(path)
    except Exception as exc:
        raise typer.BadParameter(f"Gagal membaca file CV: {exc}") from exc
    analysis = cvmod.analyze_cv(text)
    analysis_path = config.OUTPUT_DIR / "cv_analysis.json"
    cvmod.save_analysis(analysis, analysis_path)

    table = Table(title="Kecocokan Arah (0-100)")
    for col in ("Arah", "Skor", "Skill terdeteksi"):
        table.add_column(col)
    for direction, score in sorted(analysis["scores"].items(), key=lambda kv: -kv[1]):
        label = cvmod.ROLE_LABEL.get(direction, direction)
        table.add_row(label, str(score), ", ".join(analysis["skills"][direction][:10]))
    console.print(table)

    console.print("\n[bold]Rekomendasi:[/bold]")
    for s in analysis["strengths"]:
        console.print(f"  • {s}")
    if analysis["gaps"]:
        console.print("\n[bold]Gap yang perlu diisi:[/bold]")
        for g in analysis["gaps"]:
            console.print(f"  • {g}")

    console.print("\n[bold]Checklist ATS:[/bold]")
    for check in analysis["ats"]:
        mark = "[green]PASS[/green]" if check["ok"] else "[red]FAIL[/red]"
        note = f" — {check['note']}" if check["note"] else ""
        console.print(f"  {mark} {check['check']}{note}")

    console.print(f"\n[s cyan]Hasil tersimpan: {analysis_path}[/s cyan]")


@cv_app.command("match")
def cv_match(
    save: bool = typer.Option(True, "--save/--no-save", help="Simpan fit_score ke DB"),
    limit: int | None = typer.Option(None, help="Batasi jumlah hasil"),
    min_fit: float | None = typer.Option(None, help="Minimal fit score"),
) -> None:
    """Ranking perusahaan berdasarkan kecocokan dengan CV (perlu cv analyze dulu)."""
    analysis = cvmod.load_analysis(config.OUTPUT_DIR / "cv_analysis.json")
    if not analysis:
        raise typer.BadParameter(
            "Belum ada hasil analisa CV. Jalankan dulu: pkl-research cv analyze <path>"
        )
    conn = _connect()
    repo = CompanyRepository(conn)
    qualified = repo.qualified()
    qualified_ids = {c.id for c in qualified}
    companies = qualified + [
        c for c in repo.find() if c.is_it and c.id not in qualified_ids
    ]
    ranked = sorted(
        companies,
        key=lambda c: (
            cvmod.fit_for_roles(analysis, c.role_fit),
            c.rating or 0,
            c.review_count or 0,
        ),
        reverse=True,
    )
    if save:
        for c in ranked:
            repo.set_fit_score(c.id, cvmod.fit_for_roles(analysis, c.role_fit))

    table = Table(title=f"Perusahaan by Fit-CV ({len(ranked)})")
    for col in ("Nama", "Fit", "Rating", "Ulasan", "Jarak", "Role"):
        table.add_column(col)
    for c in ranked:
        fit = cvmod.fit_for_roles(analysis, c.role_fit)
        if min_fit and fit < min_fit:
            continue
        d = f"{c.distance_km:.1f} km" if c.distance_km is not None else "-"
        table.add_row(
            c.name,
            f"{fit:g}",
            f"{c.rating:g}" if c.rating else "-",
            str(c.review_count or "-"),
            d,
            ",".join(c.role_fit) or "-",
        )
    console.print(table)
    if limit:
        console.print(f"(menampilkan {limit} teratas — jalankan tanpa --limit untuk lengkap)")


# ---------------------------------------------------------------------------
# report / message
# ---------------------------------------------------------------------------

@app.command()
def report() -> None:
    """Generate laporan, CSV, draft pesan, dan profil website dari database."""
    conn = _connect()
    repo = CompanyRepository(conn)
    app_repo = ApplicationRepository(conn)
    review_repo = ReviewRepository(conn)
    profile_repo = CompanyProfileRepository(conn)

    companies = repo.find()
    qualified = repo.qualified()
    applications = [a for a, _ in app_repo.list()]
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    companies_to_csv(companies, config.OUTPUT_DIR / "companies.csv", applications)
    companies_to_json(companies, config.OUTPUT_DIR / "companies.json")
    report_markdown(companies, config.OUTPUT_DIR / "report.md", applications)
    profiles_markdown(
        profile_repo.list_with_company(),
        config.OUTPUT_DIR / "profiles.md",
    )

    identity = config.identity()
    cv_analysis = _load_cv_analysis()
    drafts: dict[str, dict[str, str]] = {}
    for c in companies:
        reviews = review_repo.list_by_company(c.id) if c.id else []
        if not reviews:
            continue
        profile = profile_repo.get_by_company(c.id) if c.id else None
        drafts[c.name] = build_drafts(c, reviews, identity, profile, cv_analysis)
    drafts_markdown(drafts, config.OUTPUT_DIR / "drafts.md")

    console.print("[green]Laporan dibuat di:[/green]")
    console.print(f"  - {config.OUTPUT_DIR / 'report.md'}")
    console.print(f"  - {config.OUTPUT_DIR / 'profiles.md'} (profil website)")
    console.print(f"  - {config.OUTPUT_DIR / 'companies.csv'}")
    console.print(f"  - {config.OUTPUT_DIR / 'companies.json'}")
    console.print(f"  - {config.OUTPUT_DIR / 'drafts.md'} ({len(drafts)} perusahaan)")
    console.print(f"Qualified shortlist: {len(qualified)} perusahaan")


@app.command()
def message(company: str = typer.Argument(..., help="Nama perusahaan")) -> None:
    """Generate draft pesan untuk satu perusahaan (simpan ke DB + stdout)."""
    conn = _connect()
    c = _resolve_company(conn, company)
    review_repo = ReviewRepository(conn)
    profile_repo = CompanyProfileRepository(conn)
    reviews = review_repo.list_by_company(c.id) if c.id else []
    profile = profile_repo.get_by_company(c.id) if c.id else None
    cv_analysis = _load_cv_analysis()
    drafts = build_drafts(c, reviews, config.identity(), profile, cv_analysis)
    for variant, text in drafts.items():
        console.print(Panel(text, title=f"{c.name} — {variant}", border_style="cyan"))
    ApplicationRepository(conn).save_draft(c.id, drafts["formal"])
    console.print(f"[green]Draft 'formal' disimpan ke tracker untuk {c.name}.[/green]")


# ---------------------------------------------------------------------------
# track
# ---------------------------------------------------------------------------

@track_app.command("update")
def track_update(
    company: str = typer.Argument(..., help="Nama perusahaan"),
    status: str = typer.Option("applied", "--status", help="Status PKL baru"),
    note: str | None = typer.Option(None, "--note", help="Catatan"),
    sent_via: str | None = typer.Option(None, "--sent-via", help="email/whatsapp/linkedin"),
    contact_email: str | None = typer.Option(None, "--contact-email", help="Email kontak HR"),
    applied_at: str | None = typer.Option(None, "--applied-at", help="Tanggal lamaran (YYYY-MM-DD)"),
) -> None:
    """Update status lamaran PKL untuk satu perusahaan."""
    conn = _connect()
    c = _resolve_company(conn, company)
    ApplicationRepository(conn).update(
        c.id,
        status=status,
        notes=note,
        sent_via=sent_via,
        contact_email=contact_email,
        applied_at=applied_at,
    )
    console.print(f"[green]{c.name}[/green] → status: {status}")


@track_app.command("list")
def track_list(
    status: str | None = typer.Option(None, "--status", help="Filter status"),
) -> None:
    """Daftar semua aplikasi PKL + status."""
    conn = _connect()
    rows = ApplicationRepository(conn).list(status)
    table = Table(title=f"Tracker Aplikasi PKL ({len(rows)})")
    for col in ("Perusahaan", "Status", "Via", "Diajukan", "Catatan"):
        table.add_column(col)
    for app, company in rows:
        table.add_row(
            company.name,
            app.status,
            app.sent_via or "-",
            app.applied_at or "-",
            (app.notes or "")[:40],
        )
    console.print(table)


def main() -> None:
    from pkl_research._compat import setup_utf8_io

    setup_utf8_io()
    app()
