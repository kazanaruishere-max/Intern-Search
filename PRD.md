# PRD — PKL Research Tool (Jakarta Selatan)

- **Status**: Draft v1.1 (tambah fokus peran + role_fit)
- **Tanggal**: 2026-08-05
- **Author**: Owner
- **Tipe**: Tool CLI internal (semi-otomatis, human-in-the-loop)

---

## 1. Latar Belakang

Pemilik membutuhkan daftar perusahaan IT potensial untuk lamaran **Praktik Kerja Lapangan (PKL)** yang berlokasi di sekitar domisilinya (Jakarta Selatan) dengan rating Google Maps tinggi. Riset manual (cari perusahaan → cek rating → baca review → tulis pesan lamaran personal) memakan waktu lama dan tidak terstruktur.

Tool ini mengotomatisasi bagian **riset & drafting**, sementara keputusan akhir dan eksekusi (mengirim lamaran) **tetap sepenuhnya di tangan pemilik**.

## 2. Tujuan & Metrik Sukses

### Tujuan
1. Mengumpulkan & menyimpan data detail perusahaan IT di Jakarta (dalam batas DKI Jakarta) dari Google Maps, dengan fokus pada peran yang dicari: **Software Developer, AI Developer, Fullstack Developer, dan (opsional) Game Developer**.
2. Memfilter otomatis perusahaan rating **≥ 4.5** (prioritas 5.0) dengan jumlah review yang masuk akal (≥ 10).
3. Mengambil **review pelanggan** dan **foto** tiap perusahaan sebagai bahan riset.
4. Menghasilkan **draft pesan lamaran PKL yang dipersonalisasi** berdasarkan data & review sungguhan.
5. Menyimpan **database** berisi seluruh perusahaan, lokasi, dan **status penerimaan PKL** (tracker aplikasi).
6. Tetap **human-in-the-loop**: tool tidak pernah mengirim apa pun sendiri.

### Metrik Sukses
- 1x run `search` menghasilkan ≥ 50 kandidat IT di Jakarta yang lolos filter.
- 1x run `details` berhasil enrich ≥ 90% kandidat (review + foto + kontak) tanpa error fatal.
- `report` menghasilkan file `companies.csv` + `drafts.md` yang siap dipakai.
- Database berfungsi sebagai tracker: status tiap aplikasi tercatat dan bisa di-update via CLI.
- Seluruh logika murni (filter, messaging, exporter, repository) lolos unit test.

## 3. User Persona

**Pelamar PKL (seorang pelajar/mahasiswa IT berdomisili Jakarta Selatan)**
- Ingin daftar perusahaan IT berkualitas dekat domisili.
- Tidak ingin menghabiskan waktu riset manual.
- Tetap ingin kontrol penuh: dia yang memilih, mereview, dan mengirim lamaran.
- Butuh draft pesan yang personal (bukan copy-paste generik) biar peluang diterima lebih besar.
- Ingin melacak status lamaran (sudah dilamar? dibalas? diterima? ditolak?).

## 4. Lingkup

### 4.1. In Scope
- Scraping Google Maps (Playwright) untuk: perusahaan, rating, jumlah review, alamat, koordinat, kategori, kontak, foto, review.
- Filter otomatis: rating, jumlah review, geografi (dalam Jakarta).
- Database SQLite: companies, reviews, applications (tracker).
- Generator draft pesan template-pintar (offline, gratis).
- Ekspor laporan (CSV, JSON, Markdown).
- CLI lengkap dengan checkpoint/resume.

### 4.2. Out of Scope (v1)
- Pengiriman lamaran otomatis (email/WA/LinkedIn) — **sengaja tidak ada**.
- Fitur multi-user / login / autentikasi.
- Deploy ke server/cloud (tool lokal).
- Integrasi LLM/AI API untuk draft (v2 opsional).
- Scraping di luar Google Maps (LinkedIn, Jobstreet, dll) — v2.

### 4.3. Fokus Peran & Daftar Query

Google Maps mengindeks **kategori perusahaan**, bukan lowongan/role. Karena itu pencarian memakai istilah kategori perusahaan (EN + ID), lalu hasil di-*tagging* ke peran target via heuristik kategori (`role_fit`). "Fullstack developer" bukan kategori Maps — perusahaan yang mempekerjakan fullstack dev umumnya *web dev agency / software house / perusahaan produk*, sehingga tercakup di query web/software.

