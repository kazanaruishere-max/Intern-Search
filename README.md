# PKL Research Tool

Tool CLI **semi-otomatis** untuk riset perusahaan IT di sekitar Jakarta Selatan dalam rangka lamaran **Praktik Kerja Lapangan (PKL)**.

- Scrape perusahaan IT dari **Google Maps** (rating, ulasan, foto, kontak, koordinat).
- **Filter otomatis**: rating ≥ 4.5, jumlah ulasan ≥ 10, dalam DKI Jakarta, dan jarak dari rumah ≤ `MAX_DISTANCE_KM`.
- **Tag peran**: software / AI / fullstack / game.
- **Klasifikasi sektor**: swasta / negeri / bumn (dari nama, kategori, dan domain `.go.id`).
- **Profil perusahaan dari website**: kunjungi website, ambil inti fokus (meta/heading), halaman tentang, layanan, halaman karir, email, sosmed — plus **deteksi unsur AI** (AI Development, Machine Learning, Chatbot, dsb) dengan bukti kutipan.
- Generate **draft pesan lamaran yang dipersonalisasi** dari data, review, dan profil website.
- **Database SQLite** untuk semua perusahaan + **tracker status lamaran** (shortlisted → applied → … → accepted).
- **Human-in-the-loop**: tool hanya riset & menulis draft. **Tidak pernah mengirim lamaran sendiri.**

---

## Setup

```bash
# 1. Install dependensi + browser
uv sync
uv run playwright install chromium

# 2. Konfigurasi lokasi & identitas (edit file .env)
#    - HOME_LAT, HOME_LON, MAX_DISTANCE_KM   → filter jarak dari rumah
#    - NAMA, SEKOLAH, JURUSAN, DURASI_PKL     → pengisi draft pesan
```

> Koordinat rumah bisa dicek di Google Maps (klik kanan pada lokasi → copy koordinat).
> Contoh: Cikoko/Pancoran → `-6.2395, 106.8555`.

## Alur pakai (cepat)

```bash
# 1. Buat database
uv run pkl-research db init

# 2. Kumpulkan kandidat (scan 16 query, simpan ke DB)
uv run pkl-research search --headless

# 3. Enrich kandidat IT: kontak, foto, review (bisa lama ~15 detik/company)
uv run pkl-research details --scope it --headless

# 3b. Scan website kandidat qualified (>=4.9, >=100 ulasan): profil + deteksi AI
uv run pkl-research profile --headless

# 3c. Analisa CV kamu → skor arah (software/AI/fullstack/game) + ATS checklist
uv run pkl-research cv analyze "path/CV.pdf"

# 3d. Ranking perusahaan by kecocokan dengan CV kamu
uv run pkl-research cv match

# 3e. SHORTLIST FINAL: IT + Jakarta Selatan + dekat rumah + fit CV
#     → scan website semua kandidat + profil mendalam + draft top 10
uv run pkl-research shortlist --headless

# 4. Review kandidat (filter per peran, rating, sektor)
uv run pkl-research db list --qualified --sort distance
uv run pkl-research db list --role software --min-rating 4.5
uv run pkl-research db list --sector negeri

# 5. Generate draft pesan untuk satu perusahaan
uv run pkl-research message "Nama Perusahaan"

# 6. Setelah kamu KIRIM MANUAL (email/WA/LinkedIn):
uv run pkl-research track update "Nama Perusahaan" --status applied --sent-via email --note "via HR email"

# 7. Ekspor laporan
uv run pkl-research report
```

## Referensi perintah

| Perintah | Fungsi |
|---|---|
| `pkl-research db init` | Buat schema + migrasi (idempotent) |
| `pkl-research search [--headless]` | Scan kandidat IT Jaksel → DB |
| `pkl-research details --scope it [--headless] [--limit N] [--force]` | Enrich kontak, foto, review |
| `pkl-research profile [--headless] [--force]` | Scan website qualified → profil + deteksi AI |
| `pkl-research db list [--qualified] [--min-rating] [--min-reviews] [--role] [--category] [--sector] [--sort]` | Query DB (preset `--qualified` = ≥4.9 & ≥100 ulasan) |
| `pkl-research db stats` | Ringkasan data (termasuk per sektor) |
| `pkl-research message "<nama>"` | Draft pesan (3 varian, pakai profil website) → simpan + stdout |
| `pkl-research report` | `report.md`, `profiles.md`, `companies.csv`, `companies.json`, `drafts.md` |
| `pkl-research cv analyze "<path>"` | Analisa CV: skor 4 arah + ATS checklist → `output/cv_analysis.json` |
| `pkl-research cv match` | Ranking perusahaan by fit-CV → simpan `fit_score` di DB |
| `pkl-research shortlist [--max-km 6] [--min-fit 70] [--min-ulasan 10] [--headless]` | Shortlist CV-match (IT + Jakarta Selatan + dekat + fit): scan website → `shortlist.md` + **`shortlist.xlsx` (3 sheet berwarna)** + `shortlist_drafts.md` (top N) |
| `pkl-research track update "<nama>" --status <s> [--note ...]` | Update status lamaran |
| `pkl-research track list [--status]` | Lihat semua aplikasi |

