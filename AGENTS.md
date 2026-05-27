# Berlin Classics Newsletter

## Commands (Windows)

```powershell
venv\Scripts\activate.ps1        # activate venv
venv\Scripts\python.exe -m pytest tests/  # 39 sync tests, no external deps
venv\Scripts\python.exe -m ruff check .   # lint
```

## Run modes

All `.bat` launchers delegate to `scripts\run_timed.bat` which activates venv, passes args to `main.py`, and prints elapsed time.

| Command | Effect |
|---|---|
| `run_process.bat` | Normal: cache → scrape missing → TMDB → newsletter |
| `run_fresh.bat` | `--no-cache`: fresh scrape all sites |
| `run_cached.bat` | `--fast`: skip TMDB, re-apply title/year filters (instant, for template/config tweaks) |
| `run_babylon.bat` | Rescrape only Babylon, rest from cache |
| `run_zoo_palast.bat` | Rescrape only Zoo Palast |
| `run_bestofcinema.bat` | Rescrape only Best of Cinema |
| `run_openair.bat` | Rescrape only Open Air Kino |
| `deploy.bat` | Copy latest `output/newsletter_*.html` → `docs/index.html`, commit, push to GitHub Pages |

**`--re-enrich`**: clears TMDB memory cache, re-runs TMDB on raw cache — use when `_clean_title` pattern changes.

**Live at** `https://dapa5900.github.io/berlin-classics/`

## Pipeline (two-level cache)

```
scrape → cache/screenings.json → title filters → TMDB enrich → filter_no_tmdb → cache/screenings_enriched.json → year filter → newsletter
```

- **Raw cache** (`cache/screenings.json`): scraper output before TMDB.
- **Rich cache** (`cache/screenings_enriched.json`): after TMDB, before year/title filters.

## Grid breakpoints (newsletter.html)

| Breakpoint | Columns |
|---|---|
| ≥768px | 3 columns `1fr`, gap 20px |
| 351–767px | 2 columns `1fr` |
| ≤350px | 1 column `1fr` |

## Architecture

- `main.py` maps config `type` → scraper class. All scrapers return raw `Screening` (no TMDB enrichment).
- `Screening` dataclass (`scrapers/base.py`): `cinema_name`, `movie_title`, `date`, `url`, `year`, `poster_url`, `tmdb_url`, `skip_year_filter`, `runtime`, `venue_name`, `production_year`, `original_title`
- TMDB enrichment groups by `(movie_title, production_year, original_title)`, queries once per group, mutates `Screening` in place.
- `_clean_title` (`services/tmdb.py`): NFD-normalizes, strips known series/festival prefixes. Add patterns here when obscure titles fail TMDB match. Also handles multi-part titles ("trilogie"/"marathon"/"X-hour").
- Template groups screenings by `venue_name` if set, else `cinema_name`. Open Air Kino sets `venue_name` per-article; all others leave `None`.
- Config-driven via `config.yaml`: cinemas, title filters, year threshold (`classical_year_threshold: 2010`), output format.
- `locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")` at module level in `services/newsletter.py` — breaks if locale unavailable.
- `DESIGN.md` exists for visual style reference (colors, typography, spacing).

## Scraper gotchas

- **Babylon**: HTTP GET to `/programm`. Each `.mix` `<li>` has `cat-*` CSS class. `_strip_festival_prefix` auto-detects festival sections (URL contains `/festivals/`). Uses `.right-mix .mix-title` (full title), `.mix-introtext` (year via `,\s*(\d{4})`, original via `[...]`), `.right-mix .runtime`.
- **Zoo Palast**: Playwright-based. Intercepts API JSON from `premiumkino.de/program` via network listener. Also scrapes `/specials/filmklassiker` to set `skip_year_filter=True`.
- **Best of Cinema**: Fetches each movie subpage. `Produktionsjahr:` and `Laufflänge` regex from page text.
- **Open Air Kino**: Date in `div.meta_kino` previous sibling of `<article>`, uses `[\w.]+` for abbreviated German months. Multi-cinema aggregator — `venue_name` set per screening.

## TMDB matching order

1. If `original_title` + `expected_year`: search original title + exact year first
2. Exact year match
3. ±3yr, similarity ≥ 0.3
4. ±2yr, similarity ≥ 0.5
5. Best similarity fallback (≥0.7, best year diff)

## Setup

- `TMDB_API_KEY` in `.env`
- Python 3.13+, `pip install -r requirements.txt`
- `playwright install chromium` after pip install
- `cache/`, `output/`, `venv/`, `logs/` in `.gitignore`
- Scheduled Task (Windows): `NewsletterGenerator`, weekly Fri 13:00, runs `C:\newsletter\run.bat`

## Test quirks

- All 39 tests are synchronous, no external dependencies.
- `conftest.py` provides `tmdb_service` (fake API key for unit tests), `sample_screenings` (3 `Screening` fixtures), `config_file` (tmp_path YAML).