| Fokus Peran | Query pencarian (dipakai dgn akhiran "jakarta selatan", anchor `@-6.24,106.80,13z`) |
|---|---|
| **software** | `software house`, `perusahaan perangkat lunak`, `software development`, `it company` |
| **ai** | `perusahaan AI`, `artificial intelligence company`, `AI startup`, `machine learning company` |
| **fullstack** | `web development`, `perusahaan web`, `pengembang aplikasi`, `it consultant`, `digital agency` |
| **game** (opsional) | `game developer`, `game studio`, `perusahaan game` |

- Daftar query dikelompokkan per fokus di `config.py`; semua query dijalankan saat `search`.
- Kategori asli Google Maps **selalu disimpan** (tidak di-drop); `role_fit` hanya tag tambahan untuk filter manual.
- Klasifikasi heuristik `role_fit` (dari kategori):
  - `ai` ← kategori mengandung "ai", "artificial intelligence", "machine learning", "kecerdasan buatan", "data science"
  - `game` ← "game", "gaming", "permainan"
  - `software` / `fullstack` ← "software", "perangkat lunak", "web", "aplikasi", "it", "teknologi", "digital", "konsultan"
- Heuristik tidak sempurna (mis. AI company terkategori "software house") → **user tetap review**, sesuai prinsip human-in-the-loop.

## 5. Kriteria Produk

### 5.1. Kriteria Filter Kandidat (urutan penerapan)
| # | Aturan | Tipe |
|---|---|---|
| 1 | `rating >= 4.5` | Hard filter |
| 2 | `review_count >= 10` (anti-rating-fake) | Hard filter |
| 3 | Alamat mengandung "Jakarta" | Hard filter |
| 4 | Koordinat dalam bounding box DKI Jakarta: `lat -6.052 s.d -6.364`, `lon 106.685 s.d 106.970` | Hard filter (sekunder) |
| 5 | **Jarak dari rumah `<= MAX_DISTANCE_KM`** (jarak haversine dari `HOME_LAT`, `HOME_LON`) | Hard filter |
| 6 | Kategori IT (software/IT/technology/startup/digital/consulting) | Soft filter (ditandai, tidak di-drop) |
| 7 | Sortir: rating 5.0 duluan, lalu jarak terdekat, lalu jumlah review terbanyak | Sort |

- `HOME_LAT`, `HOME_LON`, `MAX_DISTANCE_KM` dikonfigurasi user di setup (lihat `docs/WORKFLOW.md`).
- Jarak dihitung dengan **haversine distance** (meter/kilometer) dan disimpan ke kolom `distance_km` di DB.
- Rule #5 melengkapi rule #4: batas Jakarta memastikan tidak keluar DKI, jarak memastikan dekat domisili.

