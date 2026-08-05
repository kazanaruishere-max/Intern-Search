"""Schema & migrasi database SQLite."""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[str] = [
    # v1: tabel awal
    """
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT UNIQUE,
        name TEXT NOT NULL,
        category TEXT,
        categories TEXT,
        rating REAL,
        review_count INTEGER,
        rating_breakdown TEXT,
        address TEXT,
        district TEXT,
        city TEXT,
        postal_code TEXT,
        latitude REAL,
        longitude REAL,
        in_jakarta INTEGER DEFAULT 0,
        distance_km REAL,
        role_fit TEXT,
        is_it INTEGER DEFAULT 0,
        phone TEXT,
        website TEXT,
        email TEXT,
        plus_code TEXT,
        maps_url TEXT,
        cid TEXT,
        open_hours TEXT,
        description TEXT,
        price_range TEXT,
        photos TEXT,
        photo_count INTEGER DEFAULT 0,
        scraped_at TEXT,
        enriched_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_companies_rating ON companies (rating);
    CREATE INDEX IF NOT EXISTS idx_companies_place_id ON companies (place_id);

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        reviewer_name TEXT,
        reviewer_rating REAL,
        review_text TEXT,
        review_date TEXT,
        helpful_count INTEGER DEFAULT 0,
        language TEXT,
        translated_text TEXT,
        UNIQUE (company_id, reviewer_name, review_text)
    );
    CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews (company_id);

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'shortlisted',
        applied_at TEXT,
        sent_via TEXT,
        contact_person TEXT,
        contact_email TEXT,
        contact_phone TEXT,
        draft_message TEXT,
        notes TEXT,
        result_notes TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status);
    """,
    # v2: klasifikasi sektor + profil website perusahaan
    """
    ALTER TABLE companies ADD COLUMN sector TEXT NOT NULL DEFAULT 'unknown';

    CREATE TABLE IF NOT EXISTS company_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
        website_url TEXT,
        site_title TEXT,
        meta_description TEXT,
        core_focus TEXT,
        about_text TEXT,
        services_text TEXT,
        career_page_found INTEGER DEFAULT 0,
        career_url TEXT,
        career_snippet TEXT,
        ai_focus INTEGER DEFAULT 0,
        ai_subfields TEXT,
        ai_keywords TEXT,
        ai_evidence TEXT,
        emails TEXT,
        social TEXT,
        tech_stack TEXT,
        keywords TEXT,
        fetch_status TEXT NOT NULL DEFAULT 'pending',
        fetched_at TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_profiles_company ON company_profiles (company_id);
    """,
]


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Terapkan semua migrasi yang belum jalan, idempotent."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_version")}
    for version, script in enumerate(MIGRATIONS, start=1):
        if version in applied:
            continue
        conn.executescript(script)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    conn.commit()
