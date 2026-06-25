# Berlin Classics Newsletter

## Commands

```powershell
venv\Scripts\activate.ps1                            # activate venv
venv\Scripts\python.exe -m pytest tests/ -v           # 46 sync tests, no external deps
ruff check .                                          # lint (no config file = defaults)
```

## Run modes

All `.bat` files delegate to `scripts\run_timed.bat` which activates venv, runs `python main.py %*`, logs elapsed time.

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

**Auto-run rule**: after code changes, auto-generate the newsletter to verify output:

| Change type | Run |
|---|---|
| Template/design (CSS, layout, Jinja) | `run_cached.bat` |
| Year threshold, title filters | `run_cached.bat` |
| TMDB matching / `_clean_title` | `run_process.bat` (or `run_fresh.bat` if cache stale, then `--re-enrich`) |
| Single cinema scraper | Individual cinema bat, then `run_cached.bat` for full output |
| Multiple scrapers / new fields | `run_fresh.bat` |

**`--re-enrich`**: clears TMDB memory cache, re-runs TMDB on raw cache — use when `_clean_title` / matching logic changes.

**Cache staleness**: `--re-enrich` loads OLD raw cache (`cache/screenings.json`), does NOT re-scrape. If scraper was updated (new fields like `production_year`), run `run_fresh.bat` first, THEN `--re-enrich`.

## Pipeline

```
scrape → cache/screenings.json → title filters → TMDB enrich → filter_no_tmdb → cache/screenings_enriched.json → year filter → newsletter
```

- **Raw cache** (`cache/screenings.json`): scraper output before TMDB.
- **Rich cache** (`cache/screenings_enriched.json`): after TMDB, before year/title filters.

## Architecture

- `Screening` dataclass (`scrapers/base.py`): `cinema_name`, `movie_title`, `date`, `url`, `year`, `poster_url`, `tmdb_url`, `skip_year_filter`, `runtime`, `venue_name`, `production_year`, `original_title`
- TMDB enrichment groups by `(movie_title, production_year, original_title)`, queries TMDB once per group, mutates `Screening` in place.
- TMDB rate-limited: `asyncio.Semaphore(5)` + 3 retries with exponential backoff (2s/4s/8s) on 429.
- Year threshold: `datetime.now().year - 10`. Films ≤ threshold or with `skip_year_filter=True` pass.
- Template groups by `venue_name` if set, else `cinema_name`. Only Open Air Kino sets `venue_name`.
- `locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")` at module level in `services/newsletter.py` — breaks if locale unavailable.
- **Timezone pitfall**: Kinoheld dates (`datetime.fromisoformat`) are timezone-aware; other scrapers produce naive datetimes. Sort must use `.replace(tzinfo=None)` — see `main.py:446`.

## Scraper gotchas

- **Babylon**: HTTP GET to `/programm`. Each `.mix` `<li>` has `cat-*` CSS class. `_strip_festival_prefix` auto-detects festival sections. Uses `.right-mix .mix-title`, `.mix-introtext` (year via `,\s*(\d{4})`, original via `[...]`), `.right-mix .runtime`.
- **Zoo Palast**: Playwright-based. Intercepts API JSON from `premiumkino.de/program` via network listener. Also scrapes `/specials/filmklassiker` to set `skip_year_filter=True`.
- **Best of Cinema**: Fetches each movie subpage. `Produktionsjahr:` and `Laufflänge` regex. **Date regex**: uses `(\d{2})\.(\d{2})\.(\d{4})` — do NOT use `(\d{2})` for year.
- **Open Air Kino**: No `production_year` or `runtime`. Date in `div.meta_kino` previous sibling of `<article>`, uses `[\w.]+` for abbreviated German months. Multi-cinema aggregator — sets `venue_name`.
- **Filmrausch**: HTTP-only (no Playwright). Parses embedded `<script id="programm-script-config-js-extra">` JSON (`filmrausch_php_vars.cached_data`). Strips `SPECIAL:`, `Klimareihe:`, `OPEN AIR:`, `OFFENE LEINWAND:`, `REEL LOVE:`, `MONDO VIDEO` prefixes via loop. Dates from `isoFull` are timezone-aware. Backend = Kinoheld.

## TMDB matching (`services/tmdb.py`)

`get_movie_info` receives `expected_year`, `original_title`, and `scraped_runtime`.

If `original_title` + `expected_year` both provided: search TMDB by original title + exact year first. Skip fallback if found.

Fallback main search: BOTH `de-DE` + `en-US`, deduplicated by TMDB ID.

**With `expected_year` known:**
1. Exact title + exact year → `_pick_by_runtime` if multiple
2. Exact title ±3yr → same runtime tiebreaker
3. Exact year (any title)
4. ±3yr + similarity ≥ 0.8
5. ±2yr + similarity ≥ 0.5
6. Best similarity (≥0.7, best year diff wins)

**Without `expected_year` (e.g. Open Air Kino):**
- Exact title matches → `_pick_by_runtime` if multiple + runtime > 0, else by TMDB `popularity`
- Fallback: fuzzy similarity

**Key helpers:**
- `_any_title_matches(movie, search_title)`: checks BOTH `title` and `original_title`. Critical for German-localized entries (TMDB 578: `title="Der weiße Hai"`, `original_title="Jaws"`).
- `_best_title_similarity(movie, search_title)`: max of title/original_title similarity.
- `_pick_by_runtime(candidates, scraped_runtime)`: fetches TMDB runtimes in parallel, picks closest.
- `_calculate_title_similarity(title1, title2)`: word-level (exact → 1.0, substring → 0.8, common-word ratio, else 0.0).
- `_clean_title`: NFD-normalizes, strips known series/festival prefixes. Add patterns here for obscure titles. Also handles multi-part titles ("trilogie"/"marathon"/"X-hour").

## Setup

- `TMDB_API_KEY` in `.env` (create from scratch, no template file)
- Python 3.13+, `pip install -r requirements.txt` → `playwright install chromium`
- `cache/`, `output/`, `venv/`, `logs/` in `.gitignore`
- Scheduled Task (Windows): `NewsletterGenerator`, every 3 days at 13:00, runs `scripts\run_scheduled.bat`

## Test quirks

- All 46 tests synchronous, no external dependencies.
- `conftest.py` provides `tmdb_service` (fake API key), `sample_screenings` (3 fixtures), `config_file` (tmp_path YAML), `filmrausch_embedded_json` fixture.
- No tests exercise the actual TMDB API — mocking needed for integration tests.

## Key files

| File | Purpose |
|---|---|
| `main.py` | Entrypoint: CLI arg parsing, orchestrates scrape → cache → enrich → filter → render |
| `scrapers/base.py` | `Screening` dataclass, `BaseScraper` with `fetch_page`/`fetch_page_js` helpers |
| `services/tmdb.py` | TMDB enrichment with retry, semaphore, title cleaning, runtime disambiguation |
| `services/newsletter.py` | Jinja2 rendering with `de_DE` locale |
| `templates/newsletter.html` | Single Jinja2 template with inline CSS/JS |
| `config.yaml` | Cinema configs, title filters, output format |
