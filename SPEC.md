# SPEC — Universal Intern Search (Global) + Camofox Mandatory

- **Status**: Draft — Waiting Review
- **Version**: v0.2.0-spec
- **Date**: 2026-08-10
- **Author**: pkl-research team + Azka
- **Related**: `PRD.md`, `docs/WORKFLOW.md`, `README.md`
- **Decisions Locked**: Global langsung, Sources: Glints + LinkedIn + others, Camofox WAJIB, Distance dipisah per-region

---

## 1. Problem

90% repositori GitHub `job-search` fokus ke lowongan kerja full-time. Tidak ada yang fokus **intern/PKL**:
- Periode fixed (contoh: Jan-Mar 2027), durasi 3 bulan, butuh surat sekolah, mentorship, konversi, WFA/hybrid
- Tool sekarang hanya Jabodetabek + Google Maps. Tidak global, tidak multi-source. Camofox masih opsional (fallback Playwright).

User sudah apply 7, 2 ditolak (tidak butuh PKL), 1 interview Buzzup — butuh **pool yang jauh lebih luas** dan bisa dipakai internasional.

## 2. Goals

1.  **Global**: Tool bisa dipakai di negara/kota manapun via `REGION` config, bukan hardcode Jaksel/Jabodetabek.
2.  **Universal Scraper**: Dapat data dari **semua tempat yang buka lowongan magang** — Google Maps, Glints, LinkedIn, JobStreet, Indeed, dan situs karir perusahaan. Sistem plugin agar komunitas bisa tambah sumber tanpa ubah core.
3.  **Camofox WAJIB**: Semua aktivitas browser lewat Camofox (anti-detect). Playwright dipertahankan hanya sebagai fallback emergency yang log warning keras, bukan mode normal.
4.  **Dipisah**: `MAX_DISTANCE_KM` tidak lagi global tunggal. Tiap region punya radius sendiri.
5.  **Tetap Semi-Auto**: Scrape → profile → CV-fit → draft (otomatis WFA jika >10km) → **human review & kirim**. TIDAK auto-apply.
6.  **Open Source Safe**: Upload hanya Tools, bukan `output/`, `data/`, `cv`, identitas.

## 3. Non-Goals (v0.2)

- Auto-apply / auto-submit lamaran
- Bypass login berbayar / captcha solving service komersial
- Scraping data pribadi pelamar lain
- UI Web Dashboard (tetap CLI dulu, sesuai request)

## 4. Personas

- **Azka (SMK Cybermedia, Grade 11)**: AI 100 / Fullstack 73, cari PKL Jan-Mar 2027. Domisili Cikoko, siap WFA >10km.
- **Mahasiswa Internasional (SG/MY/US)**: Cari intern 3-6 bulan, butuh filter visa/remote.

## 5. Functional Requirements

### 5.1 Region Global
- `config.REGIONS: dict[str, {lat, lng, zoom, bbox, max_km, lang}]`
  ```python
  REGIONS = {
      "ID-Jakarta": {"lat": -6.24, "lng": 106.80, "zoom": 13, "bbox": JABODETABEK_BBOX, "max_km": 15, "lang": "id"},
      "SG": {"lat": 1.3521, "lng": 103.8198, "zoom": 12, "bbox": {"lat_min": 1.15, "lat_max": 1.48, "lon_min": 103.60, "lon_max": 104.05}, "max_km": 20, "lang": "en"},
  }
  ```
  > Note: `QUERIES_BY_ROLE` akan diperluas dengan dimensi `lang` (ID vs EN) di **Phase C** (bukan Phase A); Phase A tetap pakai query ID existing (`magang`/`pkl` + `software/ai/fullstack/game`).
- CLI: `--region ID-Jakarta | SG | MY-KL | custom:lat,lng,radius`
- `.env`: `REGION=ID-Jakarta` + `WFA_KM=10` (global default, override per-region jika perlu)

