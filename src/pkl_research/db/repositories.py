"""Repository pattern untuk akses data (SQLite)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from pkl_research.models import Application, Company, CompanyProfile, Review, Vacancy, _loads

COMPANY_COLUMNS = [
    "place_id", "name", "category", "categories", "rating", "review_count",
    "rating_breakdown", "address", "district", "city", "postal_code",
    "latitude", "longitude", "in_jakarta", "distance_km", "role_fit", "is_it",
    "sector", "phone", "website", "email", "plus_code", "maps_url", "cid",
    "open_hours", "description", "price_range", "photos", "photo_count",
    "scraped_at", "enriched_at",
]

PROFILE_COLUMNS = [
    "company_id", "website_url", "site_title", "meta_description", "core_focus",
    "about_text", "services_text", "career_page_found", "career_url",
    "career_snippet", "ai_focus", "ai_subfields", "ai_keywords", "ai_evidence",
    "emails", "social", "linkedin_url", "linkedin_label", "whatsapp",
    "tech_stack", "keywords", "fetch_status", "fetched_at", "created_at",
    "updated_at",
]

VACANCY_COLUMNS = [
    "source", "source_id", "title", "company_name", "location", "remote",
    "employment_type", "salary_min", "salary_max", "currency", "description_text",
    "tags", "url", "posted_at", "first_seen", "last_seen", "status",
    "repost_count", "fit_score", "scraped_at",
]

APPLICATION_COLUMNS = [
    "company_id", "status", "applied_at", "sent_via", "contact_person",
    "contact_email", "contact_phone", "draft_message", "notes", "result_notes",
    "created_at", "updated_at",
]

APPLICATION_STATUSES = [
    "shortlisted", "applied", "replied", "interview", "accepted", "rejected", "on_hold",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(obj: object) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)


class CompanyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, company: Company) -> int:
        """Insert baru atau update berdasarkan place_id. Return id baris."""
        data = {
            "place_id": company.place_id,
            "name": company.name,
            "category": company.category,
            "categories": _json(company.categories),
            "rating": company.rating,
            "review_count": company.review_count,
            "rating_breakdown": _json(company.rating_breakdown),
            "address": company.address,
            "district": company.district,
            "city": company.city,
            "postal_code": company.postal_code,
            "latitude": company.latitude,
            "longitude": company.longitude,
            "in_jakarta": int(company.in_jakarta),
            "distance_km": company.distance_km,
            "role_fit": _json(company.role_fit),
            "is_it": int(company.is_it),
            "sector": company.sector or "unknown",
            "phone": company.phone,
            "website": company.website,
            "email": company.email,
            "plus_code": company.plus_code,
            "maps_url": company.maps_url,
            "cid": company.cid,
            "open_hours": _json(company.open_hours),
            "description": company.description,
            "price_range": company.price_range,
            "photos": _json(company.photos),
            "photo_count": company.photo_count,
            "scraped_at": company.scraped_at,
            "enriched_at": company.enriched_at,
        }
        columns = COMPANY_COLUMNS
        placeholders = ",".join(f":{c}" for c in columns)
        updates = ",".join(f"{c}=excluded.{c}" for c in columns if c != "place_id")
        row = self.conn.execute(
            f"""
            INSERT INTO companies ({','.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(place_id) DO UPDATE SET {updates}
            RETURNING id
            """,
            data,
        ).fetchone()
        self.conn.commit()
        return int(row["id"])

    def get_by_place_id(self, place_id: str) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE place_id = ?", (place_id,)
        ).fetchone()
        return Company.from_row(row) if row else None

    def get_by_name(self, name: str) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        return Company.from_row(row) if row else None

    def get(self, company_id: int) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        return Company.from_row(row) if row else None

    def find(
        self,
        status: str | None = None,
        min_rating: float | None = None,
        role: str | None = None,
        category: str | None = None,
        sector: str | None = None,
        sort: str = "rating",
    ) -> list[Company]:
        where: list[str] = []
        params: list[object] = []
        if status:
            where.append("a.status = ?")
            params.append(status)
        if min_rating is not None:
            where.append("c.rating >= ?")
            params.append(min_rating)
        if role:
            where.append("c.role_fit LIKE ?")
            params.append(f'%"{role}"%')
        if category:
            where.append("c.category LIKE ?")
            params.append(f"%{category}%")
        if sector:
            where.append("c.sector = ?")
            params.append(sector)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        order = {
            "rating": "c.rating DESC, c.distance_km ASC, c.review_count DESC",
            "distance": "c.distance_km ASC, c.rating DESC",
            "reviews": "c.review_count DESC, c.rating DESC",
            "name": "c.name ASC",
        }.get(sort, "c.rating DESC, c.distance_km ASC, c.review_count DESC")
        rows = self.conn.execute(
            f"""
            SELECT c.*, a.status AS app_status
            FROM companies c
            LEFT JOIN applications a ON a.company_id = c.id
            {clause}
            ORDER BY {order}
            """,
            params,
        ).fetchall()
        return [Company.from_row(row) for row in rows]

    def pending_enrichment(self) -> list[Company]:
        rows = self.conn.execute(
            "SELECT * FROM companies WHERE enriched_at IS NULL ORDER BY id"
        ).fetchall()
        return [Company.from_row(row) for row in rows]

    def it_candidates(self, min_rating: float = 4.5) -> list[Company]:
        """Kandidat IT yang belum di-enrich dan lolos rating + Jakarta."""
        rows = self.conn.execute(
            """
            SELECT * FROM companies
            WHERE enriched_at IS NULL
              AND is_it = 1
              AND in_jakarta = 1
              AND rating >= ?
            ORDER BY rating DESC, review_count DESC
            """,
            (min_rating,),
        ).fetchall()
        return [Company.from_row(row) for row in rows]

    def qualified(
        self,
        min_rating: float | None = None,
        min_reviews: int | None = None,
    ) -> list[Company]:
        """Shortlist qualified: rating & ulasan tinggi, IT, dalam Jakarta."""
        from pkl_research import config

        rating = config.TARGET_RATING if min_rating is None else min_rating
        reviews = config.TARGET_MIN_REVIEWS if min_reviews is None else min_reviews
        rows = self.conn.execute(
            """
            SELECT * FROM companies
            WHERE rating >= ? AND review_count >= ?
              AND in_jakarta = 1 AND is_it = 1
            ORDER BY rating DESC, review_count DESC, distance_km ASC
            """,
            (rating, reviews),
        ).fetchall()
        return [Company.from_row(row) for row in rows]

    def set_sector(self, company_id: int, sector: str) -> None:
        self.conn.execute(
            "UPDATE companies SET sector = ? WHERE id = ?", (sector, company_id)
        )
        self.conn.commit()

    def set_fit_score(self, company_id: int, fit_score: float | None) -> None:
        self.conn.execute(
            "UPDATE companies SET fit_score = ? WHERE id = ?", (fit_score, company_id)
        )
        self.conn.commit()

    def mark_enriched(self, company_id: int) -> None:
        self.conn.execute(
            "UPDATE companies SET enriched_at = ? WHERE id = ?",
            (_now(), company_id),
        )
        self.conn.commit()

    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) AS n FROM companies").fetchone()["n"]
        enriched = self.conn.execute(
            "SELECT COUNT(*) AS n FROM companies WHERE enriched_at IS NOT NULL"
        ).fetchone()["n"]
        avg_rating = self.conn.execute(
            "SELECT AVG(rating) AS r FROM companies WHERE rating IS NOT NULL"
        ).fetchone()["r"]
        by_status = {
            row["status"]: row["n"]
            for row in self.conn.execute(
                "SELECT a.status AS status, COUNT(*) AS n "
                "FROM applications a GROUP BY a.status"
            )
        }
        by_sector = {
            row["sector"]: row["n"]
            for row in self.conn.execute(
                "SELECT sector, COUNT(*) AS n FROM companies GROUP BY sector"
            )
        }
        return {
            "total": total,
            "enriched": enriched,
            "avg_rating": round(avg_rating, 2) if avg_rating else None,
            "by_status": by_status,
            "by_sector": by_sector,
        }


class ReviewRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert_batch(self, company_id: int, reviews: list[Review]) -> int:
        """Insert, skip duplikat. Return jumlah baris baru."""
        inserted = 0
        for review in reviews:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO reviews
                (company_id, reviewer_name, reviewer_rating, review_text,
                 review_date, helpful_count, language, translated_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    review.reviewer_name,
                    review.reviewer_rating,
                    review.review_text,
                    review.review_date,
                    review.helpful_count,
                    review.language,
                    review.translated_text,
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def list_by_company(self, company_id: int) -> list[Review]:
        rows = self.conn.execute(
            "SELECT * FROM reviews WHERE company_id = ? ORDER BY reviewer_rating DESC",
            (company_id,),
        ).fetchall()
        return [Review(**dict(row)) for row in rows]

    def count_for_company(self, company_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM reviews WHERE company_id = ?", (company_id,)
        ).fetchone()
        return int(row["n"])


class ApplicationRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_or_create(self, company_id: int) -> Application:
        row = self.conn.execute(
            "SELECT * FROM applications WHERE company_id = ?", (company_id,)
        ).fetchone()
        if row:
            return Application.from_row(row)
        self.conn.execute(
            """
            INSERT INTO applications (company_id, status, created_at, updated_at)
            VALUES (?, 'shortlisted', ?, ?)
            """,
            (company_id, _now(), _now()),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM applications WHERE company_id = ?", (company_id,)
        ).fetchone()
        return Application.from_row(row)

    def update(
        self, company_id: int, *, status: str | None = None, **fields: object
    ) -> Application:
        if status and status not in APPLICATION_STATUSES:
            raise ValueError(
                f"Status tidak valid: {status}. "
                f"Pilihan: {', '.join(APPLICATION_STATUSES)}"
            )
        sets = ["updated_at = :now"]
        params: dict[str, object] = {"company_id": company_id, "now": _now()}
        if status:
            sets.append("status = :status")
            params["status"] = status
        for key, value in fields.items():
            if key not in APPLICATION_COLUMNS:
                raise ValueError(f"Field tidak dikenal: {key}")
            sets.append(f"{key} = :{key}")
            params[key] = value
        self.conn.execute(
            f"UPDATE applications SET {', '.join(sets)} WHERE company_id = :company_id",
            params,
        )
        self.conn.commit()
        return self.get_or_create(company_id)

    def save_draft(self, company_id: int, draft: str) -> Application:
        return self.update(company_id, draft_message=draft)

    def list(self, status: str | None = None) -> list[tuple[Application, Company]]:
        clause = "WHERE a.status = ?" if status else ""
        params: tuple[object, ...] = (status,) if status else ()
        rows = self.conn.execute(
            f"""
            SELECT a.*, c.name AS company_name
            FROM applications a
            JOIN companies c ON c.id = a.company_id
            {clause}
            ORDER BY a.updated_at DESC
            """,
            params,
        ).fetchall()
        result: list[tuple[Application, Company]] = []
        for row in rows:
            data = dict(row)
            data.pop("company_name", None)
            company_id = data.pop("company_id")
            company = self.conn.execute(
                "SELECT * FROM companies WHERE id = ?", (company_id,)
            ).fetchone()
            result.append((Application(company_id=company_id, **data), Company.from_row(company)))
        return result


class CompanyProfileRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, profile: CompanyProfile) -> int:
        data = {
            "company_id": profile.company_id,
            "website_url": profile.website_url,
            "site_title": profile.site_title,
            "meta_description": profile.meta_description,
            "core_focus": profile.core_focus,
            "about_text": profile.about_text,
            "services_text": profile.services_text,
            "career_page_found": int(profile.career_page_found),
            "career_url": profile.career_url,
            "career_snippet": profile.career_snippet,
            "ai_focus": int(profile.ai_focus),
            "ai_subfields": _json(profile.ai_subfields),
            "ai_keywords": _json(profile.ai_keywords),
            "ai_evidence": _json(profile.ai_evidence),
            "emails": _json(profile.emails),
            "social": _json(profile.social),
            "linkedin_url": profile.linkedin_url,
            "linkedin_label": profile.linkedin_label,
            "whatsapp": profile.whatsapp,
            "tech_stack": _json(profile.tech_stack),
            "keywords": _json(profile.keywords),
            "fetch_status": profile.fetch_status,
            "fetched_at": profile.fetched_at,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
        columns = PROFILE_COLUMNS
        placeholders = ",".join(f":{c}" for c in columns)
        updates = ",".join(f"{c}=excluded.{c}" for c in columns if c != "company_id")
        row = self.conn.execute(
            f"""
            INSERT INTO company_profiles ({','.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(company_id) DO UPDATE SET {updates}
            RETURNING id
            """,
            data,
        ).fetchone()
        self.conn.commit()
        return int(row["id"])

    def get_by_company(self, company_id: int) -> CompanyProfile | None:
        row = self.conn.execute(
            "SELECT * FROM company_profiles WHERE company_id = ?", (company_id,)
        ).fetchone()
        return CompanyProfile.from_row(row) if row else None

    def list_with_company(self) -> list[tuple[CompanyProfile, Company]]:
        rows = self.conn.execute(
            """
            SELECT p.*, c.name AS company_name
            FROM company_profiles p
            JOIN companies c ON c.id = p.company_id
            ORDER BY p.ai_focus DESC, c.rating DESC, c.review_count DESC
            """
        ).fetchall()
        result: list[tuple[CompanyProfile, Company]] = []
        for row in rows:
            data = dict(row)
            data.pop("company_name", None)
            company_id = data.pop("company_id")
            for key in (
                "ai_subfields", "ai_keywords", "ai_evidence", "emails",
                "social", "tech_stack", "keywords",
            ):
                data[key] = _loads(data.pop(key)) or []
            data["career_page_found"] = bool(data["career_page_found"])
            data["ai_focus"] = bool(data["ai_focus"])
            company = self.conn.execute(
                "SELECT * FROM companies WHERE id = ?", (company_id,)
            ).fetchone()
            result.append(
                (CompanyProfile(company_id=company_id, **data), Company.from_row(company))
            )
        return result


class VacancyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, vac: Vacancy) -> int:
        """Insert new or update based on (source, source_id). Return row id."""
        existing = self.conn.execute(
            "SELECT id, posted_at, repost_count, first_seen FROM vacancies WHERE source = ? AND source_id = ?",
            (vac.source, vac.source_id)
        ).fetchone()

        now_str = _now()
        first_seen = vac.first_seen or now_str
        last_seen = vac.last_seen or now_str
        repost_count = vac.repost_count

        if existing:
            first_seen = existing["first_seen"] or first_seen
            if vac.posted_at and existing["posted_at"] and vac.posted_at != existing["posted_at"]:
                repost_count = (existing["repost_count"] or 0) + 1

        data = {
            "source": vac.source,
            "source_id": vac.source_id,
            "title": vac.title,
            "company_name": vac.company_name,
            "location": vac.location,
            "remote": int(vac.remote),
            "employment_type": vac.employment_type,
            "salary_min": vac.salary_min,
            "salary_max": vac.salary_max,
            "currency": vac.currency,
            "description_text": vac.description_text,
            "tags": _json(vac.tags),
            "url": vac.url,
            "posted_at": vac.posted_at,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "status": vac.status or "active",
            "repost_count": repost_count,
            "fit_score": vac.fit_score,
            "scraped_at": vac.scraped_at or now_str,
        }

        columns = VACANCY_COLUMNS
        placeholders = ",".join(f":{c}" for c in columns)
        updates = ",".join(f"{c}=excluded.{c}" for c in columns if c not in ("source", "source_id", "first_seen", "repost_count"))
        
        row = self.conn.execute(
            f"""
            INSERT INTO vacancies ({','.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(source, source_id) DO UPDATE SET {updates}, repost_count = :repost_count
            RETURNING id
            """,
            data,
        ).fetchone()
        self.conn.commit()
        return int(row["id"])

    def get(self, vacancy_id: int) -> Vacancy | None:
        row = self.conn.execute(
            "SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)
        ).fetchone()
        return Vacancy.from_row(row) if row else None

    def get_by_source(self, source: str, source_id: str) -> Vacancy | None:
        row = self.conn.execute(
            "SELECT * FROM vacancies WHERE source = ? AND source_id = ?", (source, source_id)
        ).fetchone()
        return Vacancy.from_row(row) if row else None

    def find(
        self,
        source: str | None = None,
        min_fit: float | None = None,
        remote_only: bool = False,
        status: str | None = "active",
        employment_type: str | None = None,
    ) -> list[Vacancy]:
        where: list[str] = []
        params: list[object] = []
        if source:
            where.append("source = ?")
            params.append(source)
        if min_fit is not None:
            where.append("fit_score >= ?")
            params.append(min_fit)
        if remote_only:
            where.append("remote = 1")
        if status:
            where.append("status = ?")
            params.append(status)
        if employment_type:
            where.append("employment_type = ?")
            params.append(employment_type)

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self.conn.execute(
            f"SELECT * FROM vacancies {clause} ORDER BY fit_score DESC, posted_at DESC",
            params,
        ).fetchall()
        return [Vacancy.from_row(row) for row in rows]

    def mark_expired(self, before_date: str) -> int:
        cur = self.conn.execute(
            "UPDATE vacancies SET status = 'expired' WHERE last_seen < ? AND status = 'active'",
            (before_date,),
        )
        self.conn.commit()
        return cur.rowcount

