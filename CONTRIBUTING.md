# Contributing to Intern-Search

Terima kasih sudah tertarik untuk berkontribusi! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Pull Request Process](#pull-request-process)
- [Coding Guidelines](#coding-guidelines)
- [Plugin Development](#plugin-development)
- [Adding New Regions](#adding-new-regions)
- [Running Tests](#running-tests)
- [License](#license)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to **kazanaruishere@gmail.com**.

## Getting Started

1. **Fork** repository ini ke GitHub.
2. **Clone** fork kamu:
   ```bash
   git clone https://github.com/<username>/intern-search.git
   cd intern-search
   ```
3. **Buat branch** untuk fitur/fix kamu:
   ```bash
   git checkout -b feat/nama-fitur
   ```

## Development Setup

Prasyarat: Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
# Install dependensi
uv sync

# Install browser Chromium (untuk testing)
uv run playwright install chromium

# Jalankan tests untuk memastikan semuanya jalan
uv run pytest
```

## How to Contribute

### Reporting Bugs

Buka [GitHub Issues](link-repo/issues) dan sertakan:

- **Judul deskriptif** — "Crash saat run `search --backend camofox`"
- **Steps to reproduce** — langkah-langkah yang menyebabkan bug
- **Expected vs Actual behavior**
- **Environment** — OS, Python version, uv version
- **Logs/error** — paste stack trace jika ada

### Suggesting Features

Buka issue dengan label **enhancement** dan sertakan:

- **Use case** — kenapa fitur ini dibutuhkan?
- **Contoh konkret** — seperti apa output/behavior yang diharapkan?
- **Alternatives** — solusi lain yang sudah dipertimbangkan

### Areas We Need Help

- 🔌 **Plugin scraper baru** — lihat `src/pkl_research/scraper/plugins/template.py`
- 🌍 **Region baru** — tambah region di `src/pkl_research/config.py` (`REGIONS`)
- 🌐 **Query per bahasa** — i18n query pencarian untuk negara/kota tertentu
- 🧪 **Test coverage** — tambah unit test untuk modul yang belum ter-cover
- 📝 **Dokumentasi** — perbaiki README, tambah contoh penggunaan, dll

## Pull Request Process

1. **Update branch** kamu dengan branch `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Pastikan tests lulus**:
   ```bash
   uv run pytest
   ```

3. **Commit dengan pesan yang jelas**:
   ```bash
   git commit -m "feat: tambah plugin scraper untuk JobStreet"
   ```

   Format commit:
   - `feat:` — fitur baru
   - `fix:` — perbaikan bug
   - `docs:` — perubahan dokumentasi
   - `refactor:` — refactor tanpa perubahan behavior
   - `test:` — tambah/ubah test
   - `chore:` — maintenance, dependency update

4. **Push dan buka PR**:
   ```bash
   git push origin feat/nama-fitur
   ```

5. **Di PR**, sertakan:
   - Deskripsi singkat **apa yang berubah** dan **kenapa**
   - Link ke issue yang terkait (jika ada)
   - Screenshot/output jika ada perubahan visual

## Coding Guidelines

- **Ikuti style yang sudah ada** di codebase ini
- **Type hints** wajib untuk semua fungsi baru
- **Docstring** untuk fungsi/publik API yang signifikan
- **Pure functions** sebisa mungkin (terpisah dari I/O/side-effect)
- **Naming**: snake_case untuk Python, PascalCase untuk class
- **Python 3.12+** — gunakan fitur modern (match-case, type statement, dll)

## Plugin Development

Ingin menambah scraper untuk sumber baru? Lihat `src/pkl_research/scraper/plugins/template.py` sebagai boilerplate.

### Langkah-langkah:

1. Copy `template.py` → `nama_sumber.py`
2. Implementasi class yang extends `BaseScraper`
3. Register plugin di `__init__.py`
4. Tambah query di `config.py` jika perlu
5. Tulis unit test untuk logic scraping

### Interface yang harus diimplementasi:

```python
class MyScraper(BaseScraper):
    async def search(self, query: str, region: RegionConfig) -> list[Company]:
        """Scrape search results → list Company."""
        ...

    async def detail(self, company: Company) -> Company:
        """Enrich company: contact, reviews, photos."""
        ...
```

## Adding New Regions

Untuk menambah region/kota baru:

1. Tambah data region di `src/pkl_research/config.py`:
   ```python
   REGIONS = {
       # ... regions yang sudah ada ...
       "MY-KL": Region(
           name="Kuala Lumpur",
           center_lat=3.1390,
           center_lon=101.6869,
           max_km=20,
       ),
   }
   ```

2. Tambah query spesifik region jika perlu
3. Update README bagian CLI Reference

## Running Tests

```bash
# Jalankan semua tests
uv run pytest

# Jalankan dengan verbose output
uv run pytest -v

# Jalankan test spesifik
uv run pytest tests/test_filters.py
```

Coverage: filters, messaging, exporter, repository (SQLite) — tanpa browser.

## License

Dengan berkontribusi, kamu setuju bahwa kontribusi kamu akan dilisensikan di bawah [MIT License](LICENSE).