### 5.2 Plugin System (Dipisah)
```
src/pkl_research/scraper/
├── backend.py          # resolve_backend() -> Camofox wajib
├── plugins/
│   ├── __init__.py     # BaseScraper ABC, registry
│   ├── base.py         # class BaseScraper(collect)
│   ├── maps.py         # Google Maps (pindahan search.py)
│   ├── glints.py       # Glints internship tag
│   ├── linkedin.py     # LinkedIn internships
│   ├── jobstreet.py    # JobStreet
│   ├── indeed.py       # Indeed
│   └── template.py     # Contoh untuk kontributor
└── browser.py / website.py (dipakai plugin)
```
Interface:
```python
class BaseScraper(ABC):
    source: str  # "glints"
    @abstractmethod
    def collect(self, page, query: str, region: dict) -> list[Company]: ...
    # Company.vacancy_open: bool, vacancy_url: str | None
```

CLI:
```bash
pkl-research search --source maps,glints,linkedin --region SG --backend camofox
pkl-research search --source all --region ID-Jakarta
```

### 5.3 Data Model Delta
- `companies`: + `vacancy_open INT DEFAULT 0`, `vacancy_url TEXT`, `region TEXT`, `source TEXT`, `source_id TEXT`; UNIQUE(`source`, `source_id`) + dedupe nama via `_norm_name()` lintas source
- Backfill (1156 rows existing): `region='ID-Jakarta'`, `source='maps'`, `source_id=COALESCE(place_id, 'maps:' || id)`, `vacancy_open=0`; handle `place_id IS NULL` via fallback `maps:<id>`
- `company_profiles`: `remote_policy`, `intern_period`, `stipend` sudah ditambah di v6 — v7 TIDAK menambah lagi (no collision)
- `applications`: `interview_date` sudah direncanakan

### 5.4 Camofox WAJIB (auto-fallback konsisten)
- `scraper/backend.py`: `resolve_backend("auto")` -> `camofox` jika `CAMOFOX_API` ada, else `playwright` + warning log (bukan ERROR) — menjaga 69 tests tetap hijau.
- `--backend camofox` eksplisit requires `CAMOFOX_API`; jika unset -> ERROR: `CAMOFOX_API belum diset. Isi di .env atau pakai --backend chrome|brave.`
- Playwright fallback hanya untuk `emergency` dengan flag `--backend playwright-emergency` + warning merah.
- `README.md`: Section atas `> Disarankan pakai Camofox Browser — jauh lebih optimal & maksimal. Wajib untuk Glints/LinkedIn.` + Tabel browser.

### 5.5 Filtering & Shortlist
- `shortlist.py`: `max_km` ambil dari `REGIONS[region].max_km` jika tidak di-override CLI.
- `shortlist --region SG --max-km 20` (pisah). `is_jakarta_selatan()` -> `is_in_region(lat,lng, region_bbox)`.
- `notes.py`: tag `WFA (>10km)` tetap, threshold `WFA_KM` per-region configurable.

### 5.6 Draft Internasional + WFA
- `messaging.py`: `_wfa_line()` sudah ada. Tambah `visa_line` jika `region != ID` dan `remote_policy == WFA`.
- `ROLE_LABEL_ID` i18n: `id: "AI / machine learning"` vs `en: "AI / Machine Learning"`.

## 6. Non-Functional

- **Anti-Block**: Camofox session human-like + delay acak + persistent `user_data/`. Rate limit per-source.
- **Legal**: Hanya scrape public listing. `README` + `SPEC` cantumkan ToS warning. `output/` tetap gitignored.
- **Performance**: `details --scope it` background, `shortlist --scan` resume-aware.
- **Quality**: `uv run pytest -q` hijau sebelum merge. `69 -> 72+` tests.

## 7. Security & Open Source

- `.gitignore`: `output/`, `data/`, `user_data/`, `.env`, `Azka*.docx`, `*.pdf` (sudah ada, perketat).
- `.env.example`: anonymized (tanpa HOME_LAT real, tanpa NAMA).
- `pre-commit` (opsional): cek secret sebelum push.

## 8. Migration Plan (v7 idempotent, no collision)

