# Berlin Classics Newsletter

## Commands (Windows)

```powershell
venv\Scripts\activate.ps1                            # activate venv
venv\Scripts\python.exe -m pytest tests/ -v           # 46 sync tests, no external deps
ruff check .                                          # lint (not via python -m)
```

## Run modes

All `.bat` files delegate to `scripts\run_timed.bat` which logs elapsed time.

| Command | Effect |
|---|---|
| `run_process.bat` | cache → scrape missing → TMDB → newsletter |
| `run_fresh.bat` | `--no-cache`: fresh scrape all sites |
| `run_cached.bat` | `--fast`: skip TMDB, re-apply title/year filters (instant) |
| `run_babylon.bat` | rescrape Babylon only, rest from cache |
| `run_zoo_palast.bat` | rescrape Zoo Palast only |
| `run_bestofcinema.bat` | rescrape Best of Cinema only |
| `run_openair.bat` | rescrape Open Air Kino only |
| `run_filmrausch.bat` | rescrape Filmrausch only, rest from cache |
| `deploy.bat` | copy `output/newsletter_*.html` → `docs/index.html`, commit, push to GitHub Pages |

**`--re-enrich`**: clears TMDB memory cache, re-runs TMDB on raw cache — use when `_clean_title` pattern changes or title filters change.

**Live at**: `https://dapa5900.github.io/berlin-classics/`

## Pipeline (two-level cache)

```
scrape → cache/screenings.json → title filters → TMDB enrich → filter_no_tmdb → cache/screenings_enriched.json → year filter → newsletter
```

- **Raw cache** (`cache/screenings.json`): scraper output before TMDB.
- **Rich cache** (`cache/screenings_enriched.json`): after TMDB, before year/title filters.

## Architecture

- `main.py` maps config `type` → scraper class. All scrapers return raw `Screening` (no TMDB enrichment).
- `Screening` dataclass (`scrapers/base.py`): `cinema_name`, `movie_title`, `date`, `url`, `year`, `poster_url`, `tmdb_url`, `skip_year_filter`, `runtime`, `venue_name`, `production_year`, `original_title`
- TMDB enrichment groups by `(movie_title, production_year, original_title)`, queries once per group, mutates `Screening` in place.
- TMDB API calls are rate-limited: `asyncio.Semaphore(5)` + 3 retries with exponential backoff (2s/4s/8s) on 429.
- `_clean_title` (`services/tmdb.py`): NFD-normalizes, strips known series/festival prefixes. Add patterns here for obscure titles. Also handles multi-part titles ("trilogie"/"marathon"/"X-hour").
- Template groups screenings by `venue_name` if set, else `cinema_name`. Open Air Kino sets `venue_name` per-article; all others leave `None`.
- Config-driven via `config.yaml`: cinemas, title filters, year threshold (`classical_year_threshold: 2010`), output format.
- `locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")` at module level in `services/newsletter.py` — breaks if locale unavailable.
- **Timezone pitfall**: Kinoheld dates (`datetime.fromisoformat`) are timezone-aware; other scrapers produce naive datetimes. Sort must use `.replace(tzinfo=None)` — see `main.py:445`.

## Scraper gotchas

- **Babylon**: HTTP GET to `/programm`. Each `.mix` `<li>` has `cat-*` CSS class. `_strip_festival_prefix` auto-detects festival sections. Uses `.right-mix .mix-title`, `.mix-introtext` (year via `,\s*(\d{4})`, original via `[...]`), `.right-mix .runtime`.
- **Zoo Palast**: Playwright-based. Intercepts API JSON from `premiumkino.de/program` via network listener. Also scrapes `/specials/filmklassiker` to set `skip_year_filter=True`.
- **Best of Cinema**: Fetches each movie subpage. `Produktionsjahr:` and `Laufflänge` regex from page text.
- **Open Air Kino**: Date in `div.meta_kino` previous sibling of `<article>`, uses `[\w.]+` for abbreviated German months. Multi-cinema aggregator — `venue_name` set per screening.
- **Filmrausch**: HTTP-only (no Playwright). Parses embedded `<script id="programm-script-config-js-extra">` JSON (`filmrausch_php_vars.cached_data`). Strips `SPECIAL:`, `Klimareihe:`, `OPEN AIR:`, `OFFENE LEINWAND:`, `REEL LOVE:`, `MONDO VIDEO` prefixes via loop in `_clean_movie_title`. Dates from `isoFull` are timezone-aware. Backend = Kinoheld.

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
- Scheduled Task (Windows): `NewsletterGenerator`, daily 13:00, runs `scripts\run_scheduled.bat` (full no-cache + TMDB + newsletter + deploy)

## Test quirks

- All 46 tests are synchronous, no external dependencies.
- `conftest.py` provides `tmdb_service` (fake API key), `sample_screenings` (3 fixtures), `config_file` (tmp_path YAML), `filmrausch_embedded_json` fixture.
