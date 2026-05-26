# Agent Guidelines for Berlin Classics Newsletter

## Run (Windows)

```
venv\Scripts\activate.ps1
python main.py --no-cache          # fresh scrape, regenerates cache
python main.py                     # use cache/screenings.json
ruff check .                       # lint
pytest tests/                      # verify
```

Batch helpers: `run_fresh.bat`, `run_cached.bat`

> **Design-only changes**: Always use `python main.py` (cached). Fresh scraping takes ~20s and is unnecessary for HTML/CSS/template tweaks.

## Prerequisites

- `TMDB_API_KEY` in `.env` (create from `.env.example` if available)
- Python 3.13+ — `requirements.txt` lists dependencies

## Architecture

`main.py` orchestrates: reads `config.yaml` → instantiates scrapers → enriches via TMDB → filters ≤ threshold_year → renders Jinja2 template → saves to `output/`.

- `scrapers/base.py` — `BaseScraper`, `Screening` dataclass
- `scrapers/<name>.py` — one scraper per cinema type
- `services/tmdb.py` — TMDB lookup and title matching
- `services/newsletter.py` — Jinja2 template rendering
- `templates/newsletter.html` — HTML output + JS for calendar export / collapse
- `cache/screenings.json` — cached scraped data (regenerated on `--no-cache`)

## Screening dataclass fields

```python
Screening(
    cinema_name: str,      # newsletter section group name (e.g. "Open Air Cinema")
    movie_title: str,      # cleaned title from TMDB or source page
    date: datetime,        # screening datetime
    url: Optional[str],    # source page URL
    year: Optional[int],   # movie release year from TMDB
    poster_url: Optional[str],
    tmdb_url: Optional[str],
    skip_year_filter: bool = False,
    runtime: int = 0,
    venue_name: Optional[str],  # actual venue for calendar export
)
```

`Screening` is a regular `@dataclass` (NOT frozen) — fields are mutated during TMDB enrichment.
`venue_name` carries the actual venue; `cinema_name` is the section group. Template uses `screening.venue_name if screening.venue_name else screening.cinema_name`.

## Adding a new scraper

1. Create `scrapers/<name>.py` inheriting `BaseScraper`.
2. Implement `async get_screenings() -> list[Screening]`.
3. Register in `SCRAPER_MAP` in `main.py:33`.
4. Add to `config.yaml` under `cinemas:` with matching `type`.
5. If it needs TMDB enrichment, add its type to the `tmdb_service` check in `get_scraper()` at `main.py:68`.
6. If it already enriched titles (so `enrich_screenings` should skip it), add its type to the `skip_enriched` check in `scrape_cinema()` at `main.py:251`.
7. Steps 5 and 6 use the same list: `("babylon", "bestofcinema", "openair_kino")`.

## Open Air Kino scraper gotchas

- **Date regex**: must use `[\w.]+` (not `\w+`) to match abbreviated months like "Aug." that end in a period.
- **Date/time source**: live in a `div.meta_kino` **previous sibling** of each `article`, not inside the article itself.
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
