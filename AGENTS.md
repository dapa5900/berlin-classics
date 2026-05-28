# Berlin Classics Newsletter

## Commands (Windows)

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

**`--re-enrich`**: clears TMDB memory cache, re-runs TMDB on raw cache — use when `_clean_title` / matching logic changes.

**Cache staleness pitfall**: `--re-enrich` loads the OLD raw cache (`cache/screenings.json`). It does NOT re-scrape. If a scraper was updated to extract new fields (e.g. `production_year`, `runtime`), run `run_fresh.bat` first to regenerate the raw cache, THEN `--re-enrich` to re-run TMDB.

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
- TMDB API calls rate-limited: `asyncio.Semaphore(5)` + 3 retries with exponential backoff (2s/4s/8s) on 429.
- `_clean_title` (`services/tmdb.py`): NFD-normalizes, strips known series/festival prefixes. Add patterns here for obscure titles. Also handles multi-part titles ("trilogie"/"marathon"/"X-hour").
- Template groups screenings by `venue_name` if set, else `cinema_name`. Open Air Kino sets `venue_name` per-article; all others leave `None`.
- Config-driven via `config.yaml`: cinemas, title filters, year threshold (`classical_year_threshold: 2010`), output format.
- `locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")` at module level in `services/newsletter.py` — breaks if locale unavailable.
- **Timezone pitfall**: Kinoheld dates (`datetime.fromisoformat`) are timezone-aware; other scrapers produce naive datetimes. Sort must use `.replace(tzinfo=None)` — see `main.py:446`.

## Scraper gotchas

- **Babylon**: HTTP GET to `/programm`. Each `.mix` `<li>` has `cat-*` CSS class. `_strip_festival_prefix` auto-detects festival sections. Uses `.right-mix .mix-title`, `.mix-introtext` (year via `,\s*(\d{4})`, original via `[...]`), `.right-mix .runtime`.
- **Zoo Palast**: Playwright-based. Intercepts API JSON from `premiumkino.de/program` via network listener. Also scrapes `/specials/filmklassiker` to set `skip_year_filter=True`.
- **Best of Cinema**: Fetches each movie subpage. `Produktionsjahr:` and `Laufflänge` regex from page text. **Date regex pitfall**: uses `(\d{2})\.(\d{2})\.(\d{4})` — do NOT use `(\d{2})` for year or it'll capture only the first two digits of a four-digit year (e.g. "20" from "2026" → 2020).
- **Open Air Kino**: Does NOT scrape `production_year` or `runtime`. Date in `div.meta_kino` previous sibling of `<article>`, uses `[\w.]+` for abbreviated German months. Multi-cinema aggregator — `venue_name` set per screening.
- **Filmrausch**: HTTP-only (no Playwright). Parses embedded `<script id="programm-script-config-js-extra">` JSON (`filmrausch_php_vars.cached_data`). Strips `SPECIAL:`, `Klimareihe:`, `OPEN AIR:`, `OFFENE LEINWAND:`, `REEL LOVE:`, `MONDO VIDEO` prefixes via loop in `_clean_movie_title`. Dates from `isoFull` are timezone-aware. Backend = Kinoheld.

## TMDB matching (`services/tmdb.py`)

Matching is in `get_movie_info`. The method receives `expected_year`, `original_title`, and `scraped_runtime` as hints.

### Priority path (if `original_title` + `expected_year` both provided)
- Search TMDB by original title + exact year → if found, skip fallback.

### Fallback main search
- **Always searches BOTH languages** (`de-DE` + `en-US`), deduplicates by TMDB ID, then applies matching on the combined result set. No per-language early break.

Two branches:

**1. `expected_year` is known:**
1. **Exact title + exact year** — uses `_any_title_matches(m, cleaned_title)` which checks BOTH `title` and `original_title` fields. If multiple candidates, `_pick_by_runtime` fetches runtimes and picks the closest.
2. **Exact title ±3yr** — same `_any_title_matches`, same runtime tiebreaker.
3. **Exact year match** — any title, exact year.
4. **±3yr + similarity ≥ 0.8** — uses `_best_title_similarity(m, cleaned_title)` (max of title and original_title similarity).
5. **±2yr + similarity ≥ 0.5** — same.
6. **Best similarity fallback** — ≥0.7, best year diff wins.

**2. `expected_year` is `None` (e.g. Open Air Kino):**
- Find exact title matches via `_any_title_matches` (title OR original_title).
- If multiple matches AND `scraped_runtime` > 0: use `_pick_by_runtime`.
- Otherwise: pick by TMDB `popularity`.
- Fallback: fuzzy similarity via `_best_title_similarity`.

### Key helpers
- **`_any_title_matches(movie, search_title)`**: checks `movie["title"]` AND `movie["original_title"]` against the cleaned search title. Critical for German-localized entries (e.g. TMDB 578 Jaws has `title="Der weiße Hai"` but `original_title="Jaws"`).
- **`_best_title_similarity(movie, search_title)`**: returns `max(sim(title), sim(original_title))`.
- **`_pick_by_runtime(candidates, scraped_runtime)`**: fetches TMDB runtimes in parallel (`asyncio.gather`), picks closest to scraper's runtime. No tolerance — just absolute diff.
- **`_calculate_title_similarity(title1, title2)`**: simple word-level matching (exact → 1.0, substring → 0.8, common words ratio, else 0.0).

## Setup

- `TMDB_API_KEY` in `.env` (create from scratch, no template file)
- Python 3.13+, `pip install -r requirements.txt`
- `playwright install chromium` after pip install
- `cache/`, `output/`, `venv/`, `logs/` in `.gitignore`
- Scheduled Task (Windows): `NewsletterGenerator`, daily 13:00, runs `scripts\run_scheduled.bat`

## Test quirks

- All 46 tests are synchronous, no external dependencies.
- `conftest.py` provides `tmdb_service` (fake API key), `sample_screenings` (3 fixtures), `config_file` (tmp_path YAML), `filmrausch_embedded_json` fixture.
- No tests exercise the actual TMDB API — mocking would be needed for integration tests.

## Key files

| File | Purpose |
|---|---|
| `main.py` | Entrypoint: CLI arg parsing, orchestrates scrape → cache → enrich → filter → render |
| `scrapers/base.py` | `Screening` dataclass, `BaseScraper` with `fetch_page`/`fetch_page_js` helpers |
| `scrapers/bestofcinema.py` | Best of Cinema scraper — **date regex uses 4-digit year** |
| `services/tmdb.py` | TMDB enrichment with retry, semaphore, title cleaning, runtime disambiguation |
| `services/newsletter.py` | Jinja2 rendering with `de_DE` locale |
| `templates/newsletter.html` | Single Jinja2 template with inline CSS/JS |
| `config.yaml` | Cinema configs, filters, threshold, output |
| `DESIGN.md` | Full style & layout reference for the HTML template |
