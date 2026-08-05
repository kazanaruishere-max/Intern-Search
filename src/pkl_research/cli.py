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
    CompanyRepository,
    ReviewRepository,
)
from pkl_research.db.schema import apply_migrations
from pkl_research.exporter import (
    companies_to_csv,
    companies_to_json,
    drafts_markdown,
    report_markdown,
)
from pkl_research.filters import evaluate_candidate
from pkl_research.messaging import build_drafts
from pkl_research.models import Company, Review
from pkl_research.scraper.browser import BrowserSession, human_delay
from pkl_research.scraper.detail import apply_detail, scrape_detail
from pkl_research.scraper.reviews import open_reviews, parse_reviews, scroll_reviews
from pkl_research.scraper.search import collect_candidates

console = Console(legacy_windows=False)

app = typer.Typer(help="PKL Research Tool — riset perusahaan IT Jakarta Selatan.")
db_app = typer.Typer(help="Manajemen database.")
track_app = typer.Typer(help="Tracker status lamaran PKL.")
app.add_typer(db_app, name="db")
app.add_typer(track_app, name="track")


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


def _apply_filters(company: Company) -> Company:
    """Hitung ulang flag filter & jarak untuk satu Company."""
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
    role: str | None = typer.Option(None, help="Peran: ai|software|fullstack|game"),
    category: str | None = typer.Option(None, help="Filter kategori (LIKE)"),
    sort: str = typer.Option("rating", help="rating|distance|reviews|name"),
) -> None:
    """Tampilkan perusahaan di database dengan filter."""
    conn = _connect()
    companies = CompanyRepository(conn).find(
        status=status, min_rating=min_rating, role=role,
        category=category, sort=sort,
    )
    apps = {app.company_id: app.status for app, _ in ApplicationRepository(conn).list()}
    table = Table(title=f"Perusahaan ({len(companies)})")
    for col in ("Nama", "Rating", "Ulasan", "Jarak", "Role", "Status"):
        table.add_column(col)
    for c in companies:
        table.add_row(
            c.name,
            f"{c.rating:g}" if c.rating else "-",
            str(c.review_count or "-"),
            f"{c.distance_km:.1f} km" if c.distance_km is not None else "-",
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


# ---------------------------------------------------------------------------
# report / message
# ---------------------------------------------------------------------------

@app.command()
def report() -> None:
    """Generate laporan, CSV, dan draft pesan dari database."""
    conn = _connect()
    repo = CompanyRepository(conn)
    app_repo = ApplicationRepository(conn)
    review_repo = ReviewRepository(conn)

    companies = repo.find()
    applications = [a for a, _ in app_repo.list()]
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    companies_to_csv(companies, config.OUTPUT_DIR / "companies.csv", applications)
    companies_to_json(companies, config.OUTPUT_DIR / "companies.json")
    report_markdown(companies, config.OUTPUT_DIR / "report.md", applications)

    identity = config.identity()
    drafts: dict[str, dict[str, str]] = {}
    for c in companies:
        reviews = review_repo.list_by_company(c.id) if c.id else []
        if not reviews:
            continue
        drafts[c.name] = build_drafts(c, reviews, identity)
    drafts_markdown(drafts, config.OUTPUT_DIR / "drafts.md")

    console.print("[green]Laporan dibuat di:[/green]")
    console.print(f"  - {config.OUTPUT_DIR / 'report.md'}")
    console.print(f"  - {config.OUTPUT_DIR / 'companies.csv'}")
    console.print(f"  - {config.OUTPUT_DIR / 'companies.json'}")
    console.print(f"  - {config.OUTPUT_DIR / 'drafts.md'} ({len(drafts)} perusahaan)")


@app.command()
def message(company: str = typer.Argument(..., help="Nama perusahaan")) -> None:
    """Generate draft pesan untuk satu perusahaan (simpan ke DB + stdout)."""
    conn = _connect()
    c = _resolve_company(conn, company)
    review_repo = ReviewRepository(conn)
    reviews = review_repo.list_by_company(c.id) if c.id else []
    drafts = build_drafts(c, reviews, config.identity())
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