Status: `shortlisted` / `applied` / `replied` / `interview` / `accepted` / `rejected` / `on_hold`

## Struktur proyek

```
src/pkl_research/
├── config.py        # konstanta + bbox Jakarta + query per peran + target qualified + .env
├── models.py        # dataclass: Company, Review, Application, CompanyProfile
├── filters.py       # filter rating/geografi/jarak + klasifikasi peran (pure)
├── sector.py        # klasifikasi sektor: swasta/negeri/bumn (pure)
├── ai_detect.py     # deteksi unsur AI pada teks (regex frase, pure)
├── messaging.py     # template draft pesan (pure)
├── exporter.py      # CSV/JSON/Markdown (pure)
├── db/              # koneksi + schema/migrasi + Repository pattern
└── scraper/         # Playwright: browser, search, detail, reviews, website
```

## Filter (PRD 5.1)

1. Rating ≥ 4.5 (hard)
2. Jumlah ulasan ≥ 10 (hard)
3. Alamat mengandung "Jakarta" (hard)
4. Koordinat dalam bounding box DKI Jakarta (hard, sekunder)
5. Jarak dari rumah ≤ `MAX_DISTANCE_KM` (hard)
6. Kategori IT (soft — ditandai `role_fit`, tidak di-drop)

**Qualified shortlist** (target lamaran): rating ≥ 4.9 **dan** ulasan ≥ 100 (bisa diubah di `config.py`: `TARGET_RATING`, `TARGET_MIN_REVIEWS`).

## Sektor & Deteksi AI

- **Sektor**: `classify_sector(name, category, website)` → `negeri` (domain `.go.id`, nama Dinas/Kementerian/Pemerintah — word-boundary), `bumn` (`(Persero)`/BUMN terkurasi), `swasta`, `unknown`.
- **Deteksi AI** (`ai_detect`): pola frase regex — AI Development, Artificial Intelligence/Kecerdasan Buatan, Machine Learning, Deep Learning, LLM/Generative AI, Chatbot, Computer Vision, NLP, Data Science, AI Agent. `\bai\b` sendirian tidak dihitung (anti false-positive). Output `ai_subfields` + `ai_evidence` (kutipan bukti).

## Analisa CV & Pencocokan

- **`cv analyze`**: ekstrak teks dari PDF/DOCX/TXT (`pypdf`, `python-docx`), deteksi skill teknis, skor 4 arah (0–100): software/AI/fullstack/game, plus checklist ATS (kontak, section, keyword, angka terukur, panjang).
- **`cv match`**: ranking perusahaan `fit_score` = rata-rata skor CV untuk `role_fit` perusahaan → tersimpan di kolom `fit_score` (migrasi v3).
- Draft pesan otomatis menyisipkan skill CV yang relevan dengan arah perusahaan.

## Anti-block

- Browser persistent context (`user_data/`) → cookie tersimpan, terlihat seperti pengguna biasa.
- Delay acak antar aksi & antar perusahaan.
- Run pertama disarankan **headful** (hapus `--headless`) kalau muncul captcha — selesaikan manual, lalu lanjutkan `--headless`.
- Checkpoint/resume: perusahaan yang sudah `enriched_at` tidak di-enrich ulang (kecuali `--force`).

## Catatan legal (penting)

Scraping Google Maps melanggar **Terms of Service** Google. Tool ini ditujukan untuk **riset pribadi volume kecil** saja — jangan gunakan untuk scraping massal/komersial, dan jangan abuse (pakai delay, headful saat captcha). Data ulasan tetap milik penulisnya. Semua lamaran dikirim **manual oleh user**, bukan oleh tool.

## Test

```bash
uv run pytest
```

Coverage unit test: filters, messaging, exporter, dan repository (SQLite) — tanpa browser.
Smoke test live: `uv run python scripts/smoke_search.py`, `scripts/smoke_detail.py`.

## Roadmap v2

- Draft via LLM API (OpenAI/Claude) — opsional.
- Integrasi email/WA dengan tetap human-approval.
- UI web dashboard.
- Sumber data tambahan (LinkedIn, Jobstreet).
