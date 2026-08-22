"""MCP Server — expose Intern-Search tools ke Hermes/OpenClaw/Claude Code.

Run via stdio:
    uv run python -m pkl_research.mcp_server

Config di Claude Code / OpenCode / Hermes:
    {
      "mcpServers": {
        "intern-search": {
          "command": "uv",
          "args": ["run", "python", "-m", "pkl_research.mcp_server"],
          "cwd": "/path/to/intern-search"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp.server import MCPServer
from mcp.types import TextContent

from pkl_research._compat import setup_utf8_io

setup_utf8_io()

server = MCPServer(
    name="intern-search",
    version="0.2.0",
    instructions=(
        "Semi-autonomous intern/PKL search tool. "
        "Search companies by region/role, analyze CV fit, "
        "generate personalized application drafts, track status. "
        "Human-in-the-loop: never auto-sends applications."
    ),
)


def _connect():
    from pkl_research.db.connection import connect
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    return conn


def _get_repos():
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import (
        ApplicationRepository,
        CompanyProfileRepository,
        CompanyRepository,
        ReviewRepository,
    )
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    return (
        conn,
        CompanyRepository(conn),
        CompanyProfileRepository(conn),
        ReviewRepository(conn),
        ApplicationRepository(conn),
    )


@server.tool()
def search_internships(
    region: str = "ID-Jakarta",
    role: str = "ai",
    min_rating: float = 4.5,
) -> str:
    """Search internship opportunities by region, role, and minimum rating.

    Args:
        region: Region key (ID-Jakarta, SG) or custom.
        role: Role filter (ai, software, fullstack, game).
        min_rating: Minimum Google Maps rating (default 4.5).
    """
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import CompanyRepository
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    repo = CompanyRepository(conn)
    companies = repo.find(role=role, min_rating=min_rating, sort="rating")
    if not companies:
        return json.dumps({"message": "No companies found", "count": 0}, ensure_ascii=False)
    results = [
        {
            "name": c.name,
            "rating": c.rating,
            "reviews": c.review_count,
            "distance_km": c.distance_km,
            "role_fit": c.role_fit,
            "sector": c.sector,
            "website": c.website,
            "email": c.email,
            "maps_url": c.maps_url,
        }
        for c in companies[:20]
    ]
    return json.dumps(
        {"count": len(companies), "showing": len(results), "results": results},
        ensure_ascii=False,
    )


@server.tool()
def shortlist_companies(max_km: float = 15.0, min_fit: float = 70.0) -> str:
    """Get ranked shortlist of companies by CV fit, distance, and AI alignment.

    Args:
        max_km: Maximum distance from home (default 15 km).
        min_fit: Minimum CV fit score (default 70).
    """
    from pkl_research.cv import load_analysis
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import CompanyProfileRepository, CompanyRepository
    from pkl_research.db.schema import apply_migrations
    from pkl_research.shortlist import build_shortlist

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    analysis = load_analysis(config.OUTPUT_DIR / "cv_analysis.json")
    if not analysis:
        return json.dumps({"error": "Run cv analyze first"}, ensure_ascii=False)
    repo = CompanyRepository(conn)
    plist = CompanyProfileRepository(conn).list_with_company()
    ai_by_id = {p.company_id: p.ai_focus for p, _ in plist}
    items = build_shortlist(
        repo.find(), analysis, max_km=max_km, min_fit=min_fit, ai_by_id=ai_by_id
    )
    results = [
        {
            "name": c.name,
            "fit": f,
            "ai": a,
            "rating": c.rating,
            "reviews": c.review_count,
            "distance_km": c.distance_km,
            "email": (prof_by[c.id].emails[0] if c.id in prof_by and prof_by[c.id].emails else ""),
        }
        for c, f, a in items[:15]
    ]
    return json.dumps({"count": len(items), "top": results}, ensure_ascii=False)


@server.tool()
def generate_draft(company_name: str, variant: str = "formal") -> str:
    """Generate a personalized internship application draft for a specific company.

    Args:
        company_name: Name of the company (partial match OK).
        variant: Draft style — formal, casual, or short.
    """
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import CompanyProfileRepository, CompanyRepository, ReviewRepository
    from pkl_research.db.schema import apply_migrations
    from pkl_research.messaging import build_drafts

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    repo = CompanyRepository(conn)
    cands = [c for c in repo.find() if company_name.lower() in c.name.lower()]
    if not cands:
        return json.dumps({"error": f"'{company_name}' not found"}, ensure_ascii=False)
    c = cands[0]
    prof = CompanyProfileRepository(conn).get_by_company(c.id) if c.id else None
    reviews = ReviewRepository(conn).list_by_company(c.id) if c.id else []
    from pkl_research import config as cfg

    drafts = build_drafts(c, reviews, cfg.identity(), prof, _load_cv())
    return json.dumps({"company": c.name, "variant": variant, "draft": drafts.get(variant, "")}, ensure_ascii=False)


def _load_cv():
    from pkl_research import config
    from pkl_research.cv import load_analysis

    return load_analysis(config.OUTPUT_DIR / "cv_analysis.json")


@server.tool()
def analyze_cv(path: str) -> str:
    """Analyze a CV file (PDF/DOCX/TXT): 4-direction scores + ATS checklist.

    Args:
        path: File path to the CV.
    """
    from pkl_research import config
    from pkl_research.cv import analyze_cv, extract_text, save_analysis

    text = extract_text(path)
    result = analyze_cv(text)
    save_analysis(result, config.OUTPUT_DIR / "cv_analysis.json")
    return json.dumps(result, ensure_ascii=False)


@server.tool()
def get_company_profile(company_name: str) -> str:
    """Get full company profile: contact, AI detection, career page, WhatsApp.

    Args:
        company_name: Name of the company (partial match OK).
    """
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import CompanyProfileRepository, CompanyRepository
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    repo = CompanyRepository(conn)
    cands = [c for c in repo.find() if company_name.lower() in c.name.lower()]
    if not cands:
        return json.dumps({"error": f"'{company_name}' not found"}, ensure_ascii=False)
    c = cands[0]
    p = CompanyProfileRepository(conn).get_by_company(c.id) if c.id else None
    return json.dumps(
        {
            "name": c.name,
            "rating": c.rating,
            "reviews": c.review_count,
            "category": c.category,
            "address": c.address,
            "website": c.website,
            "email": (p.emails if p and p.emails else []),
            "whatsapp": p.whatsapp if p else None,
            "linkedin": p.linkedin_url if p else None,
            "ai_focus": p.ai_focus if p else False,
            "ai_subfields": p.ai_subfields if p else [],
            "career_page": p.career_url if p else None,
            "core_focus": p.core_focus if p else None,
        },
        ensure_ascii=False,
    )


@server.tool()
def update_status(company_name: str, status: str, note: str = "") -> str:
    """Update application status for a company.

    Args:
        company_name: Name of the company (partial match OK).
        status: One of shortlisted, applied, replied, interview, accepted, rejected, on_hold.
        note: Optional note.
    """
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import ApplicationRepository, CompanyRepository
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    cands = [c for c in CompanyRepository(conn).find() if company_name.lower() in c.name.lower()]
    if not cands:
        return json.dumps({"error": f"'{company_name}' not found"}, ensure_ascii=False)
    app = ApplicationRepository(conn)
    app.update(cands[0].id, status=status, notes=note)
    return json.dumps({"company": cands[0].name, "status": status}, ensure_ascii=False)


@server.tool()
def suggest_next_action() -> str:
    """Get AI-recommended next action: who to follow up, which channel, what to prioritize."""
    from pkl_research.db.connection import connect
    from pkl_research import config as cfg
    from pkl_research.db.repositories import ApplicationRepository, CompanyRepository
    from pkl_research.db.schema import apply_migrations

    conn = connect(cfg.DB_PATH)
    apply_migrations(conn)
    apps = ApplicationRepository(conn).list()
    applied = [(a, c) for a, c in apps if a.status == "applied"]
    rejected = [(a, c) for a, c in apps if a.status == "rejected"]
    interview = [(a, c) for a, c in apps if a.status == "interview"]
    shortlisted = [(a, c) for a, c in apps if a.status == "shortlisted"]

    suggestions = []
    if interview:
        suggestions.append(f"🎯 INTERVIEW: {interview[0][1].name} — prepare!")
    if rejected:
        reasons = [a.notes or "unknown" for a, _ in rejected[:3]]
        suggestions.append(f"❌ REJECTED ({len(rejected)}): {', '.join(r[:30] for r in reasons)} — avoid similar companies.")
    if applied:
        suggestions.append(f"⏳ APPLIED ({len(applied)}): follow up after 3 business days via WA.")
    if shortlisted:
        suggestions.append(f"📋 SHORTLISTED ({len(shortlisted)}): generate draft & send.")
    if not suggestions:
        suggestions.append("No applications yet. Run search + shortlist to get started.")

    stats = {
        "total_applied": len(applied),
        "total_rejected": len(rejected),
        "total_interview": len(interview),
        "total_shortlisted": len(shortlisted),
        "response_rate": f"{len(interview) + len(rejected)}/{len(applied)}" if applied else "0/0",
    }
    return json.dumps({"suggestions": suggestions, "stats": stats}, ensure_ascii=False)


@server.tool()
def get_stats() -> str:
    """Get summary statistics: total companies, enriched, per sector, per status."""
    from pkl_research.db.connection import connect
    from pkl_research.db.repositories import CompanyRepository
    from pkl_research.db.schema import apply_migrations

    conn = connect(config.DB_PATH)
    apply_migrations(conn)
    stats = CompanyRepository(conn).stats()
    return json.dumps(stats, ensure_ascii=False)


async def run() -> None:
    await server.run_stdio_async()


if __name__ == "__main__":
    setup_utf8_io()
    asyncio.run(run())