- v6 sudah menambah `remote_policy`, `intern_period`, `stipend` di `companies` + `company_profiles` — **v7 WAJIB TIDAK re-ADD kolom tersebut** (collision guard).
- `db/schema.py` v7 HANYA ADD: `vacancy_open INT DEFAULT 0`, `vacancy_url TEXT`, `region TEXT`, `source TEXT`, `source_id TEXT` ke `companies`; guard idempotent via `schema_version` (MIGRATIONS `enumerate(start=1)`, skip jika `version IN applied`), bukan `ADD COLUMN IF NOT EXISTS` (SQLite tidak support).
- `UNIQUE(source, source_id)` dibuat via `CREATE UNIQUE INDEX IF NOT EXISTS` (idempotent) setelah kolom ada.
- Backfill (1156 rows existing): `UPDATE companies SET region='ID-Jakarta', source='maps', source_id=COALESCE(place_id, 'maps:' || id), vacancy_open=0 WHERE source IS NULL`; handle `place_id IS NULL` via fallback `maps:<id>`.

## 9. Implementation Phases

**Phase A — Foundation (SPEC ini):**
- `config.REGIONS` + `WFA` per-region + `.env.example` + `backend.py` wajib Camofox + README update

**Phase B — Plugin Core:**
- `scraper/plugins/base.py` + `maps.py` (refactor existing) + `glints.py` POC

**Phase C — Expand Sources:**
- `linkedin.py`, `jobstreet.py`, `indeed.py` (reuse `website.py` pattern) + `template.py`

**Phase D — Intern Features:**
- `vacancy_open` filter `shortlist --with-vacancy`, draft WFA/visa, `xlsx_export` kolom `Vacancy`

**Phase E — Release:**
- Tag `v0.2.0-global`, `git push origin main`, demo GIF global

## 10. CLI Contract (Phased)

> **Phased, not breaking.** Perubahan flag bersifat *additive*. Flag yang sudah ada di `cli.py` (`--backend`, `--headless`, `--scope`, `--max-km`, `--no-scan`) **tetap ada dan tidak diubah** (Phase A). Flag `--source` dan `--region` adalah **flag BARU yang belum ada di `cli.py`** — akan ditambahkan di **Phase B** (bareng plugin system). Parser `custom:lat,lng,radius` juga **diimplementasikan di Phase B** (Phase A hanya support region key terdaftar seperti `ID-Jakarta`/`SG`).

```bash
# Setup
uv sync && uv run playwright install chromium  # Camofox tetap disarankan

# Search global  (--source & --region: NEW flag, Phase B)
uv run pkl-research search --source maps,glints --region SG --backend camofox --headless
uv run pkl-research search --source all --region custom:-6.2,106.8,15   # custom: parser = Phase B

# Enrich + Profile + Shortlist (region-aware)
uv run pkl-research details --scope it --region ID-Jakarta --headless   # --region: Phase B
uv run pkl-research shortlist --region SG --max-km 20 --no-scan           # --region: Phase B
```

> Catatan: Baris di atas adalah target kontrak akhir. Di **Phase A**, flag existing (`--backend camofox`, `--headless`, `--scope`, `--max-km`, `--no-scan`) sudah berfungsi; `--region`/`--source` menyusul di Phase B tanpa mem-break flag yang sudah ada.

## 11. Verification Gate

- [ ] `uv run pytest -q` 69 -> 72+ hijau (plugin + WFA + region)
- [ ] `search --region SG --source glints --backend camofox` smoke 1 page ok
- [ ] `shortlist --region ID-Jakarta` 100 rows (dedupe+is_non_dev); `search --region SG --source maps` smoke returns >=1 company (if 0, skip with log)
- [ ] `git ls-files` 0 file sensitif, `git push origin main` clean
- [ ] README Camofox section di atas

## 12. Open Questions (resolved)

- Q: Camofox MCP `fetch failed` saat ini -> A: CLI fallback Playwright sementara, SPEC wajibkan Camofox + docs `CAMOFOX_API`. Agent tetap bisa pakai Camofox MCP tools.
- Q: Game/web query sudah masuk config (36 query) -> A: Reuse, i18n-kan untuk global.

---
*Reviewer: Azka — Approve / Request Changes / Comments di bawah.*
