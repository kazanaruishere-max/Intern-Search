# Intern-Search

> Semi-autonomous intern/PKL search tool dengan CV-fit scoring, multi-source scraping (Google Maps / Glints / LinkedIn), auto-draft WFA untuk kandidat >10 km, dan prinsip **human-in-the-loop**.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![CLI](https://img.shields.io/badge/interface-CLI-informational)

Intern-Search adalah tool CLI semi-otomatis untuk riset lowongan PKL/magang IT: scraping kandidat dari beberapa sumber, filtering otomatis, analisa kecocokan CV, hingga generate draft pesan lamaran yang dipersonalisasi. Tool **tidak pernah mengirim lamaran sendiri** — kamu yang memilih, mengedit, dan mengirim manual.

---

## Kenapa Intern-Search?

90% repositori `job-search` di GitHub fokus ke lowongan full-time. Kebutuhan intern/PKL sangat berbeda:

| Kebutuhan PKL/Intern | Repositori job-search biasa | Intern-Search |
|---|---|---|
| Periode fixed (mis. Jan–Mar, durasi 3 bulan) | ❌ Tidak ada | ✅ Terintegrasi di draft (`DURASI_PKL`) |
| Butuh surat sekolah & mentorship | ❌ Tidak relevan | ✅ Diperhitungkan dalam konteks lamaran |
| Harapan konversi magang→kerja | ❌ Tidak dibahas | ✅ Sudut bicara di draft |
| Skema WFA/hybrid untuk kandidat jauh | ❌ Tidak ada | ✅ Auto-draft WFA jika >10 km |
| Multi-source global (Maps/Glints/LinkedIn) | Umumnya 1 sumber | ✅ Plugin system, region-aware |

Hasilnya: pool kandidat yang jauh lebih luas dan bisa dipakai di negara/kota manapun via konfigurasi `REGION`, bukan hardcode satu kota.

## Features

**Riset & Scraping**
- Scrape perusahaan IT dari Google Maps: rating, ulasan, foto, kontak, koordinat.
- Multi-source via plugin system: Maps, Glints, LinkedIn (+ JobStreet/Indeed di roadmap).
- Region global: `ID-Jabodetabek`, `SG` (Singapore), atau custom koordinat.
- ~36 query pencarian per peran: software / AI / fullstack / game.

**Filtering & Analisa**
- Filter otomatis rating ≥ 4.5, ulasan ≥ 10, dalam bbox region, jarak ≤ 15 km.
- Deteksi perusahaan non-dev (branding agency, gym, bimbel, dll) dengan override sinyal dev.
- Klasifikasi sektor: swasta / negeri / bumn (nama, kategori, domain `.go.id`).
- Deteksi unsur AI pada website perusahaan + bukti kutipan.

**CV & Drafting**
- Analisa CV (PDF/DOCX/TXT): skor 4 arah + checklist ATS.
- Ranking perusahaan by fit-CV (`fit_score` tersimpan di DB).
- Draft pesan lamaran 3 varian, terpersonalisasi dari profil website + skill CV.
- ⚠️ **Auto-WFA**: jarak >10 km otomatis menyisipkan usulan skema Work From Anywhere/hybrid.

**Human-in-the-loop**
- Tool hanya riset & menulis draft — **TIDAK auto-apply**.
- Tracker status lamaran: `shortlisted → applied → replied → interview → accepted/rejected`.
- Database SQLite + export CSV/JSON/Markdown/XLSX.

## Quick Start

Prasyarat: [uv](https://docs.astral.sh/uv/) terpasang, Python 3.12+.

```bash
# 0. Clone & install dependensi
git clone <repo-url>
cd intern-search
uv sync
uv run playwright install chromium   # atau chrome | brave | edge

# 1. Konfigurasi environment
cp .env.example .env                 # lalu edit:
#   HOME_LAT / HOME_LON        → koordinat rumahmu (klik kanan di Google Maps)
#   MAX_DISTANCE_KM=15.0       → radius pencarian maksimum
#   WFA_KM=10.0                → ambang auto-draft Work From Anywhere
#   CAMOFOX_API=<url>          → WAJIB untuk Glints/LinkedIn (lihat bagian Anti-Block)
#   NAMA / SEKOLAH / JURUSAN / DURASI_PKL / EMAIL / TELEPON → pengisi draft pesan

# 2. Buat database SQLite
uv run pkl-research db init

# 3. Kumpulkan kandidat (~36 query, AI-first + IT)
uv run pkl-research search --headless --backend camofox

# 4. Enrich kandidat IT: kontak, foto, review (~15 detik/company)
uv run pkl-research details --scope it --headless

# 5. Analisa CV kamu → skor arah + ATS checklist
uv run pkl-research cv analyze "path/CV.pdf"

# 6. Ranking perusahaan by kecocokan CV
uv run pkl-research cv match

# 7. Shortlist final: scan website + profil mendalam + draft top-N
#    Output: shortlist.md + shortlist.xlsx (3 sheet berwarna) + shortlist_drafts.md
uv run pkl-research shortlist --headless
```

Setelah itu, review kandidat, generate draft per perusahaan, kirim **manual**, dan track statusnya:

```bash
uv run pkl-research db list --qualified --sort distance
uv run pkl-research message "Nama Perusahaan"
# ...kirim manual via email/WA/LinkedIn...
uv run pkl-research track update "Nama Perusahaan" --status applied --sent-via email
uv run pkl-research report
```

## CLI Reference

Semua perintah dijalankan via `uv run pkl-research <command>`.

| Command | Flags | Fungsi |
|---|---|---|
| `db init` | — | Buat schema + migrasi idempotent |
| `search` | `--headless` · `--backend chrome\|camofox\|brave\|edge\|auto` · `--source maps,glints,linkedin,all` · `--region ID-Jakarta\|SG\|custom:lat,lng,radius` | Scan kandidat multi-source → DB |
| `details` | `--scope it` · `--headless` · `--limit N` · `--force` | Enrich kontak, foto, review (resume-aware) |
| `profile` | `--headless` · `--force` | Scan website qualified → profil + deteksi AI |
| `db list` | `--qualified` · `--min-rating N` · `--min-reviews N` · `--role software\|ai\|fullstack\|game` · `--category C` · `--sector swasta\|negeri\|bumn` · `--sort distance\|rating\|ulasan` | Query DB (preset `--qualified` = rating ≥ 4.9 & ulasan ≥ 100) |
| `db stats` | — | Ringkasan data per sektor/peran |
| `cv analyze` | `"<path CV>"` (PDF/DOCX/TXT) | Skor 4 arah + checklist ATS → `output/cv_analysis.json` |
| `cv match` | — | Ranking perusahaan by fit-CV → simpan `fit_score` |
| `shortlist` | `--max-km 15` · `--min-fit 70` · `--min-ulasan 10` · `--headless` · `--no-scan` | IT + dekat + fit-CV → `shortlist.xlsx` + draft top-N |
| `message` | `"<nama>"` | Draft pesan 3 varian (auto-WFA jika >10 km) → DB + stdout |
| `track update` | `--status shortlisted\|applied\|replied\|interview\|accepted\|rejected\|on_hold` · `--note "..."` · `--sent-via email\|wa\|linkedin` | Update status lamaran |
| `track list` | `--status S` | Lihat semua aplikasi |
| `report` | — | Export `report.md`, `profiles.md`, `companies.csv/json`, `drafts.md` |

## Architecture

```text
                 ┌──────────────────────────────┐
                 │      .env / config.py        │
                 │ HOME_LAT · WFA_KM · REGION   │
                 │ NAMA · SEKOLAH · CAMOFOX_API │
                 └──────────────┬───────────────┘
                                ▼
┌──────────────┐   ┌────────────────────────────┐   ┌─────────────────┐
│   Browser    │◀─▶│      scraper/plugins/      │──▶│  data/pkl.db    │
│ Camofox (WAJIB│  │  maps · glints · linkedin  │   │  (SQLite)       │
│ Chrome/Brave │   │  BaseScraper ABC + dedupe  │   │ companies ·     │
│ fallback)    │   └────────────────────────────┘   │ profiles ·      │
└──────────────┘                                    │ applications    │
                                                    └────────┬────────┘
                                                             ▼
  filters.py ──▶ sector.py ──▶ ai_detect.py ──▶ cv_match ──▶ messaging.py
  rating·jarak·  swasta/negeri/ AI subfields    fit_score    draft 3 varian
  bbox·non-dev   bumn           + evidence                   + auto-WFA line
                                                             │
                                                             ▼
                                        exporter (md/csv/xlsx) ─▶ ✅ HUMAN REVIEW
                                                                  kirim manual
```

### Project Structure

```text
src/pkl_research/
├── cli.py             # Entry point CLI (13 subcommand)
├── config.py          # REGIONS global, WFA_THRESHOLD_KM, QUERIES_BY_ROLE, loader .env
├── models.py          # Dataclass: Company, Review, Application, CompanyProfile
├── filters.py         # Filter rating/geografi/jarak + klasifikasi peran (pure)
├── sector.py          # Klasifikasi sektor swasta/negeri/bumn (pure)
├── ai_detect.py       # Deteksi unsur AI pada teks + bukti kutipan (pure)
├── messaging.py       # Template draft + WFA line (pure)
├── exporter.py        # Export CSV/JSON/Markdown/XLSX
├── db/                # Koneksi + schema/migrasi idempotent + Repository pattern
└── scraper/
    ├── backend.py     # resolve_backend() → Camofox wajib
    ├── plugins/       # BaseScraper ABC, registry, maps/glints/linkedin/template.py
    └── browser.py     # Persistent context anti-block
```

## Filter Rules

| # | Aturan | Jenis | Nilai default |
|---|---|---|---|
| 1 | Rating ≥ 4.5 | Hard | `MIN_RATING` di `config.py` |
| 2 | Jumlah ulasan ≥ 10 | Hard | `MIN_REVIEW_COUNT` di `config.py` |
| 3 | Alamat mengandung "Jakarta" | Hard | — |
| 4 | Koordinat dalam bbox region (Jabodetabek / SG) | Hard | `REGIONS[region].bbox` |
| 5 | Jarak rumah ≤ `MAX_DISTANCE_KM` | Hard | 15 km (Jabodetabek), 20 km (SG) |
| 6 | Kategori IT soft-fit | Soft | Ditandai `role_fit`, tidak di-drop |
| 7 | Filter `is_non_dev` | Drop | Gym/salon/kafe/percetakan/branding agency/dll |

Detail aturan 6–7: keyword kategori & nama yang jelas bukan software development (contoh: "penjenamaan", "bimbel", "sablon") menandai kandidat sebagai non-dev. Keyword dev yang kuat ("software", "pengembang aplikasi", "it ") dapat **mengoverride** tanda non-dev.

💡 **Qualified shortlist** (target lamaran): rating ≥ 4.9 **dan** ulasan ≥ 100 — ubah lewat `TARGET_RATING` / `TARGET_MIN_REVIEWS` di `config.py`.

## WFA Auto-Draft

Banyak perusahaan IT bagus ada di luar radius nyaman komuter. Alih-alih membuang kandidat jauh:

- Jika `distance_km > WFA_KM` (default **10 km**, configurable via `.env`), draft menyisipkan **wfa_line**: usulan skema **Work From Anywhere/hybrid** — onsite terjadwal + remote, *bukan* menuntut full remote.
- Threshold bisa diubah per-user (`WFA_KM`) atau per-region (`REGIONS[region].max_km` untuk batas pencarian).
- Untuk region non-ID, draft juga bisa menyisipkan catatan visa jika `remote_policy == WFA`.
- Kamu tetap pegang kendali penuh: baris ini bisa diedit/hapus sebelum kirim.

## Sektor & AI Detection

**Klasifikasi sektor** (`classify_sector(name, category, website)`):
- `negeri` — domain `.go.id`, atau nama mengandung Dinas/Kementerian/Pemerintah (word-boundary).
- `bumn` — pola `(Persero)` dan daftar BUMN terkurasi.
- `swasta` / `unknown` — sisanya.

**Deteksi AI** (`ai_detect`): regex frase — AI Development, Machine Learning, Deep Learning, LLM/Generative AI, Chatbot, Computer Vision, NLP, Data Science, AI Agent, dst. Token `\bai\b` sendirian tidak dihitung (anti false-positive). Output: `ai_subfields` + `ai_evidence` (kutipan bukti dari website).

## CV Analysis

- **`cv analyze`**: ekstrak teks PDF/DOCX/TXT (`pypdf`, `python-docx`), deteksi skill teknis, skor 4 arah 0–100 (software/AI/fullstack/game), plus checklist ATS: kontak, struktur section, keyword, angka terukur, panjang dokumen.
- **`cv match`**: ranking semua perusahaan — `fit_score` = rata-rata skor CV terhadap arah `role_fit` perusahaan, tersimpan di kolom `fit_score`.
- Draft pesan otomatis menyisipkan skill CV yang relevan dengan arah perusahaan tersebut.

📱 Hasil lengkap tersedia di `output/cv_analysis.json` dan kolom `fit_score` di DB.

## Anti-Block Tips

> **Disarankan pakai Camofox Browser** — jauh lebih optimal untuk scraping Maps/Glints (anti-detect, session human-like). **Camofox wajib** untuk sumber Glints/LinkedIn.

- Isi `CAMOFOX_API` di `.env`; gunakan `--backend camofox` (atau biarkan `--backend auto` yang memprioritaskan Camofox).
- Browser persistent context (`user_data/`) — cookie tersimpan, terlihat seperti user biasa.
- Delay acak antar aksi (2–6 dtk) dan antar perusahaan (5–10 dtk).
- Run pertama disarankan **headful** (tanpa `--headless`); kalau muncul captcha, selesaikan manual lalu lanjut headless.
- Checkpoint/resume: perusahaan yang sudah di-enrich tidak diproses ulang (kecuali `--force`).

## Legal Disclaimer

⚠️ Scraping Google Maps melanggar **Terms of Service** Google. Tool ini hanya untuk **riset pribadi volume kecil** — jangan digunakan untuk scraping massal/komersial. Gunakan delay yang wajar dan patuhi rate limit. Data ulasan tetap milik penulisnya. Semua lamaran dikirim **manual oleh user** — tool tidak memiliki jalur pengiriman otomatis apa pun.

## Contributing

Kontribusi welcome! Silakan baca panduan lengkap di [CONTRIBUTING.md](CONTRIBUTING.md). Ide kontribusi yang dibutuhkan: plugin scraper baru (JobStreet, Indeed — lihat `scraper/plugins/template.py`), penambahan region baru di `config.REGIONS`, i18n query per bahasa, dan perbaikan test.

## License

Proyek ini dilisensikan di bawah [MIT License](LICENSE).