- Setiap hasil menyimpan flag `in_jakarta` (hasil cek #3 & #4) dan `is_it` (#5) di database untuk transparansi & filter manual.
- Setiap hasil menyimpan tag `role_fit` (JSON array: `software`/`ai`/`fullstack`/`game`) hasil klasifikasi heuristik kategori (lihat 4.3) — bukan filter hard, hanya untuk filter manual per fokus peran.

### 5.2. Kriteria Anti-Block (Google Maps)
- Gunakan `launch_persistent_context` (user data dir) → profil "kembali", cookie persist.
- Delay acak 2–6 detik antar aksi, 5–10 detik antar perusahaan.
- Default `--headful` untuk run pertama (bisa selesaikan captcha/consent manual); `--headless` opsional setelah aman.
- Auto-dismiss dialog consent.
- Volume kecil & sequential (tanpa konkurrensi agresif).
- Checkpoint/resume berbasis state database.

### 5.3. Kriteria Draft Pesan
- Isi otomatis: nama perusahaan, kategori, lokasi, rating + jumlah review, 1–2 tema positif dari review asli.
- **Sesuai fokus peran**: draft menyesuaikan dengan `role_fit` perusahaan (mis. "...saya tertarik posisi AI developer di perusahaan yang...").
- Placeholder user: `NAMA`, `SEKOLAH`, `JURUSAN`, `DURASI_PKL`, kontak — dikonfigurasi sekali via env/flag.
- 3 varian template: formal / santai-profesional / singkat.
- Draft tersimpan ke DB (`applications.draft_message`) + bisa dicetak ke stdout.
- **Tidak ada jalur pengiriman otomatis.** Titik.

## 6. Kebutuhan Fungsional (diterjemahkan ke CLI)

### 6.1. Database (`db`)
| Perintah | Deskripsi | Keluaran |
|---|---|---|
| `pkl-research db init` | Buat schema + jalankan migrasi (idempotent) | status ok |
| `pkl-research db list [--status] [--min-rating] [--role] [--category] [--sort]` | Query DB dengan filter (termasuk `--role ai|software|fullstack|game`) | tabel |
| `pkl-research db stats` | Ringkasan: total, per status, rata-rata rating | tabel |

### 6.2. Riset (`search`, `details`)
| Perintah | Deskripsi | Keluaran |
|---|---|---|
| `pkl-research search` | Scan semua query per fokus peran (4.3) di center Jaksel (`@-6.24,106.80,13z`), paginate, filter, tag `role_fit`, upsert ke DB (status `scraped`) | progress log |
| `pkl-research details [--force]` | Enrich kandidat (review + foto + kontak), upsert ke DB; skip yang sudah `enriched_at` kecuali `--force` | progress log |

### 6.3. Reporting (`report`, `message`)
| Perintah | Deskripsi | Keluaran |
|---|---|---|
| `pkl-research report` | Baca DB → laporan + ekspor | `output/report.md`, `companies.csv`, `drafts.md` |
| `pkl-research message <nama>` | Generate 1 draft → simpan ke DB + stdout | stdout |

### 6.4. Tracker (`track`)
| Perintah | Deskripsi | Keluaran |
|---|---|---|
| `pkl-research track update <nama> --status <status> [--note ...]` | Update status PKL + catatan | status ok |
| `pkl-research track list` | Semua aplikasi + status | tabel |

**Status PKL yang didukung**: `shortlisted` (default) / `applied` / `replied` / `interview` / `accepted` / `rejected` / `on_hold`.

## 7. Kebutuhan Non-Fungsional

- **Portabilitas**: berjalan di Windows (dev utama), via `uv`; tidak bergantung pada installasi global Python.
- **Kinerja**: stage `details` rata-rata 10–20 detik/company + delay; 100 perusahaan ≈ 30–45 menit (boleh dijalankan semalam).
- **Reliabilitas**: checkpoint/resume dari DB; error satu perusahaan tidak menghentikan seluruh run; log jelas.
- **Kemudahan**: setup `uv sync && uv run playwright install chromium`; `README.md` lengkap.
- **Maintainability**: struktur modular (`scraper/`, `db/`, domain logic terpisah); fungsi < 50 baris; no dead code.
- **Etika/Compliance**: dokumentasi jujur soal ToS Google Maps di README; volume kecil; tanpa abuse.

## 8. Data Model (SQLite `data/pkl.db`)

### `companies`
| Kolom | Tipe | Catatan |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| place_id | TEXT UNIQUE | kunci dedupe (Google) |
| name | TEXT NOT NULL | |
| category | TEXT | kategori utama |
| categories | TEXT (JSON) | daftar kategori |
| rating | REAL | |
| review_count | INTEGER | |
| rating_breakdown | TEXT (JSON) | {1..5: n} |
| address | TEXT | alamat lengkap |
| district | TEXT | kecamatan (jika ter-parse) |
| city | TEXT | |
| postal_code | TEXT | |
| latitude | REAL | |
| longitude | REAL | |
| in_jakarta | INTEGER | flag cek alamat + bbox |
| distance_km | REAL | jarak haversine dari rumah (HOME_LAT/HOME_LON) |
| role_fit | TEXT (JSON) | array peran: `["software","fullstack"]`, hasil klasifikasi heuristik kategori (4.3) |
| phone | TEXT | |
| website | TEXT | |
| email | TEXT | opsional (enrichment) |
| plus_code | TEXT | |
| maps_url | TEXT | |
| cid | TEXT | |
| open_hours | TEXT (JSON) | |
| description | TEXT | |
| price_range | TEXT | |
| photos | TEXT (JSON) | array URL foto |
| photo_count | INTEGER | |
| scraped_at | TEXT (ISO) | |
| enriched_at | TEXT (ISO) | null = belum enrich |

### `reviews`
| Kolom | Tipe | Catatan |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK → companies.id | |
| reviewer_name | TEXT | |
| reviewer_rating | REAL | |
| review_text | TEXT | |
| review_date | TEXT | |
| helpful_count | INTEGER DEFAULT 0 | |
| language | TEXT | |
| translated_text | TEXT | |
| UNIQUE (company_id, reviewer_name, review_text) | | anti-duplikat |

### `applications`
| Kolom | Tipe | Catatan |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK UNIQUE | 1 aplikasi per perusahaan |
| status | TEXT DEFAULT 'shortlisted' | enum di 6.4 |
| applied_at | TEXT | |
| sent_via | TEXT | email/whatsapp/linkedin/website |
| contact_person | TEXT | |
| contact_email | TEXT | |
| contact_phone | TEXT | |
| draft_message | TEXT | draft tersimpan |
| notes | TEXT | catatan pemilik |
| result_notes | TEXT | catatan hasil |
| created_at | TEXT | |
| updated_at | TEXT | |

- Migrasi: tabel `schema_version` + daftar DDL berurut (SQLite, `sqlite3` stdlib).
- Mode koneksi: `WAL`, foreign keys ON.
- Lokasi DB: `data/pkl.db` (gitignored).

## 9. Arsitektur & Komponen

- `models.py` — dataclass domain (Company, Review, Application, DraftMessage).
- `config.py` — konstanta & setting (bbox, center, **query list per fokus peran**, threshold, path, keyword role_fit).
- `db/` — `connection.py` (koneksi, WAL, FK), `schema.py` (DDL + migrasi), `repositories.py` (Repository pattern per entitas).
- `scraper/` — `browser.py` (launch + stealth + delay), `search.py` (kandidat), `detail.py` (info detail + foto), `reviews.py` (review + highlight).
- `filters.py` — logika filter (PURE, testable).
- `messaging.py` — generator draft (PURE, testable).
- `exporter.py` — CSV/JSON/Markdown dari DB (PURE, testable).
- `cli.py` — entry point (typer/rich).

**Prinsip**: domain logic dipisah dari browser automation; logika keputusan bisa di-unit-test tanpa browser; akses data lewat Repository.

## 10. Kebutuhan Teknis & Dependensi

- Python 3.12+ via `uv` (`.python-version`, `pyproject.toml`).
- `playwright` (pip) + `uv run playwright install chromium`.
- `typer`, `rich` untuk CLI.
- `pytest` untuk test.
- Tanpa ORM eksternal — `sqlite3` stdlib + Repository pattern.
- Jarak haversine dihitung dengan `math` stdlib (tanpa dependency tambahan).

## 11. Kebutuhan Test (Verification Gate)

**Unit test (tanpa browser) — critical path:**
- `filters`: semua aturan 5.1 (rating, review count, alamat Jakarta, bbox, kategori, sortir) + klasifikasi `role_fit` (4.3).
- `messaging`: template mengisi data benar, 3 varian valid, placeholder handling.
- `exporter`: CSV/JSON/Markdown terbentuk benar dari data fixture.
- `repositories`: upsert/tulis/baca/hapus ke temp DB; dedupe place_id; FK; migrasi berjalan.
- **Smoke test live (manual):** `scripts/smoke.py` scrape 1 query kecil → cek hasil + simpan HTML fixture.

**Gate**: semua unit test hijau + 1 smoke test sukses sebelum dianggap selesai. Tidak memfabrikasi hasil — laporkan output asli perintah.

## 12. Deliverables

1. Kode lengkap + `pyproject.toml` + `README.md` (setup, usage, arsitektur, caveat ToS).
2. Repo git dengan commit message format `<type>: <description>`.
3. Database `data/pkl.db` terisi (hasil run aktual) + `output/` (report, csv, drafts).
4. **Cerita interview (2 lapis)**:
   - Pipeline riset otomatis: scrape Google Maps → filter geospasial & rating → draft personalized (human-in-the-loop).
   - Data layer: SQLite + Repository pattern + migrasi + application tracker.

## 13. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Google Maps ubah DOM | scraper rusak | fallback selector + `aria-label`; resume; dampak terisolasi di `scraper/` |
| Captcha / rate-limit | run terhambat | headful + manual solve, volume kecil, delay acak |
| ToS Google Maps | blokir akun/IP | volume kecil, dokumentasi jujur, tanpa abuse |
| Data review berubah/dihapus | hasil tidak konsisten | `scraped_at`/`enriched_at` per baris, re-run upsert |
| Selector foto berubah | foto kosong | simpan URL; `--download-photos` opsional |

## 14. Out of Scope & Roadmap v2 (referensi)

- Draft berbasis LLM API (OpenAI/Claude) — opsional.
- Email/WA/LinkedIn integration dengan tetap human-approval.
- UI web dashboard.
- Sumber data lain (LinkedIn, Jobstreet).
- Notifikasi follow-up deadline otomatis.

---

*Dokumen ini menjadi kontrak ruang lingkup v1. Perubahan scope memerlukan revisi PRD.*
