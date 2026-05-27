# Agent Guidelines for Berlin Classics Newsletter

## Run (Windows)

```
venv\Scripts\activate.ps1
pytest tests/          # verify
ruff check .           # lint
```

## Batch helpers

| File | Purpose |
|---|---|
| `run_fresh.bat` | Full fresh scrape, no cache |
| `run_cached.bat` | Render from cached screenings (fast, no TMDB calls) |
| `run_reenrich.bat` | Re-run TMDB enrichment on cached screenings (for threshold iteration) |
| `run_zoo_palast.bat` | Scrape only Zoo Palast, others from cache |
| `run_babylon.bat` | Scrape only Babylon, others from cache |
| `run_bestofcinema.bat` | Scrape only Best of Cinema, others from cache |
| `run_openair.bat` | Scrape only Open Air Cinema, others from cache |

> **Design-only changes**: Use `run_cached.bat` (or `python main.py`). Fresh scraping takes ~20s and is unnecessary for HTML/CSS/template tweaks.

## CLI flags

- `--no-cache` — force fresh scrape of all cinemas
- `--re-enrich` — load cache, clear TMDB lookup cache, re-run TMDB matching on all screenings, save back. Use when tuning thresholds in `services/tmdb.py`.
- `--cinema <type>` — scrape only this cinema type (babylon, zoo_palast, bestofcinema, openair_kino). Removes that cinema's screenings from cache before merging the fresh scrape (no duplicates). Other cinemas stay from cache.

## Prerequisites

- `TMDB_API_KEY` in `.env`
- Python 3.13+

## Architecture

`main.py` orchestrates: reads `config.yaml` → instantiates scrapers → enriches via TMDB → filters ≤ threshold_year → renders Jinja2 template → saves to `output/`.

- `scrapers/base.py` — `BaseScraper`, `Screening` dataclass
- `scrapers/<name>.py` — one scraper per cinema type
- `services/tmdb.py` — TMDB lookup and title matching
- `services/newsletter.py` — Jinja2 template rendering
- `templates/newsletter.html` — HTML output + JS for calendar export / collapse
- `cache/screenings.json` — cached scraped data

## Screening dataclass

```python
Screening(
    cinema_name: str,
    movie_title: str,
    date: datetime,
    url: Optional[str],
    year: Optional[int],       # TMDB release year
    poster_url: Optional[str],
    tmdb_url: Optional[str],
    skip_year_filter: bool,    # True for Filmklassiker / exempt from year filter
    runtime: int,
    venue_name: Optional[str], # actual venue for calendar export
    production_year: Optional[int],  # source-of-truth year from scraper API/page
)
```

`Screening` is a regular `@dataclass` (NOT frozen) — fields are mutated during TMDB enrichment.
`venue_name` carries the actual venue; `cinema_name` is the section group. Template uses `screening.venue_name if screening.venue_name else screening.cinema_name`.

## TMDB matching priority order (in `services/tmdb.py`)

1. **Exact year match** (step 1)
2. **±3 year match** with title similarity ≥ 0.3 (step 1.5) — extended tolerance, lower threshold. Uses `production_year` as `expected_year`.
3. **±2 year match** with title similarity ≥ 0.5 (step 2) — original tolerance
4. **Best similarity** fallback (step 3)

The `production_year` field is the source of truth for year-based filtering. It comes from the scraper (API response or page parsing). If `production_year` is `None`, the year filter steps are skipped.

## `_clean_title` — umlaut handling

Uses `unicodedata.normalize("NFD", title)` to decompose umlauts (ö→o, ü→u, ä→a), not `encode("ascii", "replace")`. This is critical for German titles — the old approach replaced umlauts with `?` and broke TMDB matching.

The regex `(?<=\s)-\s.*$` preserves compound words like "hai-alarm" (dash only removes content after a space-dash pattern).

## Adding a new scraper

1. Create `scrapers/<name>.py` inheriting `BaseScraper`.
2. Implement `async get_screenings() -> list[Screening]`.
3. Register in `SCRAPER_MAP` in `main.py:33`.
4. Add to `config.yaml` under `cinemas:` with matching `type`.
5. If it provides `production_year`, pass it to `Screening` — TMDB matching uses it as `expected_year`.
6. If it already enriched titles (so `enrich_screenings` should skip it), add its type to the `tmdb_service` check in `get_scraper()` at `main.py:68`.
7. If it already enriched titles (so `enrich_screenings` should skip it), add its type to the `skip_enriched` check in `scrape_cinema()` at `main.py:251`.
8. Steps 6 and 7 use the same list: `("babylon", "bestofcinema", "openair_kino")`.

## Cinema types and enrichment

- **zoo_palast** (PremiumKino): get `production_year` from API. TMDB enrichment uses it as `expected_year`.
- **babylon, bestofcinema, openair_kino**: enrich in scraper's `get_screenings()`. Skip in `enrich_screenings()`. **Never pass `expected_year`** for these — screening dates don't correspond to movie release years.

## Open Air Kino scraper gotchas

- **Date regex**: must use `[\w.]+` (not `\w+`) to match abbreviated months like "Aug." that end in a period.
- **Date/time source**: lives in a `div.meta_kino` **previous sibling** of each `article`, not inside the article itself.
- **German month names** must be mapped (Mär, Okt, Dez, etc.).
- **TMDB lookup**: happens in the scraper's `get_screenings()`, NOT in `enrich_screenings()`. **Never pass `expected_year`** — screening dates don't correspond to movie release years. TMDB matching should rely on title similarity, with the threshold_year filter applied afterward.
- **Compound words**: the TMDB `_clean_title` regex `(?<=\s)-\s.*$` uses a lookbehind to preserve compound words like "hai-alarm" (dash only removes content after a space-dash pattern).
- Multi-cinema aggregator, not a single venue.

## Cinema config fields

- `name` — section title in newsletter
- `url` — scraper source URL
- `type` — maps to scraper class
- `google_maps_url` — optional, shown in footer
- `title_filters` — list of substrings to exclude from screenings

## Iterating on TMDB matching thresholds

1. Change thresholds in `services/tmdb.py` (e.g. `<= 3` → `<= 4`, `>= 0.3` → `>= 0.4`)
2. Run `run_reenrich.bat` (or `python main.py --re-enrich`)
   - Loads cached screenings, clears TMDB lookup cache, re-queries TMDB, saves back
3. Check output

No page loading, no premiumkino API calls — just TMDB lookups.

## Poster cache TTL

`POSTER_CHECK_TTL = 86400` (24 hours). If cached screenings are older than this, stale posters are re-fetched from TMDB. Otherwise cache is used as-is.
