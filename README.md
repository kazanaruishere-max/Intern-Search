# Intern-Search

[🇬🇧 English](README.md) | [🇮🇩 Bahasa Indonesia](README_ID.md)

> Semi-autonomous intern/PKL search tool with CV-fit scoring, multi-source scraping (Google Maps / Glints / LinkedIn), auto-draft WFA for candidates >10 km, and a **human-in-the-loop** design.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![CLI](https://img.shields.io/badge/interface-CLI-informational)

Intern-Search is a semi-automated CLI tool for researching IT internship/PKL opportunities: scrape candidates from multiple sources, auto-filter, analyze CV fit, and generate personalized application draft messages. The tool **never sends applications on its own** — you choose, edit, and send manually.

---

## Why Intern-Search?

90% of `job-search` repos on GitHub focus on full-time vacancies. Intern/PKL needs are fundamentally different:

| Intern/PKL Need | Typical job-search repo | Intern-Search |
|---|---|---|
| Fixed period (e.g. Jan–Mar, 3 months) | ❌ Not supported | ✅ Integrated in draft (`DURASI_PKL`) |
| School letter & mentorship | ❌ Not relevant | ✅ Factored into application context |
| Internship-to-fulltime conversion | ❌ Not discussed | ✅ Angle in draft message |
| WFA/hybrid for far candidates | ❌ Not available | ✅ Auto-draft WFA if >10 km |
| Multi-source global (Maps/Glints/LinkedIn) | Usually 1 source | ✅ Plugin system, region-aware |

Result: a much wider candidate pool, usable in any city/country via `REGION` config — not hardcoded to one city.

## Features

**Research & Scraping**
- Scrape IT companies from Google Maps: rating, reviews, photos, contact, coordinates.
- Multi-source via plugin system: Maps, Glints, LinkedIn (+ JobStreet/Indeed on roadmap).
- Global regions: `ID-Jabodetabek`, `SG` (Singapore), or custom coordinates.
- ~36 search queries per role: software / AI / fullstack / game.

**Filtering & Analysis**
- Auto-filter: rating ≥ 4.5, reviews ≥ 10, within region bbox, distance ≤ 15 km.
- Non-dev detection (branding agency, gym, tutoring, etc.) with dev-signal override.
- Sector classification: private / government / state-owned (name, category, `.go.id` domain).
- AI detection on company websites + evidence quotes.

**CV & Drafting**
- CV analysis (PDF/DOCX/TXT): 4-direction score + ATS checklist.
- Company ranking by CV-fit (`fit_score` stored in DB).
- 3-variant application draft messages, personalized from website profile + CV skills.
- ⚠️ **Auto-WFA**: distance >10 km automatically inserts a Work From Anywhere/hybrid proposal.

**Human-in-the-loop**
- The tool only researches & writes drafts — **NO auto-apply**.
- Application tracker: `shortlisted → applied → replied → interview → accepted/rejected`.
- SQLite database + export to CSV/JSON/Markdown/XLSX.

## Quick Start

Prerequisite: [uv](https://docs.astral.sh/uv/) installed, Python 3.12+.

```bash
# 0. Clone & install dependencies
git clone <repo-url>
cd intern-search
uv sync
uv run playwright install chromium   # or chrome | brave | edge

# 1. Configure environment
cp .env.example .env                 # then edit:
#   HOME_LAT / HOME_LON        → your home coordinates (right-click on Google Maps)
#   MAX_DISTANCE_KM=15.0       → max search radius
#   WFA_KM=10.0                → auto-draft Work From Anywhere threshold
#   CAMOFOX_API=<url>          → REQUIRED for Glints/LinkedIn (see Anti-Block)
#   NAMA / SEKOLAH / JURUSAN / DURASI_PKL / EMAIL / TELEPON → draft message fields

# 2. Create SQLite database
uv run pkl-research db init

# 3. Collect candidates (~36 queries, AI-first + IT)
uv run pkl-research search --headless --backend camofox

# 4. Enrich IT candidates: contact, photos, reviews (~15 sec/company)
uv run pkl-research details --scope it --headless

# 5. Analyze your CV → direction scores + ATS checklist
uv run pkl-research cv analyze "path/CV.pdf"

# 6. Rank companies by CV fit
uv run pkl-research cv match

# 7. Final shortlist: scan websites + deep profiles + top-N drafts
#    Output: shortlist.md + shortlist.xlsx (3 color-coded sheets) + shortlist_drafts.md
uv run pkl-research shortlist --headless
```

After that, review candidates, generate per-company drafts, send **manually**, and track:

```bash
uv run pkl-research db list --qualified --sort distance
uv run pkl-research message "Company Name"
# ...send manually via email/WA/LinkedIn...
uv run pkl-research track update "Company Name" --status applied --sent-via email
uv run pkl-research report
```

## CLI Reference

All commands run via `uv run pkl-research <command>`.

| Command | Flags | Description |
|---|---|---|
| `db init` | — | Create schema + idempotent migrations |
| `search` | `--headless` · `--backend chrome\|camofox\|brave\|edge\|auto` · `--source maps,glints,linkedin,all` · `--region ID-Jakarta\|SG\|custom:lat,lng,radius` | Multi-source candidate scan → DB |
| `details` | `--scope it` · `--headless` · `--limit N` · `--force` | Enrich contact, photos, reviews (resume-aware) |
| `profile` | `--headless` · `--force` | Scan qualified websites → profile + AI detection |
| `db list` | `--qualified` · `--min-rating N` · `--min-reviews N` · `--role software\|ai\|fullstack\|game` · `--category C` · `--sector swasta\|negeri\|bumn` · `--sort distance\|rating\|ulasan` | Query DB (preset `--qualified` = rating ≥ 4.9 & reviews ≥ 100) |
| `db stats` | — | Summary per sector/role |
| `cv analyze` | `"<CV path>"` (PDF/DOCX/TXT) | 4-direction scores + ATS checklist → `output/cv_analysis.json` |
| `cv match` | — | Rank companies by CV fit → saves `fit_score` |
| `shortlist` | `--max-km 15` · `--min-fit 70` · `--min-ulasan 10` · `--headless` · `--no-scan` | IT + near + CV-fit → `shortlist.xlsx` + top-N drafts |
| `message` | `"<name>"` | 3-variant draft (auto-WFA if >10 km) → DB + stdout |
| `track update` | `--status shortlisted\|applied\|replied\|interview\|accepted\|rejected\|on_hold` · `--note "..."` · `--sent-via email\|wa\|linkedin` | Update application status |
| `track list` | `--status S` | View all applications |
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
  rating·jarak·  swasta/negeri/ AI subfields    fit_score    draft 3 variants
  bbox·non-dev   bumn           + evidence                   + auto-WFA line
                                                             │
                                                             ▼
                                       exporter (md/csv/xlsx) ─▶ ✅ HUMAN REVIEW
                                                                 send manually
```

### Project Structure

```text
src/pkl_research/
├── cli.py             # CLI entry point (13 subcommands)
├── config.py          # REGIONS global, WFA_THRESHOLD_KM, QUERIES_BY_ROLE, .env loader
├── models.py          # Dataclasses: Company, Review, Application, CompanyProfile
├── filters.py         # Rating/geography/distance filter + role classification (pure)
├── sector.py          # Sector classification: private/government/state-owned (pure)
├── ai_detect.py       # AI detection on text + evidence quotes (pure)
├── messaging.py       # Draft templates + WFA line (pure)
├── exporter.py        # Export CSV/JSON/Markdown/XLSX
├── db/                # Connection + schema/idempotent migrations + Repository pattern
└── scraper/
    ├── backend.py     # resolve_backend() → Camofox preferred
    ├── plugins/       # BaseScraper ABC, registry, maps/glints/linkedin/template.py
    └── browser.py     # Persistent context anti-block
```

## Filter Rules

| # | Rule | Type | Default |
|---|---|---|---|
| 1 | Rating ≥ 4.5 | Hard | `MIN_RATING` in `config.py` |
| 2 | Review count ≥ 10 | Hard | `MIN_REVIEW_COUNT` in `config.py` |
| 3 | Address contains "Jakarta" | Hard | — |
| 4 | Coordinates within region bbox (Jabodetabek / SG) | Hard | `REGIONS[region].bbox` |
| 5 | Home distance ≤ `MAX_DISTANCE_KM` | Hard | 15 km (Jabodetabek), 20 km (SG) |
| 6 | IT category soft-fit | Soft | Tagged `role_fit`, not dropped |
| 7 | `is_non_dev` filter | Drop | Gym/salon/café/printing/branding agency/etc. |

Rules 6–7 detail: category & name keywords that are clearly not software development (e.g. "branding", "tutoring", "screen printing") mark a candidate as non-dev. Strong dev keywords ("software", "app developer", "it ") can **override** the non-dev flag.

💡 **Qualified shortlist** (application target): rating ≥ 4.9 **and** reviews ≥ 100 — configurable via `TARGET_RATING` / `TARGET_MIN_REVIEWS` in `config.py`.

## WFA Auto-Draft

Many great IT companies are beyond a comfortable commute. Instead of dropping distant candidates:

- If `distance_km > WFA_KM` (default **10 km**, configurable via `.env`), the draft inserts a **wfa_line**: a proposal for a **Work From Anywhere/hybrid** scheme — scheduled onsite + remote, *not* demanding full remote.
- Threshold is per-user (`WFA_KM`) or per-region (`REGIONS[region].max_km` for search limit).
- For non-ID regions, the draft can also include a visa note if `remote_policy == WFA`.
- You retain full control: this line can be edited/removed before sending.

## Sector & AI Detection

**Sector classification** (`classify_sector(name, category, website)`):
- `government` — `.go.id` domain, or name contains Dinas/Kementerian/Pemerintah (word-boundary).
- `state-owned` — `(Persero)` pattern and a curated BUMN list.
- `private` / `unknown` — everything else.

**AI Detection** (`ai_detect`): phrase regex — AI Development, Machine Learning, Deep Learning, LLM/Generative AI, Chatbot, Computer Vision, NLP, Data Science, AI Agent, etc. Standalone `\bai\b` token is not counted (anti-false-positive). Output: `ai_subfields` + `ai_evidence` (evidence quotes from website).

## CV Analysis

- **`cv analyze`**: extract text from PDF/DOCX/TXT (`pypdf`, `python-docx`), detect technical skills, score 4 directions 0–100 (software/AI/fullstack/game), plus ATS checklist: contact, section structure, keywords, quantified achievements, document length.
- **`cv match`**: rank all companies — `fit_score` = average CV score against company's `role_fit`, stored in the `fit_score` column.
- Draft messages automatically insert CV skills relevant to the company's direction.

📱 Full results available in `output/cv_analysis.json` and the `fit_score` column in the DB.

## Anti-Block Tips

> **Camofox Browser is recommended** — significantly better for scraping Maps/Glints (anti-detect, human-like session). **Camofox is required** for Glints/LinkedIn sources.

- Set `CAMOFOX_API` in `.env`; use `--backend camofox` (or leave `--backend auto` which prioritizes Camofox).
- Browser persistent context (`user_data/`) — cookies persist, looks like a returning user.
- Random delay between actions (2–6 sec) and between companies (5–10 sec).
- First run recommended **headful** (without `--headless`); if captcha appears, solve manually then continue headless.
- Checkpoint/resume: already-enriched companies are not re-processed (unless `--force`).

## Troubleshooting

| Problem | Solution |
|---|---|
| **CAPTCHA during scraping** | Run without `--headless`, solve captcha manually, then continue with `--headless`. |
| **Camofox error / `fetch failed`** | Ensure Camofox server is running & `CAMOFOX_API` is set in `.env`. Fallback: `--backend chrome` (Playwright). |
| **`shortlist.xlsx` Permission denied** | File is open in Excel — close it first, then re-run. |
| **Glints/LinkedIn return 0 results** | Plugin POC — sites often change DOM. Check `output/probe_*.html` for debugging, or use `--source maps` only. |
| **Reviews not fully loaded** | Increase `--max-reviews 50` in `details`. Default 20 is enough for highlights. |
| **`fit_score` empty** | Run `cv analyze <path>` first, then `cv match`. |
| **Draft message missing profile_line** | Run `profile --scan` to scan qualified companies' websites. |

## Legal Disclaimer

⚠️ Scraping Google Maps violates Google's **Terms of Service**. This tool is for **small-volume personal research** only — do not use for mass/commercial scraping. Use reasonable delays and respect rate limits. Review data belongs to its authors. All applications are sent **manually by the user** — the tool has no automated sending mechanism.

## Contributing

Contributions welcome! Read the full guide at [CONTRIBUTING.md](CONTRIBUTING.md). Areas we need help with: new scraper plugins (JobStreet, Indeed — see `scraper/plugins/template.py`), new regions in `config.REGIONS`, i18n query per language, and test improvements.

## License

This project is licensed under the [MIT License](LICENSE).
