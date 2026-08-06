# WORKFLOW — PKL Research Tool

Panduan operasional penggunaan tool. Dokumen pelengkap dari `../PRD.md`.

## Prinsip Utama

Tool bersifat **semi-otomatis (human-in-the-loop)**:
- Otomatis: riset, filter, enrichment, drafting.
- Manual: **memilih kandidat**, **mengedit & mengirim** draft, **mencatat status** lamaran.
- Tool **tidak pernah mengirim apa pun** — tidak ada jalur pengiriman otomatis.

## 1. Workflow Runtime (pemakaian sehari-hari)

```
┌────────────────────────────────────────────────────────────┐
│ 1. SETUP (sekali)                                          │
│    • uv sync && uv run playwright install chromium         │
│    • Set env identitas: NAMA, SEKOLAH, JURUSAN, DURASI_PKL │
│    • Set env lokasi: HOME_LAT, HOME_LON, MAX_DISTANCE_KM   │
│        (koordinat rumah + jarak maks, contoh: 2.5)         │
│    • pkl-research db init            ← buat schema SQLite  │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 2. RISET OTOMATIS                                          │
│    pkl-research search        → scan query per fokus peran │
│        │                        (software/ai/fullstack/game)│
│        │                        filter rating≥4.5, in Jakarta│
│        │                        + jarak ≤ MAX_DISTANCE_KM   │
│        │                        dari rumah (HOME_LAT/LON)   │
│        │                        tag role_fit → DB           │
│        ▼                        upsert → DB (status scraped)│
│    pkl-research details       → enrich review + foto +     │
│                                  kontak (resume-aware)     │
└────────────────────────────────────────────────────────────┘
                            ▼
            ⚠️ DECISION GATE 1 — LO REVIEW KANDIDAT
            (pkl-research db list --sort rating)
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 3. DRAFTING                                                │
│    pkl-research message <nama>  → draft 3 varian, simpan DB│
│                                                             │
│    ⚠️ DECISION GATE 2 — LO EDIT DRAFT, PILIH YANG DIPAKAI  │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 4. KIRIM MANUAL (DI LUAR TOOL — oleh user, bukan agent)    │
│    Email/WA/LinkedIn, apa pun yang dipilih                 │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 5. TRACK (manual update)                                   │
│    pkl-research track update <nama> --status applied       │
│        ... --status replied / interview / accepted / rejected
│    pkl-research track list      → semua status aplikasi    │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 6. LAPORAN                                                 │
│    pkl-research report  → report.md + companies.csv +      │
│                           drafts.md (export dari DB)       │
│    Re-run kapan saja: upsert by place_id, tidak duplikat   │
└────────────────────────────────────────────────────────────┘
```

### Status PKL yang didukung
`shortlisted` (default) / `applied` / `replied` / `interview` / `accepted` / `rejected` / `on_hold`

## 2. Workflow Implementasi (urutan build)

1. `uv init` + dependensi + `uv run playwright install chromium`
2. `models.py` + `config.py` + `db/` (schema + migrasi + repositories) → unit test repo
3. `filters.py` → unit test
4. `scraper/`:
   - `browser.py` → `search.py` → smoke test live
   - `detail.py` → `reviews.py` → smoke test live
5. `messaging.py` + `exporter.py` → unit test
6. `cli.py` (8 subcommand) + checkpoint/resume
7. Run end-to-end → verifikasi (DB + report + draft) → README → git

## 3. Referensi Cepat Perintah

| Subcommand | Fungsi |
|---|---|
| `pkl-research db init` | Buat schema + jalankan migrasi (idempotent) |
| `pkl-research search` | Scan & filter kandidat → upsert ke DB |
| `pkl-research details [--force]` | Enrich review + foto + kontak |
| `pkl-research profile [--force]` | Scan website qualified → profil + deteksi AI |
| `pkl-research cv analyze "<path>"` | Analisa CV → skor 4 arah + ATS checklist |
| `pkl-research cv match` | Ranking perusahaan by fit-CV → simpan `fit_score` |
| `pkl-research report` | Export laporan dari DB |
| `pkl-research message <nama>` | Generate 1 draft → simpan DB + stdout |
| `pkl-research db list [--qualified] [--min-rating] [--min-reviews] [--role] [--category] [--sector] [--sort]` | Query DB |
| `pkl-research db stats` | Ringkasan data |
| `pkl-research track update <nama> --status <s> [--note ...]` | Update status PKL |
| `pkl-research track list` | Semua aplikasi + status |
